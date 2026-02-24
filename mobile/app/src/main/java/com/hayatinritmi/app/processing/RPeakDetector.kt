package com.hayatinritmi.app.processing

import com.hayatinritmi.app.domain.model.HrvMetrics
import kotlin.math.sqrt

class RPeakDetector(private val sampleRateHz: Int = 250) {
    private val windowSize = (0.150 * sampleRateHz).toInt() // 150ms integration window
    private val refractoryPeriod = (0.200 * sampleRateHz).toInt() // 200ms min between peaks

    private val integrationBuffer = FloatArray(windowSize)
    private var integrationIndex = 0
    private var integrationSum = 0f

    private var prevSample = 0f
    private var threshold = 0f
    private var peakValue = 0f
    private var samplesSinceLastPeak = 0

    private val rrIntervals = mutableListOf<Float>() // in milliseconds
    private val maxRRHistory = 20

    var currentBpm: Int = 0
        private set
    var currentHrv: HrvMetrics = HrvMetrics()
        private set

    fun processSample(filteredSample: Float): Boolean {
        // Step 1: Derivative
        val derivative = filteredSample - prevSample
        prevSample = filteredSample

        // Step 2: Squaring
        val squared = derivative * derivative

        // Step 3: Moving window integration
        integrationSum -= integrationBuffer[integrationIndex]
        integrationBuffer[integrationIndex] = squared
        integrationSum += squared
        integrationIndex = (integrationIndex + 1) % windowSize
        val integrated = integrationSum / windowSize

        // Step 4: Adaptive threshold
        samplesSinceLastPeak++

        if (integrated > threshold && samplesSinceLastPeak > refractoryPeriod) {
            // R-peak detected
            val rrMs = samplesSinceLastPeak * 1000f / sampleRateHz

            // Sanity check: 30-200 BPM range (300-2000ms R-R)
            if (rrMs in 300f..2000f) {
                rrIntervals.add(rrMs)
                if (rrIntervals.size > maxRRHistory) {
                    rrIntervals.removeAt(0)
                }
                updateMetrics()
            }

            samplesSinceLastPeak = 0
            peakValue = integrated
            threshold = 0.5f * peakValue
            return true
        }

        // Slowly decay threshold
        threshold *= 0.998f

        return false
    }

    private fun updateMetrics() {
        if (rrIntervals.size < 3) return

        // BPM from mean R-R interval
        val meanRR = rrIntervals.average().toFloat()
        currentBpm = (60_000f / meanRR).toInt().coerceIn(30, 200)

        // SDNN
        val sdnn = rrIntervals.map { it - meanRR }.map { it * it }.average().let { sqrt(it) }.toFloat()

        // RMSSD
        val successiveDiffs = rrIntervals.zipWithNext { a, b -> (b - a) }
        val rmssd = successiveDiffs.map { it * it }.average().let { sqrt(it) }.toFloat()

        currentHrv = HrvMetrics(sdnn = sdnn, rmssd = rmssd)
    }

    fun reset() {
        prevSample = 0f
        threshold = 0f
        peakValue = 0f
        samplesSinceLastPeak = 0
        integrationBuffer.fill(0f)
        integrationIndex = 0
        integrationSum = 0f
        rrIntervals.clear()
        currentBpm = 0
        currentHrv = HrvMetrics()
    }
}
