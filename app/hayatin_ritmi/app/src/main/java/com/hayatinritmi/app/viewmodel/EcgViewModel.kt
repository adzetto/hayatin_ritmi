package com.hayatinritmi.app.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.hayatinritmi.app.data.EcgRepository
import com.hayatinritmi.app.data.model.ConnectionState
import com.hayatinritmi.app.data.model.DeviceStatus
import com.hayatinritmi.app.data.model.HrvMetrics
import com.hayatinritmi.app.ble.BleManager
import com.hayatinritmi.app.processing.EcgFilter
import com.hayatinritmi.app.processing.RPeakDetector
import com.hayatinritmi.app.processing.RingBuffer
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch

class EcgViewModel(
    private val repository: EcgRepository,
    private val bleManager: BleManager
) : ViewModel() {

    private val ringBuffer = RingBuffer(2500)  // 10 seconds at 250Hz
    private val filter = EcgFilter()
    private val rPeakDetector = RPeakDetector()

    // Graph points for Canvas (last 4 seconds = 1000 samples)
    private val _graphPoints = MutableStateFlow<List<Float>>(emptyList())
    val graphPoints: StateFlow<List<Float>> = _graphPoints.asStateFlow()

    private val _bpm = MutableStateFlow(0)
    val bpm: StateFlow<Int> = _bpm.asStateFlow()

    private val _hrv = MutableStateFlow(HrvMetrics())
    val hrv: StateFlow<HrvMetrics> = _hrv.asStateFlow()

    private val _deviceStatus = MutableStateFlow(DeviceStatus.DISCONNECTED)
    val deviceStatus: StateFlow<DeviceStatus> = _deviceStatus.asStateFlow()

    val connectionState: StateFlow<ConnectionState> = bleManager.connectionState

    private var sampleCounter = 0

    init {
        // Collect ECG samples
        viewModelScope.launch {
            repository.observeEcgSamples().collect { sample ->
                val filtered = filter.filter(sample.voltageUv)
                ringBuffer.add(filtered)
                rPeakDetector.processSample(filtered)

                sampleCounter++
                // Update UI every ~33ms (30 FPS) = every 8 samples at 250Hz
                if (sampleCounter % 8 == 0) {
                    _graphPoints.value = ringBuffer.getLastN(1000).toList()
                    _bpm.value = rPeakDetector.currentBpm
                    _hrv.value = rPeakDetector.currentHrv
                }
            }
        }

        // Collect device status
        viewModelScope.launch {
            repository.observeDeviceStatus().collect { status ->
                _deviceStatus.value = status
            }
        }
    }

    fun resetProcessing() {
        ringBuffer.clear()
        filter.reset()
        rPeakDetector.reset()
        _graphPoints.value = emptyList()
        _bpm.value = 0
        _hrv.value = HrvMetrics()
    }
}
