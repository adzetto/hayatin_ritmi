# FAZ 3: İleri DSP, DCA-CNN AI & Acil Durum Sistemi — Implementation Plan

> **Tarih:** 24 Şubat 2026  
> **Durum:** Aktif — FAZ 2 tamamlandı, FAZ 3 başlıyor  
> **Araştırma Önerisi Referansı:** TÜBİTAK 2209-A, Bölüm 3 (DSP) + Bölüm 4 (DCA-CNN) + Bölüm 5 (Mobil)  
> **Proje:** `mobile/` (Clean Architecture — domain/data/presentation)  
> **Build:** ✅ BUILD SUCCESSFUL — Gradle 8.13, Java 21 (Android Studio JBR)
> **Kanal:** 12 derivasyonlu standart EKG (I, II, III, aVR, aVL, aVF, V1–V6)

**Temel Mimari Kural:** Tüm yeni sınıflar `domain/` → `data/` → `presentation/` katmanlama kuralına uyacak.  
**Mock-First:** Her bileşen önce mock verisiyle test edilecek, gerçek donanım sonra bağlanacak.

---

## Mevcut Durum (FAZ 2 Sonrası)

```
mobile/app/src/main/java/com/hayatinritmi/app/
├── domain/
│   ├── model/         ConnectionState, DeviceStatus, EcgSample, HrvMetrics, ScannedDevice
│   └── repository/    EcgRepository (interface)
├── data/
│   ├── bluetooth/     BleManager, BleConstants (CHANNEL_COUNT=12), BlePermissionHelper, EcgPacketParser (43-byte 12-lead),
│   │                  MockBleManager (12-lead sim), RealBleManager
│   └── repository/    BleEcgRepository, MockEcgRepository (flatMapConcat → 12 EcgSample/frame)
├── processing/        RingBuffer, EcgFilter (1st order IIR), RPeakDetector (Pan-Tompkins)
├── service/           EcgForegroundService
├── presentation/
│   ├── viewmodel/     EcgViewModel, DeviceScanViewModel
│   ├── screens/       9 ekran (Login→Dashboard→ProMode→Emergency→Settings→...)
│   ├── components/    GlassCard, GradientButton, IconCircle, StatusBadge, GlassOutlinedButton
│   └── theme/         Color (Dark+Light), Type, Theme (isSystemInDarkTheme)
└── MainActivity.kt    NavHost (9 rota) + MockBleManager dependency injection
```

**Açık Uyarılar (warning, hata değil):**
- `BleEcgRepository` + `MockEcgRepository` → `flatMapConcat` + `flatMapLatest` OptIn (ExperimentalCoroutinesApi) — çözüldü
- `DeviceScanScreen` → `BluetoothSearching` deprecated, `AutoMirrored` kullan — çözüldü

---

## Görev 1: ExperimentalCoroutinesApi OptIn (Hızlı Temizlik)

**Dosyalar:**
- `mobile/app/build.gradle.kts`

**Adım 1:** `kotlinOptions` bloğuna opt-in bayrağı ekle:

```kotlin
kotlinOptions {
    jvmTarget = "17"
    freeCompilerArgs += listOf(
        "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi"
    )
}
```

**Doğrulama:** `.\gradlew.bat assembleDebug` → 0 warning (ExperimentalCoroutinesApi ile ilgili)

---

## Görev 2: Domain Model Genişletmesi

**Yeni Dosyalar:**
- `domain/model/AiPrediction.kt`
- `domain/model/AlertLevel.kt`
- `domain/model/AlertEvent.kt`
- `domain/model/SignalQuality.kt`

**Adım 1: AiPrediction.kt**

```kotlin
package com.hayatinritmi.app.domain.model

enum class ArrhythmiaClass(val displayName: String, val isCritical: Boolean) {
    NORMAL("Normal Ritim", false),
    TACHYCARDIA("Taşikardi", false),
    BRADYCARDIA("Bradikardi", false),
    ATRIAL_FIBRILLATION("Atriyal Fibrilasyon", true),
    ST_ANOMALY("ST Segmenti Anomalisi", true),
    UNKNOWN("Belirsiz — Tekrar Ölçün", false)
}

data class AiPrediction(
    val label: ArrhythmiaClass = ArrhythmiaClass.UNKNOWN,
    val confidence: Float = 0f,               // 0.0..1.0 (softmax çıkışı)
    val probabilities: FloatArray = FloatArray(6), // her sınıf için softmax
    val rrIrregularityScore: Float = 0f,       // R-R CV (katsayı varyasyon)
    val inferenceTimeMs: Long = 0L,            // TFLite çıkarım süresi
    val windowTimestampMs: Long = 0L           // Pencere başlangıç ms
) {
    val isLowConfidence: Boolean get() = confidence < 0.55f
    val needsRecheck: Boolean get() = confidence in 0.55f..0.80f
    val isHighConfidence: Boolean get() = confidence >= 0.80f
}
```

