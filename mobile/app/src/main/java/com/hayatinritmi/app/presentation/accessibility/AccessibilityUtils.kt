package com.hayatinritmi.app.presentation.accessibility

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp

/**
 * WCAG 2.1 AA Erişilebilirlik Yardımcıları
 *
 * 1. Minimum dokunma hedefi: 48dp × 48dp (WCAG 2.5.5 Level AAA = 44dp)
 * 2. Renk kontrastı: 4.5:1 normal metin, 3:1 büyük metin (WCAG 1.4.3)
 * 3. Semantik açıklamalar: contentDescription, stateDescription, heading
 * 4. Canlı bölgeler: BPM, uyarı gibi değişen veriler TalkBack'e bildirilir
 */
object AccessibilityUtils {

    /** Minimum dokunma hedefi boyutu (WCAG 2.5.8 Level AA) */
    val MIN_TOUCH_TARGET = 48.dp

    /**
     * BPM değeri için TalkBack açıklaması.
     * Değişen değeri "polite" modda duyurur.
     */
    fun bpmDescription(bpm: Int): String = when {
        bpm <= 0 -> "Kalp atışı ölçülmüyor"
        bpm < 50 -> "Kalp atışı düşük: dakikada $bpm atım"
        bpm in 50..100 -> "Kalp atışı normal: dakikada $bpm atım"
        bpm in 101..150 -> "Kalp atışı yüksek: dakikada $bpm atım"
        else -> "Kalp atışı çok yüksek: dakikada $bpm atım. Dikkat!"
    }

    /**
     * Uyarı seviyesi için TalkBack açıklaması.
     */
    fun alertDescription(level: String): String = when (level.uppercase()) {
        "RED" -> "Kritik uyarı. Acil durum tespit edildi."
        "YELLOW" -> "Uyarı. Kalp ritmi düzensizliği tespit edildi."
        "NONE", "GREEN" -> "Durum normal. Herhangi bir uyarı yok."
        else -> "Durum bilinmiyor."
    }

    /**
     * Sinyal kalitesi için TalkBack açıklaması.
     */
    fun signalQualityDescription(score: Int): String = when {
        score >= 80 -> "Sinyal kalitesi mükemmel: yüzde $score"
        score >= 60 -> "Sinyal kalitesi iyi: yüzde $score"
        score >= 40 -> "Sinyal kalitesi orta: yüzde $score"
        score > 0 -> "Sinyal kalitesi zayıf: yüzde $score. Elektrot bağlantısını kontrol edin."
        else -> "Sinyal kalitesi ölçülmüyor"
    }

    /**
     * Bağlantı durumu için TalkBack açıklaması.
     */
    fun connectionDescription(state: String): String = when (state.uppercase()) {
        "CONNECTED" -> "Sensör bağlı. Veri alınıyor."
        "CONNECTING" -> "Sensöre bağlanılıyor. Lütfen bekleyin."
        "SCANNING" -> "Sensör taranıyor. Lütfen bekleyin."
        "DISCONNECTED" -> "Sensör bağlı değil. Ayarlar menüsünden bağlayabilirsiniz."
        else -> "Bağlantı durumu bilinmiyor."
    }

    /**
     * Renk kontrastı doğrulama (WCAG 1.4.3)
     * Relative luminance hesaplaması.
     */
    fun contrastRatio(foreground: Color, background: Color): Float {
        val l1 = relativeLuminance(foreground)
        val l2 = relativeLuminance(background)
        val lighter = maxOf(l1, l2)
        val darker = minOf(l1, l2)
        return (lighter + 0.05f) / (darker + 0.05f)
    }

    /**
     * Renk kontrastı minimum eşiği aşıyor mu?
     * Normal metin: 4.5:1, büyük metin (18sp+): 3:1
     */
    fun meetsContrastRequirement(
        foreground: Color,
        background: Color,
        isLargeText: Boolean = false
    ): Boolean {
        val ratio = contrastRatio(foreground, background)
        return ratio >= if (isLargeText) 3.0f else 4.5f
    }

    private fun relativeLuminance(color: Color): Float {
        fun linearize(c: Float): Float =
            if (c <= 0.03928f) c / 12.92f
            else Math.pow(((c + 0.055) / 1.055).toDouble(), 2.4).toFloat()

        val r = linearize(color.red)
        val g = linearize(color.green)
        val b = linearize(color.blue)
        return 0.2126f * r + 0.7152f * g + 0.0722f * b
    }
}

/**
 * Semantik modifier uzantıları — Compose bileşenlerine erişilebilirlik ekler.
 */
fun Modifier.accessibleBpm(bpm: Int): Modifier = this.then(
    Modifier.semantics {
        contentDescription = AccessibilityUtils.bpmDescription(bpm)
        liveRegion = LiveRegionMode.Polite
        stateDescription = if (bpm > 0) "$bpm BPM" else "Ölçüm yok"
    }
)

fun Modifier.accessibleAlert(level: String): Modifier = this.then(
    Modifier.semantics {
        contentDescription = AccessibilityUtils.alertDescription(level)
        liveRegion = LiveRegionMode.Assertive
    }
)

fun Modifier.accessibleHeading(text: String): Modifier = this.then(
    Modifier.semantics {
        heading()
        contentDescription = text
    }
)
