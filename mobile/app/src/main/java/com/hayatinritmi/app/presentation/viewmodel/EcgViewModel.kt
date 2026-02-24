package com.hayatinritmi.app.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class EcgViewModel(
    private val repository: EcgRepository,
    private val bleManager: BleManager,
    private val classifier: ArrhythmiaClassifier
) : ViewModel() {

    private val ringBuffer = RingBuffer(2500)   // 10 saniye @ 250 Hz
    private val processor = AdvancedEcgProcessor()
    private val rPeakDetector = RPeakDetector()

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

    private var sampleCounter = 0

    init {
        viewModelScope.launch {
            repository.observeEcgSamples().collect { sample ->
                val filtered = processor.processSample(sample.voltageUv)
                ringBuffer.add(filtered)
                rPeakDetector.processSample(filtered)

                sampleCounter++

                // 30 FPS UI güncellemesi (her 8 örnekte)
                if (sampleCounter % 8 == 0) {
                    _graphPoints.value = ringBuffer.getLastN(1000).toList()
                    _bpm.value = rPeakDetector.currentBpm
                    _hrv.value = rPeakDetector.currentHrv
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

                // Her 10 saniyede DCA-CNN çıkarımı (2500 örnekte)
                if (sampleCounter % 2500 == 0) {
                    val window = ringBuffer.getAll()
                    viewModelScope.launch(Dispatchers.Default) {
                        val prediction = classifier.classify(window)
                        _aiPrediction.value = prediction
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

    fun resetProcessing() {
        ringBuffer.clear()
        processor.reset()
        rPeakDetector.reset()
        AlertEngine.reset()
        sampleCounter = 0
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
    }
}
