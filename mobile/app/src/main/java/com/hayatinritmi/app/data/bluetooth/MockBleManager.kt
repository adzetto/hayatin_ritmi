package com.hayatinritmi.app.data.bluetooth

import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.domain.model.DeviceStatus
import com.hayatinritmi.app.domain.model.ScannedDevice
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
        var frameSeq = 0

        // Heart rate: ~72 BPM with slight variability
        val baseHeartRateHz = 1.2  // 72 BPM
        val pqrstTemplate = generatePqrstTemplate()
        // Lead-specific amplitude and polarity scaling factors (standard 12-lead morphology)
        // [I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6]
        val leadScaleR  = floatArrayOf(1.0f,  1.6f,  0.6f, -1.3f,  0.2f,  1.1f, -0.4f,  0.1f,  0.9f,  1.4f,  1.3f,  1.0f)
        val leadScaleT  = floatArrayOf(1.0f,  1.2f,  0.4f, -1.0f,  0.3f,  0.9f, -0.3f,  0.4f,  1.0f,  1.2f,  1.1f,  0.9f)
        val leadOffsetP = floatArrayOf(0.0f,  0.0f,  0.0f,  0.0f,  0.0f,  0.0f,  0.0f,  0.0f,  0.0f,  0.0f,  0.0f,  0.0f)

        while (currentCoroutineContext().isActive) {
            val heartRateHz = baseHeartRateHz + 0.05 * sin(timestampMs * 0.001)
            val phaseIncrement = heartRateHz / sampleRate
            phase += phaseIncrement
            if (phase >= 1.0) phase -= 1.0

            val baselineWander = 20f * sin(2.0 * PI * 0.3 * timestampMs / 1000.0).toFloat()
            val lineNoise = 5f * sin(2.0 * PI * 50.0 * timestampMs / 1000.0).toFloat()

            // Build 43-byte 12-lead frame
            val leadRawAdcs = IntArray(BleConstants.CHANNEL_COUNT) { ch ->
                val ecgUv = interpolateLeadValue(pqrstTemplate, phase.toFloat(), leadScaleR[ch], leadScaleT[ch])
                val muscleNoise = Random.nextFloat() * 3f - 1.5f
                val totalUv = ecgUv + baselineWander + lineNoise + muscleNoise
                ((totalUv / 1_000_000f) * EcgSample_ADC_MAX * EcgSample_GAIN / EcgSample_VREF).toInt()
            }

            emit(buildFrame(frameSeq, timestampMs, leadRawAdcs))
            frameSeq = (frameSeq + 1) and 0xFF
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

    private fun interpolateLeadValue(template: FloatArray, phase: Float, scaleR: Float, scaleT: Float): Float {
        val index = (phase * template.size).toInt().coerceIn(0, template.size - 1)
        val raw = template[index]
        // Apply lead-specific morphology: R-peak region (t≈0.17) uses scaleR, T-wave (t≈0.37) uses scaleT
        val t = phase
        return when {
            t in 0.14f..0.22f -> raw * scaleR
            t in 0.28f..0.46f -> raw * scaleT
            else -> raw
        }
    }

    private fun buildFrame(frameSeq: Int, timestampMs: Long, leadRawAdcs: IntArray): ByteArray {
        // 43-byte frame: [Header:1B][FrameSeq:1B][Timestamp:4B][12×Lead:36B int24 BE][Checksum:1B]
        val frame = ByteArray(BleConstants.PACKET_SIZE)
        frame[0] = BleConstants.PACKET_HEADER
        frame[1] = frameSeq.toByte()

        val tsBytes = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(timestampMs.toInt()).array()
        System.arraycopy(tsBytes, 0, frame, 2, 4)

        for (ch in 0 until BleConstants.CHANNEL_COUNT) {
            val offset = 6 + ch * BleConstants.BYTES_PER_LEAD
            val v = leadRawAdcs[ch]
            frame[offset]     = ((v shr 16) and 0xFF).toByte()
            frame[offset + 1] = ((v shr 8)  and 0xFF).toByte()
            frame[offset + 2] = (v          and 0xFF).toByte()
        }

        var xor: Byte = 0
        for (i in 0 until 42) xor = (xor.toInt() xor frame[i].toInt()).toByte()
        frame[42] = xor

        return frame
    }

    companion object {
        // Mirror EcgSample constants to avoid circular dep
        private const val EcgSample_VREF = 2.4f
        private const val EcgSample_GAIN = 6f
        private const val EcgSample_ADC_MAX = 8388608f
    }
}