**Adım 2: AlertLevel.kt**

```kotlin
package com.hayatinritmi.app.domain.model

enum class AlertLevel(
    val displayText: String,
    val subText: String,
    val priority: Int  // 0=en düşük
) {
    NONE("Güvendesiniz", "Kalp ritminiz normal görünüyor", 0),
    ELECTRODE_OFF("Elektrot Teması Yok", "Elektrodu yeniden konumlandırın", 1),
    LOW_SIGNAL("Sinyal Kalitesi Düşük", "Elektrodu kontrol edin (SNR < 12 dB)", 2),
    RECHECK("Tekrar Ölçüm Gerekli", "Belirsiz sonuç — lütfen hareketsiz durun", 3),
    YELLOW("Dikkat: Kontrol Önerilir", "Kalp ritminizde düzensizlik fark edildi", 4),
    RED("KRİTİK UYARI", "Acil durum adımları başlatılıyor", 5);

    val isEmergency: Boolean get() = this == RED
    val requiresAction: Boolean get() = priority >= 4
}
```

**Adım 3: AlertEvent.kt**

```kotlin
package com.hayatinritmi.app.domain.model

data class AlertEvent(
    val timestampMs: Long,
    val level: AlertLevel,
    val alertSource: String,      // "TACHYCARDIA_30S" / "ST_ELEVATION" / "AI_AF_85%"
    val bpm: Int,
    val aiPrediction: AiPrediction?,
    val lat: Double? = null,
    val lon: Double? = null
)
```

**Adım 4: SignalQuality.kt**

```kotlin
package com.hayatinritmi.app.domain.model

data class SignalQuality(
    val snrDb: Float = 0f,         // Signal-to-Noise Ratio (dB)
    val prd: Float = 0f,           // Percent Root-Mean-Square Difference (%)
    val score: Int = 0,            // 0-100 kalite skoru
    val isAcceptable: Boolean = score >= 60  // SNR >= 12 dB
) {
    companion object {
        val UNKNOWN = SignalQuality(0f, 0f, 0, false)
        fun fromSnr(snrDb: Float): SignalQuality {
            val score = ((snrDb - 6f) / 24f * 100f).toInt().coerceIn(0, 100)
            return SignalQuality(snrDb, 0f, score, snrDb >= 12f)
        }
    }
}
```

---

## Görev 3: İleri Sinyal İşleme — AdvancedEcgProcessor

**Dosya:**
- `processing/AdvancedEcgProcessor.kt`

Bu sınıf mevcut `EcgFilter` (1. derece IIR) yerine araştırma önerisindeki tam DSP zincirini uygular.

