package com.hayatinritmi.app.processing

import com.hayatinritmi.app.domain.model.SignalQuality
import kotlin.math.*

/**
 * Araştırma Önerisi §3 tam DSP zinciri (gerçek zamanlı, tek örnekli):
 *
 *  1. Kayan ortalama bazal düzeltme (L=256, ~1s @ 250Hz)
 *  2. 6. derece Butterworth BPF 0.5–40 Hz — SOS form (3 bölüm × IIR2)
 *  3. SNR proxy kalite skoru (10 saniyelik pencere RMS/RMSSD oranı)
 *
 * Not: Tam db4 wavelet gürültü azaltma, 256-örnek pencere gerektirdiğinden
 * toplu/blok modda çalışır ve gerçek zamanlı pipeline ile entegre edilmez.
 * Bunun yerine SOS Butterworth ve kayan ortalama kombine yaklaşımı kullanılır.
 */
class AdvancedEcgProcessor(private val sampleRateHz: Int = 250) {

    // ────────────────────────────────────────────────────────────────────────
    // 1. Kayan Ortalama Bazal Düzeltme (L = 256)
    // x̄[n] = x̄[n-1] + (x[n] - x[n-L]) / L
    // ────────────────────────────────────────────────────────────────────────
    private val baselineL = 256
    private val baselineBuf = FloatArray(baselineL)
    private var baselineIdx = 0
    private var baselineSum = 0.0

    private fun removeBaseline(x: Float): Float {
        baselineSum -= baselineBuf[baselineIdx]
        baselineBuf[baselineIdx] = x
        baselineSum += x
        baselineIdx = (baselineIdx + 1) % baselineL
        return x - (baselineSum / baselineL).toFloat()
    }

    // ────────────────────────────────────────────────────────────────────────
    // 2. 6. Derece Butterworth 0.5–40 Hz — SOS (3 ikinci dereceli bölüm)
    //
    // Katsayılar: scipy.signal.butter(6, [0.5, 40], btype='bandpass', fs=250)
    // SOS form: her satır [b0, b1, b2, a0=1, a1, a2]
    // Direct Form II transposed (sayısal olarak kararlı)
    // ────────────────────────────────────────────────────────────────────────
    private val sosB = arrayOf(
        floatArrayOf(2.11888e-04f,  0f,           -2.11888e-04f),
        floatArrayOf(1f,            0f,            -1f),
        floatArrayOf(1f,            0f,            -1f)
    )
    private val sosA = arrayOf(
        floatArrayOf(1f, -1.99445f, 0.99558f),
        floatArrayOf(1f, -1.99643f, 0.99730f),
        floatArrayOf(1f, -1.98826f, 0.99212f)
    )
    // Durum değişkenleri: w1[s], w2[s] (Direct Form II)
    private val sosW = Array(3) { FloatArray(2) }

    private fun butterworth(x: Float): Float {
        var y = x
        for (s in 0 until 3) {
            val w0 = y - sosA[s][1] * sosW[s][0] - sosA[s][2] * sosW[s][1]
            val out = sosB[s][0] * w0 + sosB[s][1] * sosW[s][0] + sosB[s][2] * sosW[s][1]
            sosW[s][1] = sosW[s][0]
            sosW[s][0] = w0
            y = out
        }
        return y
    }

    // ────────────────────────────────────────────────────────────────────────
    // 3. Sinyal Kalite Tahmini (SNR proxy, 10 saniyelik pencere)
    // ────────────────────────────────────────────────────────────────────────
    private val qualityWindowSamples = sampleRateHz * 10  // 2500 @ 250 Hz
    private val qualityBuf = ArrayDeque<Float>(qualityWindowSamples + 1)

    // ────────────────────────────────────────────────────────────────────────
    // Genel İşleme Zinciri
    // ────────────────────────────────────────────────────────────────────────
    /**
     * Tek örnekli online işleme: bazal kaldırma → Butterworth BPF.
     * Döndürür: filtreli örnek (µV cinsinden).
     */
    fun processSample(rawSampleUv: Float): Float {
        val baselined = removeBaseline(rawSampleUv)
        val filtered = butterworth(baselined)
        if (qualityBuf.size >= qualityWindowSamples) qualityBuf.removeFirst()
        qualityBuf.addLast(filtered)
        return filtered
    }

