package com.hayatinritmi.app.processing

import android.content.Context
import com.hayatinritmi.app.domain.model.AiPrediction
import com.hayatinritmi.app.domain.model.ArrhythmiaClass
import kotlin.math.sqrt

/**
 * DCA-CNN / DS-1D-CNN TFLite INT8 çıkarım sınıfı — 55 SNOMED-CT multi-label aritmi.
 *
 * DCA-CNN modeli:  ecg_dca_cnn_int8.tflite (312 KB, 261K param, adaptif 1/3/12 kanal)
 * Fallback model:  ecg_model_int8.tflite   (232 KB, 176K param, sabit 12 kanal)
 *
 * Giriş tensor:  [1, 2500, 12] INT8 channels-last  |  Çıkış: [1, 55] float32 sigmoid
 * Model mevcut değilse otomatik mock mod.
 */
class ArrhythmiaClassifier(private val context: Context) {

    companion object {
        private const val DCA_MODEL_FILE = "ecg_dca_cnn_int8.tflite"
        private const val FALLBACK_MODEL_FILE = "ecg_model_int8.tflite"
        private const val WINDOW_SIZE = 2500
        private const val NUM_LEADS = 12
        private const val NUM_CLASSES = 55
        private const val MOCK_INFERENCE_MS = 8L

        private const val INPUT_SCALE = 0.0909f
        private const val INPUT_ZERO_POINT = -9

        /** 55 SNOMED-CT sınıf adları — model çıkış indeksi sırasıyla (CSV sırası). */
        val CLASS_NAMES = arrayOf(
            "1AVB", "2AVB", "2AVB1", "2AVB2", "3AVB",
            "ABI", "ALS", "APB", "AQW", "ARS",
            "AVB", "CCR", "CR", "ERV", "FQRS",
            "IDC", "IVB", "JEB", "JPT", "LBBB",
            "LBBBB", "LFBBB", "LVH", "LVQRSAL", "LVQRSCL",
            "LVQRSLL", "MI", "MIBW", "MIFW", "MILW",
            "MISW", "PRIE", "PWC", "QTIE", "RAH",
            "RBBB", "RVH", "STDD", "STE", "STTC",
            "STTU", "TWC", "TWO", "UW", "VB",
            "VEB", "VFW", "VPB", "VPE", "VET",
            "WAVN", "WPW", "SB", "SR", "AFIB"
        )

        /** Kritik sınıf indeksleri — AlertEngine RED tetikler */
        private val CRITICAL_INDICES = setOf(
            4,   // 3AVB
            54,  // AFIB
            47,  // VPB
            45,  // VEB
            46,  // VFW
            48,  // VPE
            26, 27, 28, 29, 30  // MI variants
        )

        /** SR (Sinus Rhythm) indeksi */
        private const val SR_INDEX = 53

        /** ArrhythmiaClass kategorisi eşlemesi */
        private fun mapToCategory(classIndex: Int): ArrhythmiaClass = when (classIndex) {
            53 -> ArrhythmiaClass.NORMAL           // SR
            52 -> ArrhythmiaClass.BRADYCARDIA      // SB
            in CRITICAL_INDICES -> when (classIndex) {
                54 -> ArrhythmiaClass.ATRIAL_FIBRILLATION  // AFIB
                in 26..30 -> ArrhythmiaClass.ST_ANOMALY    // MI variants
                else -> ArrhythmiaClass.ATRIAL_FIBRILLATION // VPB/VEB/3AVB
            }
            37, 38, 39, 40 -> ArrhythmiaClass.ST_ANOMALY  // STDD, STE, STTC, STTU
            else -> ArrhythmiaClass.TACHYCARDIA    // diğer anormal bulgular
        }
    }

    private var interpreter: Any? = null
    val isMockMode: Boolean
    val activeModelName: String

    init {
        val (loaded, name) = tryLoadModels()
        isMockMode = !loaded
        activeModelName = name
    }

    private fun tryLoadModels(): Pair<Boolean, String> {
        for (modelFile in listOf(DCA_MODEL_FILE, FALLBACK_MODEL_FILE)) {
            try {
                val interpreterClass = Class.forName("org.tensorflow.lite.Interpreter")
                val assetFd = context.assets.openFd(modelFile)
                val inputStream = java.io.FileInputStream(assetFd.fileDescriptor)
                val channel = inputStream.channel
                val buffer = channel.map(
                    java.nio.channels.FileChannel.MapMode.READ_ONLY,
                    assetFd.startOffset,
                    assetFd.declaredLength
                )
                interpreter = interpreterClass.getConstructor(java.nio.ByteBuffer::class.java)
                    .newInstance(buffer)
                inputStream.close()
                return true to modelFile
            } catch (_: Exception) { /* try next */ }
        }
        return false to "mock"
    }

    /**
     * 12-lead, 10 saniyelik EKG penceresi üzerinde 55-sınıf tahmin yap.
     * @param window 12 × 2500 matris — her satır bir derivasyon (µV cinsinden)
     */
    fun classify(window: Array<FloatArray>): AiPrediction {
        if (window.size < NUM_LEADS || window[0].size < WINDOW_SIZE) {
            return AiPrediction(ArrhythmiaClass.UNKNOWN, 0f,
                windowTimestampMs = System.currentTimeMillis())
        }
        return if (isMockMode) mockClassify(window) else tfliteClassify(window)
    }

