package com.hayatinritmi.app.processing

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import kotlin.math.PI
import kotlin.math.sin
import kotlin.math.sqrt

class AdvancedEcgProcessorTest {

    private lateinit var processor: AdvancedEcgProcessor

    @Before
    fun setup() {
        processor = AdvancedEcgProcessor(sampleRateHz = 250)
    }

    @Test
    fun `process single sample returns finite value`() {
        val out = processor.processSample(100f)
        assertTrue("Output should be finite", out.isFinite())
    }

    @Test
    fun `processor output is always finite`() {
        for (i in 0 until 3000) {
            val raw = 500f + 200f * sin(2 * PI * 0.3 * i / 250.0).toFloat()
            val out = processor.processSample(raw)
            assertTrue("Output at sample $i should be finite", out.isFinite())
        }
    }

    @Test
    fun `signal quality returns valid score`() {
        for (i in 0 until 3000) {
            val ecg = 300f * sin(2 * PI * 5.0 * i / 250.0).toFloat()
            val noise = (Math.random() * 10 - 5).toFloat()
            processor.processSample(ecg + noise)
        }
        val quality = processor.computeSignalQuality()
        assertTrue("SNR should be positive (got ${quality.snrDb})", quality.snrDb >= 0f)
        assertTrue("Score should be 0-100 (got ${quality.score})", quality.score in 0..100)
    }

    @Test
    fun `covariance matrix is symmetric`() {
        val n = 500
        val channels = Array(3) { ch ->
            FloatArray(n) { i ->
                sin(2 * PI * (5.0 + ch) * i / 250.0).toFloat() + (Math.random() * 0.1).toFloat()
            }
        }
        val cov = processor.computeCovarianceMatrix(channels)
        for (i in cov.indices) {
            for (j in cov.indices) {
                assertEquals("Cov[$i][$j] should equal Cov[$j][$i]",
                    cov[i][j].toDouble(), cov[j][i].toDouble(), 1e-5)
            }
        }
    }

    @Test
    fun `dominant eigenvalue is positive for real signals`() {
        val n = 500
        val channels = Array(3) { ch ->
            FloatArray(n) { i ->
                sin(2 * PI * 5.0 * i / 250.0).toFloat() * (1 + ch * 0.5f)
            }
        }
        val cov = processor.computeCovarianceMatrix(channels)
        val lambda = processor.dominantEigenvalue(cov)
        assertTrue("Dominant eigenvalue should be positive (got $lambda)", lambda > 0f)
    }

    @Test
    fun `consistency analysis detects correlated signals`() {
        val n = 2500
        val base = FloatArray(n) { i -> sin(2 * PI * 5.0 * i / 250.0).toFloat() * 300f }
        val channels = Array(12) { ch ->
            FloatArray(n) { i -> base[i] * (0.8f + ch * 0.05f) + (Math.random() * 5 - 2.5).toFloat() }
        }
        val result = processor.analyzeMultiChannelConsistency(channels)
        assertTrue("Correlated signals should have high consistency (got ${result.channelConsistencyScore})",
            result.channelConsistencyScore > 50f)
        assertTrue("Dominant ratio should be high (got ${result.dominantRatio})",
            result.dominantRatio > 0.5f)
    }

    @Test
    fun `consistency analysis detects artifact channel`() {
        val n = 2500
        val base = FloatArray(n) { i -> sin(2 * PI * 5.0 * i / 250.0).toFloat() * 300f }
        val channels = Array(12) { ch ->
            if (ch == 5) {
                FloatArray(n) { (Math.random() * 5000 - 2500).toFloat() }
            } else {
                FloatArray(n) { i -> base[i] * (0.8f + ch * 0.03f) + (Math.random() * 3).toFloat() }
            }
        }
        val result = processor.analyzeMultiChannelConsistency(channels)
        assertTrue("Should detect artifact channels", result.artifactChannels.isNotEmpty())
    }

    @Test
    fun `reset clears state`() {
        for (i in 0 until 500) processor.processSample(i.toFloat())
        processor.reset()
        val out = processor.processSample(0f)
        assertEquals("After reset, output of 0 should be ~0", 0f, out, 1f)
    }
}
