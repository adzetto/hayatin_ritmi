package com.hayatinritmi.app.processing

import kotlin.math.PI
import kotlin.math.cos

class EcgFilter(
    private val sampleRateHz: Int = 250,
    private val notchFreqHz: Float = 50f
) {
    // HPF 0.5 Hz - Baseline wander removal
    private val hpfAlpha: Float = 1f / (1f + 2f * PI.toFloat() * 0.5f / sampleRateHz)
    private var hpfPrevX = 0f
    private var hpfPrevY = 0f

    // Notch filter 50Hz - Power line interference
    private val notchR = 0.985f // Controls bandwidth (Q~30)
    private val notchW0 = 2f * PI.toFloat() * notchFreqHz / sampleRateHz
    private val notchA1 = -2f * cos(notchW0)
    private val notchA2 = 1f
    private val notchB1 = -2f * notchR * cos(notchW0)
    private val notchB2 = notchR * notchR
    private var notchX1 = 0f
    private var notchX2 = 0f
    private var notchY1 = 0f
    private var notchY2 = 0f

    // LPF 40 Hz - Muscle artifact reduction
    private val lpfAlpha: Float = (2f * PI.toFloat() * 40f / sampleRateHz).let { dt ->
        dt / (1f + dt)
    }
    private var lpfPrevY = 0f

    fun filter(sample: Float): Float {
        // Stage 1: High-pass filter (remove baseline wander)
        val hpfOut = hpfAlpha * (hpfPrevY + sample - hpfPrevX)
        hpfPrevX = sample
        hpfPrevY = hpfOut

        // Stage 2: Notch filter (remove 50/60 Hz)
        val notchOut = hpfOut + notchA1 * notchX1 + notchA2 * notchX2 - notchB1 * notchY1 - notchB2 * notchY2
        notchX2 = notchX1
        notchX1 = hpfOut
        notchY2 = notchY1
        notchY1 = notchOut

        // Stage 3: Low-pass filter (remove muscle artifacts)
        val lpfOut = lpfAlpha * notchOut + (1f - lpfAlpha) * lpfPrevY
        lpfPrevY = lpfOut

        return lpfOut
    }

    fun reset() {
        hpfPrevX = 0f; hpfPrevY = 0f
        notchX1 = 0f; notchX2 = 0f; notchY1 = 0f; notchY2 = 0f
        lpfPrevY = 0f
    }
}
