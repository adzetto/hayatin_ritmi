package com.hayatinritmi.app.ble

import com.hayatinritmi.app.data.BleConstants
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.ScannedDevice
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.*
import kotlin.random.Random

class MockBleManager : BleManager {
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    override val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _scannedDevices = MutableStateFlow<List<ScannedDevice>>(emptyList())
    override val scannedDevices: StateFlow<List<ScannedDevice>> = _scannedDevices.asStateFlow()

    private var scanJob: Job? = null
    private var dataJob: Job? = null

    override fun startScan(timeoutMs: Long) {
        _connectionState.value = ConnectionState.SCANNING
        _scannedDevices.value = emptyList()

        scanJob?.cancel()
        scanJob = scope.launch {
            // Simulate device discovery with delays
            delay(800)
            _scannedDevices.value = listOf(
                ScannedDevice("HayatinRitmi-T1", "AA:BB:CC:DD:EE:01", -45)
            )
            delay(1200)
            _scannedDevices.value = _scannedDevices.value + ScannedDevice("HayatinRitmi-T2", "AA:BB:CC:DD:EE:02", -68)

            // Auto-timeout
            delay(timeoutMs)
            if (_connectionState.value == ConnectionState.SCANNING) {
                _connectionState.value = ConnectionState.DISCONNECTED
            }
        }
    }

    override fun stopScan() {
        scanJob?.cancel()
        if (_connectionState.value == ConnectionState.SCANNING) {
            _connectionState.value = ConnectionState.DISCONNECTED
        }
    }

    override fun connect(device: ScannedDevice) {
        scanJob?.cancel()
        _connectionState.value = ConnectionState.CONNECTING
        scope.launch {
            delay(1500) // Simulate connection delay
            _connectionState.value = ConnectionState.CONNECTED
        }
    }

    override fun disconnect() {
        dataJob?.cancel()
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    override fun observeEcgData(): Flow<ByteArray> = flow {
        val sampleRate = BleConstants.SAMPLE_RATE_HZ
        val intervalMs = 1000L / sampleRate
        var timestampMs = 0L
        var phase = 0.0

        // Heart rate: ~72 BPM with slight variability
        val baseHeartRateHz = 1.2  // 72 BPM
        val pqrstTemplate = generatePqrstTemplate()

        while (currentCoroutineContext().isActive) {
            // Natural heart rate variability
            val heartRateHz = baseHeartRateHz + 0.05 * sin(timestampMs * 0.001)
            val phaseIncrement = heartRateHz / sampleRate

            phase += phaseIncrement
            if (phase >= 1.0) phase -= 1.0

            // Get PQRST value from template
            val ecgValue = interpolateTemplate(pqrstTemplate, phase.toFloat())

            // Add realistic noise
            val baselineWander = 20f * sin(2.0 * PI * 0.3 * timestampMs / 1000.0).toFloat()
            val lineNoise = 5f * sin(2.0 * PI * 50.0 * timestampMs / 1000.0).toFloat()
            val muscleNoise = Random.nextFloat() * 3f - 1.5f

            val totalUv = ecgValue + baselineWander + lineNoise + muscleNoise

            // Convert uV back to 24-bit ADC value
            val rawAdc = ((totalUv / 1_000_000f) * EcgSample_ADC_MAX * EcgSample_GAIN / EcgSample_VREF).toInt()

            emit(buildPacket(0, timestampMs, rawAdc))
            timestampMs += intervalMs
            delay(intervalMs)
        }
    }.flowOn(Dispatchers.Default)

    override fun observeDeviceStatus(): Flow<DeviceStatus> = flow {
        var battery = 85
        while (currentCoroutineContext().isActive) {
            emit(DeviceStatus(
                batteryPercent = battery,
                isElectrodeConnected = true,
                isCharging = false,
                signalQuality = Random.nextInt(85, 100)
            ))
            delay(10_000) // Update every 10 seconds
            battery = (battery - 1).coerceAtLeast(10)
        }
    }

    private fun generatePqrstTemplate(): FloatArray {
        // 250 points representing one cardiac cycle in uV
        val template = FloatArray(250)
        for (i in template.indices) {
            val t = i / 250f
            template[i] = when {
                // P wave (atrial depolarization)
                t in 0.0f..0.08f -> 30f * sin(PI.toFloat() * t / 0.08f)
                // PR segment
                t in 0.08f..0.12f -> 0f
                // Q wave
                t in 0.12f..0.15f -> -40f * sin(PI.toFloat() * (t - 0.12f) / 0.03f)
                // R wave (ventricular depolarization - the big spike)
                t in 0.15f..0.19f -> 350f * sin(PI.toFloat() * (t - 0.15f) / 0.04f)
                // S wave
                t in 0.19f..0.22f -> -60f * sin(PI.toFloat() * (t - 0.19f) / 0.03f)
                // ST segment
                t in 0.22f..0.30f -> 0f
                // T wave (ventricular repolarization)
                t in 0.30f..0.44f -> 80f * sin(PI.toFloat() * (t - 0.30f) / 0.14f)
                // Baseline
                else -> 0f
            }
        }
        return template
    }

    private fun interpolateTemplate(template: FloatArray, phase: Float): Float {
        val index = (phase * template.size).toInt().coerceIn(0, template.size - 1)
        return template[index]
    }

    private fun buildPacket(channel: Int, timestampMs: Long, rawAdc: Int): ByteArray {
        val packet = ByteArray(10)
        packet[0] = BleConstants.PACKET_HEADER

        packet[1] = channel.toByte()

        // Timestamp: little-endian uint32
        val tsBytes = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(timestampMs.toInt()).array()
        System.arraycopy(tsBytes, 0, packet, 2, 4)

        // ECG: 24-bit signed, big-endian
        packet[6] = ((rawAdc shr 16) and 0xFF).toByte()
        packet[7] = ((rawAdc shr 8) and 0xFF).toByte()
        packet[8] = (rawAdc and 0xFF).toByte()

        // Checksum: XOR of bytes 0..8
        var xor: Byte = 0
        for (i in 0 until 9) {
            xor = (xor.toInt() xor packet[i].toInt()).toByte()
        }
        packet[9] = xor

        return packet
    }

    companion object {
        // Mirror EcgSample constants to avoid circular dep
        private const val EcgSample_VREF = 2.4f
        private const val EcgSample_GAIN = 6f
        private const val EcgSample_ADC_MAX = 8388608f
    }
}
