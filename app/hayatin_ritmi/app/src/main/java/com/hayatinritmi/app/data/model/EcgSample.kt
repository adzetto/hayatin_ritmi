package com.hayatinritmi.app.data.model

data class EcgSample(
    val timestamp: Long,      // milliseconds
    val channel: Int,         // 0 = Lead I
    val rawAdc: Int,          // 24-bit signed ADC value
    val voltageUv: Float      // microvolts (µV)
) {
    companion object {
        // ADS1293 parameters
        const val VREF = 2.4f         // Reference voltage
        const val GAIN = 6f           // Default gain
        const val ADC_MAX = 8388608f  // 2^23

        fun fromRawAdc(timestamp: Long, channel: Int, rawAdc: Int): EcgSample {
            val voltageUv = (rawAdc * VREF) / (ADC_MAX * GAIN) * 1_000_000f
            return EcgSample(timestamp, channel, rawAdc, voltageUv)
        }
    }
}