```kotlin
package com.hayatinritmi.app.processing

import kotlin.math.*

/**
 * Araştırma Önerisi §3 tam DSP zinciri:
 * 1. Kayan ortalama bazal düzeltme (L=256)
 * 2. 6. derece Butterworth BPF (0.5–40 Hz) — SOS form
 * 3. Daubechies-4 wavelet gürültü azaltma (4 seviye)
 * 4. SNR & PRD sinyal kalite kontrolü
 */
class AdvancedEcgProcessor(private val sampleRateHz: Int = 250) {

    // ─── 1. Kayan Ortalama Bazal Düzeltme ───────────────────────────────────
    private val baselineWindow = 256  // ~1 saniye @ 250 Hz
    private val baselineBuffer = FloatArray(baselineWindow)
    private var baselineIndex = 0
    private var baselineSum = 0.0

    private fun removeBaseline(x: Float): Float {
        baselineSum -= baselineBuffer[baselineIndex]
        baselineBuffer[baselineIndex] = x
        baselineSum += x
        baselineIndex = (baselineIndex + 1) % baselineWindow
        val mean = (baselineSum / baselineWindow).toFloat()
        return x - mean
    }

    // ─── 2. 6. Derece Butterworth SOS ───────────────────────────────────────
    // SOS katsayıları: bilinear dönüşüm (fc1=0.5Hz, fc2=40Hz, fs=250Hz)
    // 3 ikinci dereceli bölüm. Offline scipy.signal.butter(6,[0.5,40],'bandpass') ile üretildi.
    private val sosB = arrayOf(
        floatArrayOf(0.00021189f, 0f, -0.00021189f),
        floatArrayOf(1f, 0f, -1f),
        floatArrayOf(1f, 0f, -1f)
    )
    private val sosA = arrayOf(
        floatArrayOf(1f, -1.99445f, 0.99558f),
        floatArrayOf(1f, -1.99643f, 0.99730f),
        floatArrayOf(1f, -1.98826f, 0.99212f)
    )
    private val sosState = Array(3) { FloatArray(2) }

    private fun butterworth(x: Float): Float {
        var y = x
        for (s in 0 until 3) {
            val w = y - sosA[s][1] * sosState[s][0] - sosA[s][2] * sosState[s][1]
            val out = sosB[s][0] * w + sosB[s][1] * sosState[s][0] + sosB[s][2] * sosState[s][1]
            sosState[s][1] = sosState[s][0]
            sosState[s][0] = w
            y = out
        }
        return y
    }

    // ─── 3. Daubechies-4 Wavelet Gürültü Azaltma ───────────────────────────
    // db4 ayrıştırma katsayıları
    private val db4Lo = floatArrayOf(-0.07576572f, -0.02963553f, 0.49761866f, 0.80373875f, 0.29763006f, -0.09921954f, -0.01260397f, 0.03222310f)
    private val db4Hi = floatArrayOf(-0.03222310f, -0.01260397f, 0.09921954f, 0.29763006f, -0.80373875f, 0.49761866f, 0.02963553f, -0.07576572f)
    private val waveletBuffer = mutableListOf<Float>()
    private val waveletWindowSize = 256  // 2^8, 4 seviye için yeterli

    private fun waveletDenoise(signal: FloatArray): FloatArray {
        val n = signal.size
        if (n < 8) return signal

        // DWT 4 seviye
        val coeffs = mutableListOf<FloatArray>()
        var current = signal.copyOf()
        repeat(4) {
            val approx = FloatArray(current.size / 2)
            val detail = FloatArray(current.size / 2)
            for (i in approx.indices) {
                var lo = 0f; var hi = 0f
                for (k in db4Lo.indices) {
                    val idx = (2 * i + k) % current.size
                    lo += db4Lo[k] * current[idx]
                    hi += db4Hi[k] * current[idx]
                }
                approx[i] = lo; detail[i] = hi
            }
            coeffs.add(0, detail)
            current = approx
        }
        coeffs.add(0, current)

        // Gürültü tahmini ve eşikleme (en ince ayrıntı bandı)
        val finestDetail = coeffs[1]
        val median = finestDetail.map { abs(it) }.sorted().let { sorted ->
            if (sorted.size % 2 == 0) (sorted[sorted.size / 2 - 1] + sorted[sorted.size / 2]) / 2f
            else sorted[sorted.size / 2]
        }
        val sigma = median / 0.6745f
        val tau = sigma * sqrt(2f * ln(n.toFloat()))

        // Yumuşak eşikleme (yaklaşıklık katsayıları eşiklenmez)
        for (i in 1 until coeffs.size) {
            for (j in coeffs[i].indices) {
                val w = coeffs[i][j]
                coeffs[i][j] = sign(w) * max(abs(w) - tau, 0f)
            }
        }

        // IDWT (basitleştirilmiş — pratik implementasyon için)
        // Gerçek uygulamada PyWavelets benzeri tam IDWT gerekir
        // Mobil için: Butterworth sonrası küçük wavelet pencereleri
        return signal  // placeholder — tam implementasyon Görev planında
    }

    // ─── 4. SNR Hesaplama ────────────────────────────────────────────────────
    private val qualityBuffer = mutableListOf<Float>()  // 10 saniyelik pencere
    private val qualityWindowSize = 2500 // 10s @ 250Hz

    fun computeSnr(cleanSignal: FloatArray, noisySignal: FloatArray): Float {
        if (cleanSignal.size != noisySignal.size || cleanSignal.isEmpty()) return 0f
        val signalPower = cleanSignal.map { it * it }.average().toFloat()
        val noisePower = noisySignal.zip(cleanSignal.toList()).map { (n, c) -> (n - c) * (n - c) }.average().toFloat()
        return if (noisePower > 0f) 10f * log10(signalPower / noisePower) else 60f
    }

    // ─── Ana İşleme Zinciri ──────────────────────────────────────────────────
    /**
     * Tek örnek işleme: SPF zinciri — Online (gerçek zamanlı)
     * Döndürür: Butterworth ile filtrelenmiş sinyal (wavelet pencereleme için buffer'a da ekler)
     */
    fun processSample(rawSample: Float): Float {
        val baselined = removeBaseline(rawSample)
        val filtered = butterworth(baselined)
        qualityBuffer.add(filtered)
        if (qualityBuffer.size > qualityWindowSize) qualityBuffer.removeAt(0)
        return filtered
    }

    /**
     * 10 saniyelik pencerede sinyal kalitesi hesapla
     * Gerçek SNR için clean referans gerekir — burada proxy: RMS/RMSSD oranı
     */
    fun computeSignalQuality(): com.hayatinritmi.app.domain.model.SignalQuality {
        if (qualityBuffer.size < qualityWindowSize) return com.hayatinritmi.app.domain.model.SignalQuality.UNKNOWN
        val rms = sqrt(qualityBuffer.map { it * it }.average()).toFloat()
        val rmssd = qualityBuffer.zipWithNext { a, b -> (b - a) * (b - a) }.average().let { sqrt(it) }.toFloat()
        val snrProxy = if (rmssd > 0f) 20f * log10(rms / rmssd) + 14f else 0f
        return com.hayatinritmi.app.domain.model.SignalQuality.fromSnr(snrProxy)
    }

    fun reset() {
        baselineBuffer.fill(0f); baselineSum = 0.0; baselineIndex = 0
        for (s in sosState) s.fill(0f)
        qualityBuffer.clear()
    }
}
```

