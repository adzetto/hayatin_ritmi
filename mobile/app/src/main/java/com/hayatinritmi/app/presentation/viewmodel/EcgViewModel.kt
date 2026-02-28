package com.hayatinritmi.app.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.data.export.CsvExporter
import com.hayatinritmi.app.data.export.PdfReportGenerator
import com.hayatinritmi.app.data.local.entity.EcgSessionEntity
import com.hayatinritmi.app.data.recording.EcgSessionRecorder
import com.hayatinritmi.app.domain.AlertEngine
import com.hayatinritmi.app.domain.repository.EcgRepository
import com.hayatinritmi.app.domain.model.AiPrediction
import com.hayatinritmi.app.domain.model.AlertLevel
import com.hayatinritmi.app.domain.model.ConnectionState
import com.hayatinritmi.app.domain.model.DeviceStatus
import com.hayatinritmi.app.domain.model.HrvMetrics
import com.hayatinritmi.app.domain.model.SignalQuality
import com.hayatinritmi.app.data.bluetooth.BleManager
import com.hayatinritmi.app.processing.AdvancedEcgProcessor
import com.hayatinritmi.app.processing.ArrhythmiaClassifier
import com.hayatinritmi.app.processing.RPeakDetector
import com.hayatinritmi.app.processing.RingBuffer
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class EcgViewModel @Inject constructor(
    private val repository: EcgRepository,
    private val bleManager: BleManager,
    private val classifier: ArrhythmiaClassifier,
    val sessionRecorder: EcgSessionRecorder,
    val csvExporter: CsvExporter,
    val pdfReportGenerator: PdfReportGenerator
) : ViewModel() {

    private val ringBuffer = RingBuffer(2500)   // Lead II grafik için
    private val processor = AdvancedEcgProcessor()
    private val rPeakDetector = RPeakDetector()

    // ─── 12-Kanal AI Tampon (her derivasyon için 2500 örnek) ────────────────
    private val multiChannelBuffer = Array(12) { FloatArray(2500) }
    private val channelWriteIdx = IntArray(12)

    // ─── Temel EKG StateFlow'ları ────────────────────────────────────────────
    private val _graphPoints = MutableStateFlow<List<Float>>(emptyList())
    val graphPoints: StateFlow<List<Float>> = _graphPoints.asStateFlow()

    private val _bpm = MutableStateFlow(0)
    val bpm: StateFlow<Int> = _bpm.asStateFlow()

    private val _hrv = MutableStateFlow(HrvMetrics())
    val hrv: StateFlow<HrvMetrics> = _hrv.asStateFlow()

    private val _deviceStatus = MutableStateFlow(DeviceStatus.DISCONNECTED)
    val deviceStatus: StateFlow<DeviceStatus> = _deviceStatus.asStateFlow()

    val connectionState: StateFlow<ConnectionState> = bleManager.connectionState

    // ─── FAZ 3 StateFlow'ları — AI + Alert + Sinyal Kalitesi ────────────────
    private val _aiPrediction = MutableStateFlow(AiPrediction())
    val aiPrediction: StateFlow<AiPrediction> = _aiPrediction.asStateFlow()

    private val _alertLevel = MutableStateFlow(AlertLevel.NONE)
    val alertLevel: StateFlow<AlertLevel> = _alertLevel.asStateFlow()

    private val _signalQuality = MutableStateFlow(SignalQuality.UNKNOWN)
    val signalQuality: StateFlow<SignalQuality> = _signalQuality.asStateFlow()

    // ─── FAZ 4 StateFlow'ları — Recording ───────────────────────────────────
    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording.asStateFlow()

    private val _recordingDurationMs = MutableStateFlow(0L)
    val recordingDurationMs: StateFlow<Long> = _recordingDurationMs.asStateFlow()

    private val _lastSession = MutableStateFlow<EcgSessionEntity?>(null)
    val lastSession: StateFlow<EcgSessionEntity?> = _lastSession.asStateFlow()

    private var sampleCounter = 0

    init {
        viewModelScope.launch {
            repository.observeEcgSamples().collect { sample ->
                val ch = sample.channel.coerceIn(0, 11)

                // Tüm kanalları 12-kanal AI tamponuna yaz
                val idx = channelWriteIdx[ch] % 2500
                multiChannelBuffer[ch][idx] = sample.voltageUv
                channelWriteIdx[ch]++

                // Session recording — her sample'ı diske yaz
                if (sessionRecorder.isRecording) {
                    sessionRecorder.addSample(sample)
                }

                // Lead II (channel 1) → grafik + BPM + alert
                if (ch == 1) {
                    val filtered = processor.processSample(sample.voltageUv)
                    ringBuffer.add(filtered)
                    rPeakDetector.processSample(filtered)

                    sampleCounter++

                    // 30 FPS UI güncellemesi (her 8 örnekte)
                    if (sampleCounter % 8 == 0) {
                        _graphPoints.value = ringBuffer.getLastN(1000).toList()
                        _bpm.value = rPeakDetector.currentBpm
                        _hrv.value = rPeakDetector.currentHrv

                        // Update recording BPM
                        if (sessionRecorder.isRecording) {
                            sessionRecorder.updateBpm(rPeakDetector.currentBpm)
                            _recordingDurationMs.value = sessionRecorder.getRecordingDurationMs()
                        }
                    }

                    // Her 1 saniyede AlertEngine değerlendirmesi (250 örnekte)
                    if (sampleCounter % 250 == 0) {
                        val quality = processor.computeSignalQuality()
                        _signalQuality.value = quality
                        val currentAlert = AlertEngine.evaluate(
                            bpm = rPeakDetector.currentBpm,
                            hrv = rPeakDetector.currentHrv,
                            deviceStatus = _deviceStatus.value,
                            signalQuality = quality,
                            ai = _aiPrediction.value
                        )
                        _alertLevel.value = currentAlert
                    }

                    // Her 10 saniyede DS-1D-CNN 12-lead çıkarımı (2500 örnekte)
                    if (sampleCounter % 2500 == 0) {
                        val window = Array(12) { c -> multiChannelBuffer[c].copyOf() }
                        viewModelScope.launch(Dispatchers.Default) {
                            val prediction = classifier.classify(window)
                            _aiPrediction.value = prediction
                        }
                    }
                }
            }
        }

        viewModelScope.launch {
            repository.observeDeviceStatus().collect { status ->
                _deviceStatus.value = status
            }
        }
    }

    // ─── Recording Controls ─────────────────────────────────────────────────

    fun startRecording(userId: Long) {
        viewModelScope.launch {
            val sessionId = sessionRecorder.startRecording(userId)
            _isRecording.value = true
            _recordingDurationMs.value = 0L
        }
    }

    fun stopRecording() {
        viewModelScope.launch {
            val session = sessionRecorder.stopRecording()
            _isRecording.value = false
            _recordingDurationMs.value = 0L
            _lastSession.value = session
        }
    }

    fun resetProcessing() {
        ringBuffer.clear()
        processor.reset()
        rPeakDetector.reset()
        AlertEngine.reset()
        sampleCounter = 0
        for (ch in 0 until 12) {
            multiChannelBuffer[ch].fill(0f)
            channelWriteIdx[ch] = 0
        }
        _graphPoints.value = emptyList()
        _bpm.value = 0
        _hrv.value = HrvMetrics()
        _aiPrediction.value = AiPrediction()
        _alertLevel.value = AlertLevel.NONE
        _signalQuality.value = SignalQuality.UNKNOWN
    }

    override fun onCleared() {
        super.onCleared()
        classifier.close()
        if (sessionRecorder.isRecording) {
            // Fire-and-forget stop in case ViewModel is cleared while recording
            viewModelScope.launch { sessionRecorder.stopRecording() }
        }
    }
}
