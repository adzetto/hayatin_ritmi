package com.hayatinritmi.app.domain.model

data class AlertEvent(
    val timestampMs: Long,
    val level: AlertLevel,
    val alertSource: String,
    val bpm: Int,
    val aiPrediction: AiPrediction?,
    val lat: Double? = null,
    val lon: Double? = null
)