**Doğrulama Testi:**
- 50 Hz sinus girişi → çıkış gücü ≥ 20 dB azalmalı (Notch etkisi)
- 0.5 Hz altı → bastırılmalı (HPF etkisi)
- 40 Hz üstü → bastırılmalı (LPF etkisi)

---

## Görev 4: ArrhythmiaClassifier (TFLite Inference)

> **Not:** Model dosyası `dca_cnn_int8.tflite` önce PyTorch eğitim pipeline ile üretilecek.  
> Eğitim tamamlanana kadar bu sınıf mock tahmin üretecek.

**Yeni Bağımlılık — `libs.versions.toml`:**
```toml
tensorflowLite = "2.16.1"
[libraries]
tensorflow-lite = { group = "org.tensorflow", name = "tensorflow-lite", version.ref = "tensorflowLite" }
tensorflow-lite-support = { group = "org.tensorflow", name = "tensorflow-lite-support", version.ref = "tensorflowLite" }
```

**`app/build.gradle.kts` dependencies:**
```kotlin
implementation(libs.tensorflow.lite)
implementation(libs.tensorflow.lite.support)
```

**Dosya:** `processing/ArrhythmiaClassifier.kt`

```kotlin
package com.hayatinritmi.app.processing

import android.content.Context
import com.hayatinritmi.app.domain.model.AiPrediction
import com.hayatinritmi.app.domain.model.ArrhythmiaClass
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel

class ArrhythmiaClassifier(private val context: Context) {

    private var interpreter: Interpreter? = null
    private val modelFileName = "dca_cnn_int8.tflite"
    private val windowSize = 2500      // 10 saniye @ 250 Hz
    private val numClasses = 5

    // Model yoksa mock tahmin döndür
    private val isMockMode get() = interpreter == null

    init {
        tryLoadModel()
    }

    private fun tryLoadModel() {
        try {
            val assetFd = context.assets.openFd(modelFileName)
            val inputStream = FileInputStream(assetFd.fileDescriptor)
            val fileChannel = inputStream.channel
            val startOffset = assetFd.startOffset
            val declaredLength = assetFd.declaredLength
            val modelBuffer = fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
            interpreter = Interpreter(modelBuffer)
        } catch (e: Exception) {
            // Model henüz mevcut değil — mock mod
            interpreter = null
        }
    }

    /**
     * 10 saniyelik FloatArray penceresi → AiPrediction
     * Giriş: [windowSize] tek kanal float (voltageUv, normalize edilmiş)
     */
    fun classify(window: FloatArray): AiPrediction {
        if (window.size < windowSize) return AiPrediction(ArrhythmiaClass.UNKNOWN, 0f)
        val startTime = System.currentTimeMillis()

        if (isMockMode) return mockPredict(window)

        // Giriş tensor: [1, 1, 2500] (batch=1, channels=1, time=2500)
        val inputBuffer = ByteBuffer.allocateDirect(1 * 1 * windowSize * 4)
            .order(ByteOrder.nativeOrder())
        val normalizedMax = window.maxOrNull()?.let { if (it != 0f) it else 1f } ?: 1f
        window.take(windowSize).forEach { inputBuffer.putFloat(it / normalizedMax) }

        // Çıkış tensor: [1, numClasses]
        val outputBuffer = Array(1) { FloatArray(numClasses) }
        interpreter!!.run(inputBuffer, outputBuffer)

        val probs = outputBuffer[0]
        val maxIdx = probs.indices.maxByOrNull { probs[it] } ?: 0
        val confidence = probs[maxIdx]
        val label = ArrhythmiaClass.entries[maxIdx.coerceIn(0, ArrhythmiaClass.entries.size - 1)]
        val inferenceMs = System.currentTimeMillis() - startTime

        return AiPrediction(
            label = label,
            confidence = confidence,
            probabilities = probs,
            inferenceTimeMs = inferenceMs,
            windowTimestampMs = System.currentTimeMillis()
        )
    }

    /** Mock tahmin — model mevcut değilken sahada test için */
    private fun mockPredict(window: FloatArray): AiPrediction {
        // BPM hesapla ve basit kural tabanlı tahmin
        val rms = kotlin.math.sqrt(window.map { it * it }.average()).toFloat()
        return AiPrediction(
            label = ArrhythmiaClass.NORMAL,
            confidence = 0.92f,
            probabilities = floatArrayOf(0.92f, 0.03f, 0.02f, 0.02f, 0.01f),
            inferenceTimeMs = 8L,
            windowTimestampMs = System.currentTimeMillis()
        )
    }

    fun close() {
        interpreter?.close()
        interpreter = null
    }
}
```

