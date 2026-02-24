package com.hayatinritmi.app.domain.model

enum class AlertLevel(
    val displayText: String,
    val subText: String,
    val priority: Int
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
