package com.hayatinritmi.app.domain

import com.hayatinritmi.app.domain.model.*

/**
 * Araştırma Önerisi §3 + §4 — Hibrit karar motoru.
 *
 * Tahmin sırası:
 *  1. Elektrot kaybı kontrolü
 *  2. SNR sinyal kalitesi kontrolü
 *  3. DS-1D-CNN yüksek güven (≥0.80) → direkt karar
 *  4. Süre bazlı kural tabanlı kontroller (taşikardi/bradikardi 30s)
 *  5. R-R irregülarite + AI orta güven (0.55–0.80) → sarı
 *
 * Gereksiz alarm hedefi: ≤ %5
 */
object AlertEngine {

    private const val TACHY_BPM = 120
    private const val BRADY_BPM = 50
    private const val ANOMALY_DURATION_SEC = 30
    private const val RR_CV_THRESHOLD = 0.20f
    private const val AI_HIGH_CONF = 0.80f
    private const val AI_MID_CONF = 0.55f

    private var tachySec = 0
    private var bradySec = 0
    private var rrIrregSec = 0

    /**
     * Her saniyede bir çağrılmalı (EcgViewModel 1Hz timer'ından).
     * @param bpm Anlık BPM (RPeakDetector.currentBpm)
     * @param hrv HrvMetrics (sdnn, rmssd)
     * @param deviceStatus DeviceStatus (isElectrodeConnected, batteryPercent)
     * @param signalQuality SignalQuality (snrDb, isAcceptable)
     * @param ai AiPrediction (label, confidence)
     */
    fun evaluate(
        bpm: Int,
        hrv: HrvMetrics,
        deviceStatus: DeviceStatus,
        signalQuality: SignalQuality,
        ai: AiPrediction
    ): AlertLevel {

        if (!deviceStatus.isElectrodeConnected) {
            reset()
            return AlertLevel.ELECTRODE_OFF
        }

        if (!signalQuality.isAcceptable) {
            return AlertLevel.LOW_SIGNAL
        }

        // AI yüksek güven — direkt karar
        if (ai.isHighConfidence) {
            return when {
                ai.label.isCritical -> AlertLevel.RED
                ai.label != ArrhythmiaClass.NORMAL -> AlertLevel.YELLOW
                else -> {
                    reset()
                    AlertLevel.NONE
                }
            }
        }

        // AI çok düşük güven — tekrar ölçüm
        if (ai.isLowConfidence && bpm > 0) {
            return AlertLevel.RECHECK
        }

        // Kural tabanlı süre sayaçları
        val rrInterval = if (bpm > 0) 60000f / bpm else 0f
        val rrCv = if (rrInterval > 0f) hrv.sdnn / rrInterval else 0f

        if (bpm > TACHY_BPM) tachySec++ else tachySec = 0
        if (bpm in 1 until BRADY_BPM) bradySec++ else bradySec = 0
        if (rrCv > RR_CV_THRESHOLD) rrIrregSec++ else rrIrregSec = 0

        return when {
            tachySec >= ANOMALY_DURATION_SEC -> AlertLevel.YELLOW
            bradySec >= ANOMALY_DURATION_SEC -> AlertLevel.YELLOW
            rrIrregSec >= ANOMALY_DURATION_SEC && ai.needsRecheck -> AlertLevel.YELLOW
            else -> AlertLevel.NONE
        }
    }

    fun reset() {
        tachySec = 0
        bradySec = 0
        rrIrregSec = 0
    }
}