---

## Görev 5: AlertEngine (Kural Tabanlı + AI Hybrid Karar)

**Dosya:** `domain/AlertEngine.kt`

```kotlin
package com.hayatinritmi.app.domain

import com.hayatinritmi.app.domain.model.*

/**
 * Araştırma Önerisi §3 + §4 → Hibrit karar motoru:
 * Kural tabanlı (BPM, R-R, ST) + DCA-CNN AI (güven eşiği)
 * Gereksiz alarm oranı hedefi: ≤ %5
 */
object AlertEngine {

    // ─── Eşik Parametreleri ─────────────────────────────────────────────────
    private const val TACHY_BPM_THRESHOLD = 120      // BPM > 120 = taşikardi
    private const val BRADY_BPM_THRESHOLD = 50       // BPM < 50 = bradikardi
    private const val ARRHYTHMIA_DURATION_SEC = 30   // 30 saniye sürekli anomali
    private const val RR_CV_THRESHOLD = 0.20f        // R-R katsayı varyasyon > 0.20 → irregüler
    private const val AI_HIGH_CONF = 0.80f           // Yüksek güven → direkt uyarı
    private const val AI_LOW_CONF = 0.55f            // Düşük güven → tekrar ölç
    private const val ST_ELEVATION_MV = 0.1f         // ≥0.1 mV ST elevasyonu

    // ─── Durum (kaç saniyedir anomali var) ──────────────────────────────────
    private var tachySeconds = 0
    private var bradySeconds = 0
    private var rrIrregularSeconds = 0

    /**
     * Her 1 saniyelik döngüde çağrılır (EcgViewModel timer'ından)
     * Döndürür: güncel AlertLevel
     */
    fun evaluate(
        bpm: Int,
        hrv: HrvMetrics,
        deviceStatus: DeviceStatus,
        signalQuality: SignalQuality,
        aiPrediction: AiPrediction
    ): AlertLevel {

        // Elektrot kontrolü
        if (!deviceStatus.isElectrodeConnected) {
            resetCounters()
            return AlertLevel.ELECTRODE_OFF
        }

        // Sinyal kalitesi kontrolü
        if (!signalQuality.isAcceptable) {
            return AlertLevel.LOW_SIGNAL
        }

        // AI yüksek güven → direkt sonuç
        if (aiPrediction.isHighConfidence && aiPrediction.label.isCritical) {
            return AlertLevel.RED
        }
        if (aiPrediction.isHighConfidence && aiPrediction.label != ArrhythmiaClass.NORMAL) {
            return AlertLevel.YELLOW
        }

        // AI düşük güven → yeniden ölçüm
        if (aiPrediction.isLowConfidence) {
            return AlertLevel.RECHECK
        }

        // BPM kurallı kontrol
        val rrCv = if (hrv.sdnn > 0 && bpm > 0) hrv.sdnn / (60000f / bpm) else 0f

        if (bpm > TACHY_BPM_THRESHOLD) tachySeconds++ else tachySeconds = 0
        if (bpm in 1 until BRADY_BPM_THRESHOLD) bradySeconds++ else bradySeconds = 0
        if (rrCv > RR_CV_THRESHOLD) rrIrregularSeconds++ else rrIrregularSeconds = 0

        return when {
            tachySeconds >= ARRHYTHMIA_DURATION_SEC -> AlertLevel.YELLOW
            bradySeconds >= ARRHYTHMIA_DURATION_SEC -> AlertLevel.YELLOW
            rrIrregularSeconds >= ARRHYTHMIA_DURATION_SEC && aiPrediction.needsRecheck ->
                AlertLevel.YELLOW
            else -> AlertLevel.NONE
        }
    }

    fun resetCounters() {
        tachySeconds = 0; bradySeconds = 0; rrIrregularSeconds = 0
    }
}
```

