package com.hayatinritmi.app.processing

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.sin

class RPeakDetectorTest {

    private lateinit var detector: RPeakDetector
    private val sampleRate = 250

    @Before
    fun setup() {
        detector = RPeakDetector(sampleRate)
    }

    private fun generateSyntheticEcg(bpm: Int, durationSec: Int): FloatArray {
        val totalSamples = sampleRate * durationSec
        val samples = FloatArray(totalSamples)
        val rrSamples = (60.0 / bpm * sampleRate).toInt()

        for (i in 0 until totalSamples) {
            val posInBeat = i % rrSamples
            val t = posInBeat.toDouble() / sampleRate

            val qrsCenter = 0.3
            val qrsWidth = 0.02
            val pWaveCenter = 0.15
            val tWaveCenter = 0.55

            val rWave = 1.5 * exp(-((t - qrsCenter) * (t - qrsCenter)) / (2 * qrsWidth * qrsWidth))
            val pWave = 0.15 * exp(-((t - pWaveCenter) * (t - pWaveCenter)) / (2 * 0.03 * 0.03))
            val tWave = 0.3 * exp(-((t - tWaveCenter) * (t - tWaveCenter)) / (2 * 0.05 * 0.05))
            val qWave = -0.1 * exp(-((t - (qrsCenter - 0.03)) * (t - (qrsCenter - 0.03))) / (2 * 0.01 * 0.01))
            val sWave = -0.15 * exp(-((t - (qrsCenter + 0.03)) * (t - (qrsCenter + 0.03))) / (2 * 0.01 * 0.01))

            samples[i] = (pWave + qWave + rWave + sWave + tWave).toFloat() * 500f  // scale to uV
        }
        return samples
    }

    @Test
    fun `detects peaks in 72 BPM signal`() {
        val ecg = generateSyntheticEcg(72, 20)
        var peakCount = 0
        for (sample in ecg) {
            if (detector.processSample(sample)) peakCount++
        }
        assertTrue("Should detect peaks (got $peakCount)", peakCount > 3)

        val bpm = detector.currentBpm
        assertTrue("BPM should be in valid range (got $bpm)", bpm in 30..200)
    }

    @Test
    fun `detects tachycardia at 150 BPM`() {
        val ecg = generateSyntheticEcg(150, 15)
        for (sample in ecg) { detector.processSample(sample) }
        val bpm = detector.currentBpm
        assertTrue("BPM should be near 150 (got $bpm)", bpm in 120..180)
    }

    @Test
    fun `detects bradycardia at 45 BPM`() {
        val ecg = generateSyntheticEcg(45, 30)
        for (sample in ecg) { detector.processSample(sample) }
        val bpm = detector.currentBpm
        assertTrue("BPM should be near 45 (got $bpm)", bpm in 35..55)
    }

    @Test
    fun `HRV metrics are computed`() {
        val ecg = generateSyntheticEcg(72, 15)
        for (sample in ecg) { detector.processSample(sample) }
        val hrv = detector.currentHrv
        assertTrue("SDNN should be positive (got ${hrv.sdnn})", hrv.sdnn >= 0f)
        assertTrue("RMSSD should be positive (got ${hrv.rmssd})", hrv.rmssd >= 0f)
    }

    @Test
    fun `reset clears all state`() {
        val ecg = generateSyntheticEcg(72, 10)
        for (sample in ecg) { detector.processSample(sample) }
        assertTrue(detector.currentBpm > 0)

        detector.reset()
        assertEquals(0, detector.currentBpm)
        assertEquals(0f, detector.currentHrv.sdnn, 0.001f)
    }

    @Test
    fun `flat signal produces no peaks`() {
        val flat = FloatArray(5000) { 0f }
        var peaks = 0
        for (s in flat) { if (detector.processSample(s)) peaks++ }
        assertEquals("Flat signal should have 0 peaks", 0, peaks)
    }
}