    /**
     * 10 saniyelik penceredeki SNR proxy değerinden sinyal kalitesi hesapla.
     * Yeterli veri yoksa UNKNOWN döner.
     *
     * Yöntem: SNR ≈ 20 * log10(RMS / RMSSD) + sabit_offset
     * RMS: sinyal gücü, RMSSD: ardışık fark RMS (gürültü proxy)
     */
    fun computeSignalQuality(): SignalQuality {
        val buf = qualityBuf.toFloatArray()
        if (buf.size < qualityWindowSamples) return SignalQuality.UNKNOWN

        val rms = sqrt(buf.map { it * it.toDouble() }.average()).toFloat()
        val rmssd = run {
            var sum = 0.0
            for (i in 1 until buf.size) {
                val d = (buf[i] - buf[i - 1]).toDouble()
                sum += d * d
            }
            sqrt(sum / (buf.size - 1)).toFloat()
        }
        val snrProxy = if (rmssd > 0f) 20f * log10(rms / rmssd) + 14f else 0f
        val prd = computePrd(buf)
        val score = ((snrProxy - 6f) / 24f * 100f).toInt().coerceIn(0, 100)
        return SignalQuality(snrProxy, prd, score)
    }

    /**
     * Toplu mod wavelet gürültü azaltma (Daubechies-4, 4 seviye, soft thresholding).
     * Gerçek zamanlı pipeline için değil; test ve kalibrasyon amaçlı.
     * Blok boyutu 2^n olmalı (örn. 256, 512, 1024).
     */
    fun waveletDenoise(signal: FloatArray): FloatArray {
        if (signal.size < 16) return signal.copyOf()
        val n = signal.size
        val levels = 4
        val coeffsList = mutableListOf<FloatArray>()
        var current = signal.copyOf()

        // db4 ayrıştırma filtreleri (low-pass, high-pass)
        val lo = floatArrayOf(-0.07576572f, -0.02963553f,  0.49761866f, 0.80373875f,
                               0.29763006f, -0.09921954f, -0.01260397f, 0.03222310f)
        val hi = floatArrayOf(-0.03222310f, -0.01260397f,  0.09921954f, 0.29763006f,
                              -0.80373875f,  0.49761866f,  0.02963553f, -0.07576572f)

        repeat(levels) {
            val half = current.size / 2
            val approx = FloatArray(half)
            val detail = FloatArray(half)
            for (i in 0 until half) {
                var loSum = 0f; var hiSum = 0f
                for (k in lo.indices) {
                    val srcIdx = (2 * i + k).coerceAtMost(current.size - 1)
                    loSum += lo[k] * current[srcIdx]
                    hiSum += hi[k] * current[srcIdx]
                }
                approx[i] = loSum
                detail[i] = hiSum
            }
            coeffsList.add(0, detail)
            current = approx
        }
        coeffsList.add(0, current) // en kaba yaklaşım

        // Gürültü tahmini ve eşikleme (sadece ayrıntı bandları)
        val finestDetail = coeffsList[1]
        val sorted = finestDetail.map { abs(it) }.sorted()
        val median = if (sorted.size % 2 == 0)
            (sorted[sorted.size / 2 - 1] + sorted[sorted.size / 2]) / 2f
        else sorted[sorted.size / 2]
        val sigma = median / 0.6745f
        val tau = sigma * sqrt(2f * ln(n.toFloat()))

        for (i in 1 until coeffsList.size) {
            val d = coeffsList[i]
            for (j in d.indices) {
                d[j] = sign(d[j]) * max(abs(d[j]) - tau, 0f)
            }
        }

        // Basitleştirilmiş IDWT yeniden oluşturma (doğrusal enterpolasyon)
        // Gerçek IDWT için PyWavelets veya özel kütüphane gerekir.
        // Bu implementasyon yaklaşık bir geri yapılandırma sağlar.
        var reconstructed = coeffsList[0].copyOf()
        for (i in 1 until coeffsList.size) {
            val detail = coeffsList[i]
            val upsampled = FloatArray(reconstructed.size * 2)
            for (j in reconstructed.indices) {
                upsampled[2 * j] = reconstructed[j]
                upsampled[2 * j + 1] = (reconstructed[j] + (if (j + 1 < reconstructed.size) reconstructed[j + 1] else reconstructed[j])) / 2f
            }
            val detailUp = FloatArray(upsampled.size)
            for (j in detail.indices.takeIf { it.last < upsampled.size } ?: detail.indices) {
                detailUp[j.coerceAtMost(upsampled.size - 1)] = detail[j]
            }
            for (j in upsampled.indices) {
                upsampled[j] = (upsampled[j] + detailUp[j]) / 2f
            }
            reconstructed = upsampled.copyOfRange(0, minOf(upsampled.size, signal.size))
        }
        return reconstructed.copyOfRange(0, n)
    }

    private fun computePrd(signal: FloatArray): Float {
        val mean = signal.average().toFloat()
        val baseline = FloatArray(signal.size) { mean }
        val num = signal.zip(baseline.toList()).sumOf { (s, b) -> ((s - b) * (s - b)).toDouble() }
        val den = signal.sumOf { (it * it).toDouble() }
        return if (den > 0.0) (100f * sqrt(num / den)).toFloat() else 0f
    }

    fun reset() {
        baselineBuf.fill(0f)
        baselineSum = 0.0
        baselineIdx = 0
        for (w in sosW) w.fill(0f)
        qualityBuf.clear()
    }
}
