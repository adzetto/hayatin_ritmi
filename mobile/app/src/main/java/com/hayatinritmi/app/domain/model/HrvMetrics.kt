package com.hayatinritmi.app.domain.model

data class HrvMetrics(
    val sdnn: Float = 0f,   // Standard deviation of R-R intervals (ms)
    val rmssd: Float = 0f   // Root mean square of successive differences (ms)
)
