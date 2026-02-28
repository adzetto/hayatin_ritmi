package com.hayatinritmi.app.integration

import com.hayatinritmi.app.data.bluetooth.BleConstants
import com.hayatinritmi.app.data.bluetooth.BleManager
import com.hayatinritmi.app.data.repository.BleEcgRepository
import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.domain.model.DeviceStatus
import com.hayatinritmi.app.domain.model.EcgSample
import com.hayatinritmi.app.domain.model.ScannedDevice
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder

@OptIn(ExperimentalCoroutinesApi::class)
class BlePipelineIntegrationTest {

    @Test
    fun `connected pipeline emits 12 samples per frame`() = runTest {
        val ble = FakeBleManager()
        val repository = BleEcgRepository(ble)
        val samples = mutableListOf<EcgSample>()

        val job: Job = launch {
            repository.observeEcgSamples().toList(samples)
        }

        ble.setConnected()
        advanceUntilIdle()
        ble.emitFrame(buildValidFrame(frameSeq = 1, timestampMs = 1000L))
        advanceUntilIdle()

        assertEquals(12, samples.size)
        assertEquals(0, samples.first().channel)
        assertEquals(11, samples.last().channel)
        job.cancel()
    }

    @Test
    fun `stress connect disconnect loop does not leak disconnected frames`() = runTest {
        val ble = FakeBleManager()
        val repository = BleEcgRepository(ble)
        val samples = mutableListOf<EcgSample>()

        val job: Job = launch {
            repository.observeEcgSamples().toList(samples)
        }

        repeat(50) { idx ->
            ble.setConnected()
            advanceUntilIdle()
            ble.emitFrame(buildValidFrame(frameSeq = idx, timestampMs = idx * 4L))
            advanceUntilIdle()
            ble.setDisconnected()
            advanceUntilIdle()
            // This frame should not be observed while disconnected.
            ble.emitFrame(buildValidFrame(frameSeq = idx + 100, timestampMs = idx * 4L + 1))
            advanceUntilIdle()
        }
        advanceUntilIdle()

        // 50 connected frames x 12 leads
        assertEquals(600, samples.size)
        assertTrue(samples.none { it.timestamp % 4L == 1L })
        job.cancel()
    }

    private fun buildValidFrame(frameSeq: Int, timestampMs: Long): ByteArray {
        val frame = ByteArray(BleConstants.PACKET_SIZE)
        frame[0] = BleConstants.PACKET_HEADER
        frame[1] = frameSeq.toByte()

        val ts = ByteBuffer.allocate(4)
            .order(ByteOrder.LITTLE_ENDIAN)
            .putInt(timestampMs.toInt())
            .array()
        System.arraycopy(ts, 0, frame, 2, 4)

        for (ch in 0 until BleConstants.CHANNEL_COUNT) {
            val value = 100000 + ch
            val offset = 6 + ch * BleConstants.BYTES_PER_LEAD
            frame[offset] = ((value shr 16) and 0xFF).toByte()
            frame[offset + 1] = ((value shr 8) and 0xFF).toByte()
            frame[offset + 2] = (value and 0xFF).toByte()
        }

        var xor: Byte = 0
        for (i in 0 until 42) xor = (xor.toInt() xor frame[i].toInt()).toByte()
        frame[42] = xor

        return frame
    }
}

private class FakeBleManager : BleManager {
    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    override val connectionState: StateFlow<ConnectionState> = _connectionState

    private val _scannedDevices = MutableStateFlow<List<ScannedDevice>>(emptyList())
    override val scannedDevices: StateFlow<List<ScannedDevice>> = _scannedDevices

    private val ecgFlow = MutableSharedFlow<ByteArray>(extraBufferCapacity = 64)
    private val statusFlow = MutableSharedFlow<DeviceStatus>(extraBufferCapacity = 8)

    override fun startScan(timeoutMs: Long) = Unit
    override fun stopScan() = Unit
    override fun connect(device: ScannedDevice) = setConnected()
    override fun disconnect() = setDisconnected()

    override fun observeEcgData(): Flow<ByteArray> = ecgFlow
    override fun observeDeviceStatus(): Flow<DeviceStatus> = statusFlow

    fun setConnected() {
        _connectionState.value = ConnectionState.CONNECTED
    }

    fun setDisconnected() {
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    fun emitFrame(frame: ByteArray) {
        ecgFlow.tryEmit(frame)
    }
}