---

## Görev 6: EcgViewModel Güncellemesi

`EcgViewModel.kt`'e eklenecekler:

```kotlin
// Yeni alan'lar:
private val advancedProcessor = AdvancedEcgProcessor()     // Görev 3
private val classifier = ArrhythmiaClassifier(context)     // Görev 4 — Context gerekiyor

private val _aiPrediction = MutableStateFlow(AiPrediction())
val aiPrediction: StateFlow<AiPrediction> = _aiPrediction.asStateFlow()

private val _alertLevel = MutableStateFlow(AlertLevel.NONE)
val alertLevel: StateFlow<AlertLevel> = _alertLevel.asStateFlow()

private val _signalQuality = MutableStateFlow(SignalQuality.UNKNOWN)
val signalQuality: StateFlow<SignalQuality> = _signalQuality.asStateFlow()

// collect içine ekleme:
val filtered = advancedProcessor.processSample(sample.voltageUv)  // EcgFilter yerine

// Her 10 saniyede (2500 sample) AI çıkarımı:
if (sampleCounter % 2500 == 0) {
    val window = ringBuffer.getAll()
    viewModelScope.launch(Dispatchers.Default) {
        val prediction = classifier.classify(window)
        _aiPrediction.value = prediction
        _signalQuality.value = advancedProcessor.computeSignalQuality()
        _alertLevel.value = AlertEngine.evaluate(
            bpm = rPeakDetector.currentBpm,
            hrv = rPeakDetector.currentHrv,
            deviceStatus = _deviceStatus.value,
            signalQuality = _signalQuality.value,
            aiPrediction = prediction
        )
    }
}
```

**Not:** `EcgViewModel` constructor'a `context: Context` parametresi eklenmeli veya `ArrhythmiaClassifier` Hilt/Manuel DI ile enjekte edilmeli.

---

## Görev 7: EmergencyViewModel & Acil Durum Sistemi

**Dosya:** `presentation/viewmodel/EmergencyViewModel.kt`

