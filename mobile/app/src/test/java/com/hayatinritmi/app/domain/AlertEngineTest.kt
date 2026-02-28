package com.hayatinritmi.app.domain

import com.hayatinritmi.app.domain.model.*
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class AlertEngineTest {

    @Before
    fun setup() {
        AlertEngine.reset()
    }

    private fun normalAi() = AiPrediction(
        label = ArrhythmiaClass.NORMAL, confidence = 0.92f,
        windowTimestampMs = System.currentTimeMillis()
    )

    private fun afibAi(conf: Float = 0.85f) = AiPrediction(
        label = ArrhythmiaClass.ATRIAL_FIBRILLATION, confidence = conf,
        windowTimestampMs = System.currentTimeMillis()
    )

    private fun lowConfAi() = AiPrediction(
        label = ArrhythmiaClass.UNKNOWN, confidence = 0.30f,
        windowTimestampMs = System.currentTimeMillis()
    )

    private fun connectedStatus(battery: Int = 80) = DeviceStatus(
        batteryPercent = battery, isElectrodeConnected = true,
        isCharging = false, signalQuality = 90
    )

    private fun disconnectedStatus() = DeviceStatus(
        batteryPercent = 80, isElectrodeConnected = false,
        isCharging = false, signalQuality = 0
    )

    private fun goodSignal() = SignalQuality(snrDb = 20f, prd = 5f, score = 85)
    private fun badSignal() = SignalQuality(snrDb = 5f, prd = 40f, score = 20)
    private fun normalHrv() = HrvMetrics(sdnn = 50f, rmssd = 35f)

    @Test
    fun `electrode off returns ELECTRODE_OFF`() {
        val result = AlertEngine.evaluate(72, normalHrv(), disconnectedStatus(), goodSignal(), normalAi())
        assertEquals(AlertLevel.ELECTRODE_OFF, result)
    }

    @Test
    fun `low signal quality returns LOW_SIGNAL`() {
        val result = AlertEngine.evaluate(72, normalHrv(), connectedStatus(), badSignal(), normalAi())
        assertEquals(AlertLevel.LOW_SIGNAL, result)
    }

    @Test
    fun `normal AI with good signal returns NONE`() {
        val result = AlertEngine.evaluate(72, normalHrv(), connectedStatus(), goodSignal(), normalAi())
        assertEquals(AlertLevel.NONE, result)
    }

    @Test
    fun `high confidence AFIB returns RED`() {
        val result = AlertEngine.evaluate(72, normalHrv(), connectedStatus(), goodSignal(), afibAi(0.90f))
        assertEquals(AlertLevel.RED, result)
    }

    @Test
    fun `low confidence AI returns RECHECK`() {
        val result = AlertEngine.evaluate(72, normalHrv(), connectedStatus(), goodSignal(), lowConfAi())
        assertEquals(AlertLevel.RECHECK, result)
    }

    @Test
    fun `sustained tachycardia over 30s returns YELLOW`() {
        val ai = AiPrediction(
            label = ArrhythmiaClass.NORMAL, confidence = 0.60f,
            windowTimestampMs = System.currentTimeMillis()
        )
        for (i in 0 until 31) {
            val result = AlertEngine.evaluate(150, normalHrv(), connectedStatus(), goodSignal(), ai)
            if (i < 29) {
                assertNotEquals("Before 30s should not be YELLOW at sec $i", AlertLevel.YELLOW, result)
            }
        }
        val finalResult = AlertEngine.evaluate(150, normalHrv(), connectedStatus(), goodSignal(), ai)
        // After 30+ seconds of tachycardia, should get YELLOW
        assertTrue("After 30s of tachy, should be YELLOW or higher",
            finalResult == AlertLevel.YELLOW || finalResult == AlertLevel.RED || finalResult == AlertLevel.RECHECK)
    }

    @Test
    fun `reset clears counters`() {
        for (i in 0 until 20) {
            AlertEngine.evaluate(150, normalHrv(), connectedStatus(), goodSignal(),
                AiPrediction(ArrhythmiaClass.NORMAL, 0.60f, windowTimestampMs = System.currentTimeMillis()))
        }
        AlertEngine.reset()
        val result = AlertEngine.evaluate(72, normalHrv(), connectedStatus(), goodSignal(), normalAi())
        assertEquals(AlertLevel.NONE, result)
    }
}
