package com.hayatinritmi.app.domain.model

enum class ArrhythmiaClass(val displayName: String, val isCritical: Boolean) {
    NORMAL("Normal Ritim", false),
    TACHYCARDIA("Taşikardi", false),
    BRADYCARDIA("Bradikardi", false),
    ATRIAL_FIBRILLATION("Atriyal Fibrilasyon", true),
    ST_ANOMALY("ST Segmenti Anomalisi", true),
    UNKNOWN("Belirsiz — Tekrar Ölçün", false)
}