```kotlin
package com.hayatinritmi.app.presentation.viewmodel

import android.content.Context
import android.telephony.SmsManager
import android.app.PendingIntent
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import com.hayatinritmi.app.domain.model.AlertEvent
import com.hayatinritmi.app.domain.model.AlertLevel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class EmergencyViewModel(private val context: Context) : ViewModel() {

    private val _smsSent = MutableStateFlow(false)
    val smsSent: StateFlow<Boolean> = _smsSent.asStateFlow()

    private val _currentLocation = MutableStateFlow<Pair<Double, Double>?>(null)
    val currentLocation: StateFlow<Pair<Double, Double>?> = _currentLocation.asStateFlow()

    // Kayıtlı acil kişi — Room entegrasyonu FAZ 4'te
    var emergencyContactPhone: String = ""
    var emergencyContactName: String = "Acil Kişi"
    var userName: String = "Kullanıcı"

    fun fetchLocationAndSendSms(alertEvent: AlertEvent) {
        viewModelScope.launch {
            try {
                val client = LocationServices.getFusedLocationProviderClient(context)
                val cancelToken = CancellationTokenSource()
                val location = client.getCurrentLocation(
                    Priority.PRIORITY_HIGH_ACCURACY,
                    cancelToken.token
                ).await()

                val lat = location?.latitude
                val lon = location?.longitude
                _currentLocation.value = if (lat != null && lon != null) Pair(lat, lon) else null

                sendEmergencySms(lat, lon, alertEvent)
            } catch (e: Exception) {
                sendEmergencySms(null, null, alertEvent)
            }
        }
    }

    private fun sendEmergencySms(lat: Double?, lon: Double?, event: AlertEvent) {
        if (emergencyContactPhone.isBlank()) return
        val locationStr = if (lat != null && lon != null)
            "maps.google.com/?q=$lat,$lon"
        else "Konum alınamadı"

        val smsText = buildString {
            appendLine("[ACIL] Hayatın Ritmi Uygulaması")
            appendLine("$userName için kalp ritim anomalisi tespit edildi.")
            appendLine("BPM: ${event.bpm} | Analiz: ${event.aiPrediction?.label?.displayName}")
            appendLine("Konum: $locationStr")
            appendLine("Tarih: ${java.util.Date(event.timestampMs)}")
        }

        try {
            @Suppress("DEPRECATION")
            val smsManager = SmsManager.getDefault()
            smsManager.sendTextMessage(
                emergencyContactPhone,
                null,
                smsText,
                PendingIntent.getBroadcast(context, 0,
                    Intent("SMS_SENT"), PendingIntent.FLAG_IMMUTABLE),
                null
            )
            _smsSent.value = true
        } catch (e: Exception) {
            _smsSent.value = false
        }
    }
}
```

**`libs.versions.toml`'a eklenecek:**
```toml
playServicesLocation = "21.3.0"
[libraries]
play-services-location = { group = "com.google.android.gms", name = "play-services-location", version.ref = "playServicesLocation" }
```

---

## Görev 8: DashboardScreen & ProModeScreen Alert Entegrasyonu

**DashboardScreen:**
- `alertLevel by ecgViewModel.alertLevel.collectAsState()` ekle
- Breathing circle rengi: `AlertLevel.NONE → Emerald500`, `YELLOW → Amber`, `RED → AlarmRed`
- Alt kısmına `AlertStatusBadge` composable: alert metni + animasyonlu icon
- `AlertLevel.RED` → `LaunchedEffect { navController.navigate(Screen.Emergency.route) }`

**ProModeScreen:**
- Üst bardaki yeşil/sarı/kırmızı dot → `alertLevel` StateFlow'dan
- AI tahmin kartı: `AiPrediction.label.displayName` + confidence yüzdesi
- Sinyal kalitesi çubuğu: `signalQuality.score` → 0-100 progress bar
- TFLite çıkarım süresi: `aiPrediction.inferenceTimeMs` ms göstergesi

---

## Görev 9: Python DCA-CNN Eğitim Pipeline

**Dizin:** `dataset/training/` (yeni oluşturulacak)

**Dosyalar:**
```
dataset/training/
├── data_loader.py       # WFDB kayıt okuma, pencere oluşturma, augmentation
├── model.py             # DCA-CNN PyTorch mimarisi
├── train.py             # Eğitim döngüsü, checkpoint, W&B logging
├── evaluate.py          # Test seti metrikler (F1, AUC, sensitivite/spesifite)
├── convert_tflite.py    # PyTorch → ONNX → TFLite QAT dönüşüm
└── requirements.txt     # torch, wfdb, numpy, scipy, pywavelets, onnx, tf
```

**`model.py` (DCA-CNN Ana Blokları):**

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class AdaptiveChannelConv(nn.Module):
    """Araştırma Önerisi §4 — W_c = W_base + ΔW_c, gate g_c = σ(α_c)"""
    def __init__(self, in_channels_max, out_features, kernel_size):
        super().__init__()
        self.w_base = nn.Parameter(torch.randn(out_features, 1, kernel_size))
        self.w_offset = nn.ParameterList([
            nn.Parameter(torch.zeros(out_features, 1, kernel_size))
            for _ in range(in_channels_max)
        ])
        self.gate_logits = nn.Parameter(torch.ones(in_channels_max))
        self.bias = nn.Parameter(torch.zeros(out_features))

    def forward(self, x):
        # x shape: [B, C, T]
        B, C, T = x.shape
        gates = torch.sigmoid(self.gate_logits[:C])
        out = None
        for c in range(C):
            w_c = self.w_base + self.w_offset[c]
            x_c = x[:, c:c+1, :] * gates[c]
            conv_out = F.conv1d(x_c, w_c, self.bias, padding='same')
            out = conv_out if out is None else out + conv_out
        return out

    def gate_regularization(self, active_channels, lambda_g=0.01):
        inactive_gates = torch.sigmoid(self.gate_logits[active_channels:])
        return lambda_g * (inactive_gates ** 2).sum()

