package com.hayatinritmi.app.domain.model

data class SignalQuality(
    val snrDb: Float = 0f,
    val prd: Float = 0f,
    val score: Int = 0
) {
    val isAcceptable: Boolean get() = snrDb >= 12f

    companion object {
        val UNKNOWN = SignalQuality(0f, 0f, 0)

        fun fromSnr(snrDb: Float): SignalQuality {
            val score = ((snrDb - 6f) / 24f * 100f).toInt().coerceIn(0, 100)
            return SignalQuality(snrDb, 0f, score)
        }
    }
}
