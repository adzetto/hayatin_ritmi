package com.hayatinritmi.app.processing

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import kotlin.math.PI
import kotlin.math.sin

class EcgFilterTest {

    private lateinit var filter: EcgFilter

    @Before
    fun setup() {
        filter = EcgFilter(sampleRateHz = 250, notchFreqHz = 50f)
    }

    @Test
    fun `DC input is attenuated by HPF`() {
        var last = 0f
        repeat(1000) { last = filter.filter(100f) }
        assertTrue("HPF should attenuate DC (output=$last)", kotlin.math.abs(last) < 50f)
    }

    @Test
    fun `50Hz sine is attenuated by notch`() {
        val fs = 250
        val samples = (0 until 2000).map { sin(2 * PI * 50.0 / fs * it).toFloat() }

        // Let filter settle first
        for (i in 0 until 500) filter.filter(samples[i])

        var maxOutput = 0f
        for (i in 500 until samples.size) {
            val out = kotlin.math.abs(filter.filter(samples[i]))
            if (out > maxOutput) maxOutput = out
        }
        assertTrue("50Hz should be attenuated below input amplitude (max=$maxOutput)", maxOutput < 0.8f)
    }

    @Test
    fun `low frequency signal passes through`() {
        val fs = 250
        val freq = 5.0  // 5 Hz — well within passband
        val samples = (0 until 1000).map { sin(2 * PI * freq / fs * it).toFloat() }

        var maxOutput = 0f
        for (s in samples) {
            val out = kotlin.math.abs(filter.filter(s))
            if (out > maxOutput) maxOutput = out
        }
        assertTrue("5Hz should pass through (max=$maxOutput)", maxOutput > 0.3f)
    }

    @Test
    fun `reset clears internal state`() {
        for (i in 0 until 100) filter.filter(i.toFloat())
        filter.reset()
        val out = filter.filter(0f)
        assertEquals("After reset, output of 0 should be ~0", 0f, out, 0.01f)
    }

    @Test
    fun `high frequency is attenuated by LPF`() {
        val fs = 250
        val freq = 100.0  // well above 40 Hz cutoff
        val samples = (0 until 1000).map { sin(2 * PI * freq / fs * it).toFloat() }

        var maxOutput = 0f
        for (s in samples) {
            val out = kotlin.math.abs(filter.filter(s))
            if (out > maxOutput) maxOutput = out
        }
        assertTrue("100Hz should be attenuated (max=$maxOutput)", maxOutput < 0.5f)
    }
}