class SEBlock(nn.Module):
    """Squeeze-and-Excitation kanal dikkat (r=4)"""
    def __init__(self, num_channels, reduction=4):
        super().__init__()
        self.fc1 = nn.Linear(num_channels, num_channels // reduction)
        self.fc2 = nn.Linear(num_channels // reduction, num_channels)

    def forward(self, x):
        # x: [B, C, T] → squeeze: [B, C]
        z = x.mean(dim=2)
        a = torch.sigmoid(self.fc2(F.relu(self.fc1(z))))
        return x * a.unsqueeze(2)  # scale: [B, C, T]

class DCACNN(nn.Module):
    """Dynamic Channel-Aware CNN — Araştırma Önerisi §4"""
    def __init__(self, max_channels=3, num_classes=5):
        super().__init__()
        self.acc1 = AdaptiveChannelConv(max_channels, 64, kernel_size=7)
        self.se1 = SEBlock(64)
        self.acc2 = AdaptiveChannelConv(1, 128, kernel_size=5)  # 64 ch → dummy
        self.se2 = SEBlock(128)
        self.classifier = nn.Linear(128, num_classes)
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)

    def forward(self, x):
        # x: [B, C, 2500]
        x = F.relu(self.bn1(self.acc1(x)))
        x = F.max_pool1d(x, 2)
        x = self.se1(x)
        x = F.relu(self.bn2(self.acc2(x)))
        x = self.se2(x)
        x = x.mean(dim=2)           # Global Average Pooling
        return self.classifier(x)   # [B, num_classes]

    def phase_regularization(self, lambda_phi=0.01):
        """Faz regülarizasyonu — konvolüsyon kernel Fourier cevabı"""
        loss = 0.0
        for layer in [self.acc1, self.acc2]:
            kernel = layer.w_base
            freq_response = torch.fft.rfft(kernel, dim=-1)
            # İdeal flat phase referans — basit L2 norm proxy
            loss += lambda_phi * (freq_response.abs() - 1.0).pow(2).mean()
        return loss
```

**`train.py` eğitim döngüsü özeti:**
```python
# Kayıp fonksiyonu: L = L_CE + λ_g * L_gate + λ_φ * L_phase
loss = ce_loss + model.acc1.gate_regularization(C) + model.phase_regularization()
optimizer = AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)
```

---

## Görev 10: README & Dokümantasyon Güncellemesi

**`README.md` Güncellenmesi:**
- Proje durumu tablosunda FAZ 3 → 🔄 Devam Ediyor
- `mobile/` proje yapısındaki yeni dosyaları ekle
- Çalışma takvimini güncelle

---

## Takvim (2209-A Araştırma Önerisinden)

| Faz | Süre | Görevler | Araştırma Önerisi Katkısı |
|---|---|---|---|
| FAZ 1-2 | 19 Şub–23 Şub 2026 | UI + BLE + Mock pipeline | 38/100 → **Tamamlandı** |
| FAZ 3 | 24 Şub–30 Nis 2026 | İleri DSP + DCA-CNN + Acil Durum | 27/100 → **Devam Ediyor** |
| FAZ 4 | 01 Mar–30 Nis 2026 (paralel) | Room DB + Kullanıcı Yönetimi + KVKK | — |
| FAZ 5 | 01 May–30 Haz 2026 | Kapalı Beta + Saha Pilot (≥60h) | 17/100 |
| Kapanış | 01 Tem–31 Tem 2026 | Nihai Rapor + Kongre Bildirisi | 6/100 |

## Başarı Kriterleri (Araştırma Önerisi Hedefleri)

| Metrik | Hedef | Ölçüm Yöntemi |
|---|---|---|
| Doğruluk | ≥ %95 | 60 saatlik pilot deneme, F1-score |
| Uyarı Gecikmesi | ≤ 1 saniye | AlertEngine → UI timestamp delta |
| Yanlış Alarm Oranı | ≤ %5 | Toplam alarm / gerçek pozitif |
| SUS Puanı | ≥ 75 | 10 soruluk standart ölçek |
| TFLite Çıkarım | < 38ms (3ch) / < 22ms (1ch) | Benchmark ölçümü |
| Model Boyutu | < 2.1 MB | APK assets dosya boyutu |
| Crash-free | ≥ %98 | Firebase Crashlytics |