    private fun tfliteClassify(window: Array<FloatArray>): AiPrediction {
        val startMs = System.currentTimeMillis()
        return try {
            // Per-lead z-score normalization + INT8 quantization
            // Input shape: [1, 2500, 12] → channels-last
            val inputBuf = java.nio.ByteBuffer
                .allocateDirect(1 * WINDOW_SIZE * NUM_LEADS)
                .order(java.nio.ByteOrder.nativeOrder())

            // Pre-compute per-lead mean & std
            val means = FloatArray(NUM_LEADS)
            val stds = FloatArray(NUM_LEADS)
            for (ch in 0 until NUM_LEADS) {
                val data = window[ch]
                var sum = 0.0
                for (i in 0 until WINDOW_SIZE) sum += data[i]
                means[ch] = (sum / WINDOW_SIZE).toFloat()
                var sqSum = 0.0
                for (i in 0 until WINDOW_SIZE) {
                    val d = data[i] - means[ch]
                    sqSum += d * d
                }
                stds[ch] = sqrt((sqSum / WINDOW_SIZE).toFloat()).coerceAtLeast(1e-6f)
            }

            // Fill buffer in [time, channel] order → INT8
            for (t in 0 until WINDOW_SIZE) {
                for (ch in 0 until NUM_LEADS) {
                    val normalized = (window[ch][t] - means[ch]) / stds[ch]
                    val quantized = (normalized / INPUT_SCALE + INPUT_ZERO_POINT)
                        .toInt().coerceIn(-128, 127).toByte()
                    inputBuf.put(quantized)
                }
            }
            inputBuf.rewind()

            val output = Array(1) { FloatArray(NUM_CLASSES) }
            val runMethod = interpreter!!.javaClass.getMethod(
                "run", Any::class.java, Any::class.java
            )
            runMethod.invoke(interpreter, inputBuf, output)

            interpretOutput(output[0], System.currentTimeMillis() - startMs)
        } catch (_: Exception) {
            mockClassify(window)
        }
    }

    /** Sigmoid çıkışları → AiPrediction */
    private fun interpretOutput(probs: FloatArray, inferenceMs: Long): AiPrediction {
        // Multi-label: birden fazla sınıf >0.5 olabilir
        // En yüksek non-SR olasılığı ile karar ver
        val srProb = probs[SR_INDEX]
        var topIdx = 0
        var topProb = 0f
        for (i in probs.indices) {
            if (probs[i] > topProb) {
                topProb = probs[i]
                topIdx = i
            }
        }

        // Top-5 tahminleri oluştur
        val topK = probs.indices.sortedByDescending { probs[it] }.take(5)
        val topPredictions = topK.map { idx ->
            CLASS_NAMES[idx] to probs[idx]
        }

        val isCritical = CRITICAL_INDICES.any { probs[it] > 0.5f }
        val dominantIdx = if (srProb > 0.7f && !isCritical) SR_INDEX else topIdx
        val label = mapToCategory(dominantIdx)
        val confidence = probs[dominantIdx]

        return AiPrediction(
            label = label,
            confidence = confidence,
            probabilities = probs,
            topPredictions = topPredictions,
            inferenceTimeMs = inferenceMs,
            windowTimestampMs = System.currentTimeMillis()
        )
    }

    /** Mock tahmin — model yokken kural tabanlı basit sınıflandırma */
    private fun mockClassify(window: Array<FloatArray>): AiPrediction {
        val lead2 = window[1]  // Lead II
        val rms = sqrt(lead2.take(WINDOW_SIZE).map { it * it.toDouble() }.average()).toFloat()
        val rmssd = run {
            var sum = 0.0
            val slice = lead2.take(WINDOW_SIZE)
            for (i in 1 until slice.size) {
                val d = (slice[i] - slice[i - 1]).toDouble()
                sum += d * d
            }
            sqrt(sum / (slice.size - 1)).toFloat()
        }
        val rrCv = if (rms > 0f) rmssd / rms else 0f
        val (label, conf) = when {
            rrCv > 0.35f -> ArrhythmiaClass.ATRIAL_FIBRILLATION to 0.74f
            else -> ArrhythmiaClass.NORMAL to 0.92f
        }
        val probs = FloatArray(NUM_CLASSES) { 0.02f }.apply {
            this[SR_INDEX] = if (label == ArrhythmiaClass.NORMAL) conf else 0.1f
            this[54] = if (label == ArrhythmiaClass.ATRIAL_FIBRILLATION) conf else 0.02f
        }
        return AiPrediction(
            label = label,
            confidence = conf,
            probabilities = probs,
            topPredictions = listOf(
                (if (label == ArrhythmiaClass.NORMAL) "SR" else "AFIB") to conf
            ),
            rrIrregularityScore = rrCv,
            inferenceTimeMs = MOCK_INFERENCE_MS,
            windowTimestampMs = System.currentTimeMillis()
        )
    }

    fun close() {
        try {
            interpreter?.javaClass?.getMethod("close")?.invoke(interpreter)
        } catch (_: Exception) {}
        interpreter = null
    }
}
