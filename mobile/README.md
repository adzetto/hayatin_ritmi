<div align="center">

<!-- HERO BANNER -->
<img src="docs/assets/banner.png" alt="Hayatın Ritmi Banner" width="100%" />

<br/>

# ❤️‍🔥 Hayatın Ritmi

### Giyilebilir Yapay Zeka Destekli EKG İzleme Sistemi

*Wearable AI-Powered ECG Monitoring System*

<br/>

[![Android](https://img.shields.io/badge/Platform-Android-3DDC84?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com)
[![Kotlin](https://img.shields.io/badge/Kotlin-2.0.21-7F52FF?style=for-the-badge&logo=kotlin&logoColor=white)](https://kotlinlang.org)
[![Jetpack Compose](https://img.shields.io/badge/Jetpack_Compose-Material3-4285F4?style=for-the-badge&logo=jetpackcompose&logoColor=white)](https://developer.android.com/jetpack/compose)
[![BLE](https://img.shields.io/badge/BLE-5.0-0082FC?style=for-the-badge&logo=bluetooth&logoColor=white)](https://www.bluetooth.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![TÜBİTAK](https://img.shields.io/badge/TÜBİTAK-2209--A-E11D48?style=for-the-badge)](https://www.tubitak.gov.tr)

<br/>

[📱 Özellikler](#-özellikler) •
[🏗️ Mimari](#️-mimari) •
[🚀 Kurulum](#-kurulum) •
[📋 TODO](#-todo) •
[🤝 Katkıda Bulunma](#-katkıda-bulunma)

<br/>

---

</div>

## 🎯 Proje Hakkında

> **Hayatın Ritmi**, TÜBİTAK 2209-A Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı kapsamında geliştirilen, giyilebilir bir EKG izleme sistemidir.

Proje, **ESP32 + ADS1293** tabanlı bir akıllı tişört ile **Android mobil uygulama** arasında **Bluetooth Low Energy (BLE)** bağlantısı kurarak, kullanıcının kalp ritimlerini gerçek zamanlı olarak izler, analiz eder ve acil durumlarda otomatik uyarı gönderir.

### 💡 Neden Bu Proje?

| Problem | Çözüm |
|---|---|
| 🏥 EKG takibi sadece hastanede yapılabiliyor | 👕 Giyilebilir tişörtle 7/24 izleme |
| ⏳ Aritmi teşhisi geç konulabiliyor | ⚡ Gerçek zamanlı AI destekli analiz |
| 📞 Acil durumda yardım çağırmak zor | 🚨 Otomatik acil durum bildirimi + konum paylaşımı |
| 📄 EKG verileri sadece doktorun elinde | 📊 PDF rapor oluşturma ve doktora gönderme |

---

## 📱 Özellikler

<table>
<tr>
<td width="50%">

### 🎨 Kullanıcı Arayüzü
- ✅ **Glassmorphism & Dark Theme** tasarım dili
- ✅ EKG animasyonlu giriş ekranı
- ✅ Biyometrik kimlik doğrulama (parmak izi / yüz tanıma)
- ✅ 2 adımlı şifre sıfırlama (OTP)
- ✅ Canlı EKG monitör (Pro Mod)
- ✅ "Sakin Mod" — güvenlik odaklı basitleştirilmiş arayüz
- ✅ Acil durum ekranı — geri sayım + 112 otomatik arama
- ✅ Premium ayarlar ekranı

</td>
<td width="50%">

### 📡 Donanım & Bağlantı
- 🔲 ESP32 BLE 5.0 cihaz tarama ve eşleştirme
- 🔲 4× ADS1293 — 12 derivasyonlu EKG veri alma (250 Hz, 24-bit)
- 🔲 Standart 12-Lead: I, II, III, aVR, aVL, aVF + V1–V6
- 🔲 24-bit ADC → µV voltaj dönüşümü
- 🔲 Gerçek zamanlı EKG grafiği (Canvas)
- 🔲 Arka planda bağlantı koruma (Foreground Service)
- 🔲 Pil seviyesi ve sensör durumu izleme
- 🔲 Otomatik yeniden bağlanma

</td>
</tr>
<tr>
<td width="50%">

### 🛡️ Güvenlik & Sağlık
- 🔲 R-peak tespiti ve BPM hesaplama
- 🔲 HRV (Heart Rate Variability) analizi
- 🔲 Aritmi / Taşikardi / Bradikardi tespiti
- 🔲 ST segment analizi
- 🔲 Acil durum SMS + konum gönderme
- 🔲 Otomatik 112 arama

</td>
<td width="50%">

### 📊 Raporlama & Veri
- 🔲 EKG kayıtlarının yerel depolanması (Room DB)
- 🔲 PDF rapor oluşturma
- 🔲 Doktora e-posta ile gönderme
- 🔲 Geçmiş kayıtları görüntüleme
- 🔲 Veri senkronizasyonu (WorkManager)

</td>
</tr>
</table>

> ✅ = Tamamlandı &nbsp;&nbsp; 🔲 = Geliştirme Aşamasında

---

## 🏗️ Mimari

```
hayatin_ritmi/
├── 📁 app/
│   └── 📁 src/main/
│       ├── 📁 java/com/hayatinritmi/app/
│       │   ├── 📄 MainActivity.kt              # Ana aktivite + NavHost
│       │   ├── 📁 screens/
│       │   │   ├── 📄 LoginScreen.kt            # Giriş (EKG anim + Biyometrik)
│       │   │   ├── 📄 SignUpScreen.kt            # Kayıt (Underline inputlar)
│       │   │   ├── 📄 ForgotPasswordScreen.kt    # Şifre sıfırlama (2 adımlı OTP)
│       │   │   ├── 📄 DashboardScreen.kt         # Ana panel (Sakin Mod)
│       │   │   ├── 📄 ProModeScreen.kt           # Canlı EKG (Pro Mod)
│       │   │   ├── 📄 EmergencyScreen.kt         # Acil durum (Alarm + 112)
│       │   │   ├── 📄 SettingsScreen.kt          # Ayarlar
│       │   │   └── 📄 NotificationScreen.kt      # Bildirim ayarları
│       │   ├── 📁 components/
│       │   │   └── 📄 Backgrounds.kt             # Ortak arka plan bileşenleri
│       │   └── 📁 ui/theme/
│       │       ├── 📄 Color.kt                   # Renk paleti
│       │       ├── 📄 Theme.kt                   # Tema yapılandırması
│       │       └── 📄 Type.kt                    # Tipografi
│       └── 📄 AndroidManifest.xml
├── 📁 gradle/
│   └── 📄 libs.versions.toml                    # Versiyon kataloğu
├── 📄 build.gradle.kts
├── 📄 settings.gradle.kts
└── 📄 gradle.properties
```

### Tech Stack

| Katman | Teknoloji |
|---|---|
| **Dil** | Kotlin 2.0.21 |
| **UI Framework** | Jetpack Compose + Material 3 |
| **Navigasyon** | Navigation Compose |
| **Donanım** | 4× ADS1293 + STM32F103C8T6 + nRF52832 (BLE 5.0) |
| **İletişim** | Bluetooth Low Energy (BLE 5.0) |
| **Veri İşleme** | Kotlin Coroutines + Flow |
| **Yerel DB** | Room (planlandı) |
| **Background** | Foreground Service (planlandı) |
| **Min SDK** | 24 (Android 7.0) |
| **Target SDK** | 35 (Android 15) |

---

## 🚀 Kurulum

### Gereksinimler

- Android Studio Ladybug (2024.2+)
- JDK 17+
- Android SDK 35
- Kotlin 2.0.21
- Gradle 8.9

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/kullanici-adi/hayatin-ritmi.git

# 2. Proje dizinine gir
cd hayatin-ritmi

# 3. Android Studio ile aç
# File → Open → hayatin-ritmi klasörünü seç

# 4. Gradle sync
# Android Studio otomatik olarak sync eder

# 5. Çalıştır
# ▶ Run 'app' butonuna bas veya:
./gradlew assembleDebug
```

> ⚠️ **Not:** Proje dizininde Türkçe karakter (ı, ö, ü, ş, ç) **olmamalıdır**. Gradle build hatası oluşabilir.

---

## 📋 TODO

Proje geliştirme sürecinin detaylı takibi:

### 🟢 Faz 1 — UI Arayüzü & Navigasyon `tamamlandı`

- [x] Tüm 8 ekranın tasarımı (Glassmorphism + Ambiyans Işıkları)
- [x] HTML prototiplerinin Jetpack Compose'a birebir dönüşümü
- [x] EKG Canvas animasyonu (Login ekranı)
- [x] Biyometrik Bottom Sheet (Parmak izi / Yüz tanıma)
- [x] 2 adımlı OTP şifre sıfırlama akışı
- [x] PRO/Sakin mod toggle
- [x] Floating navigation bar
- [x] 0 error, 0 warning build

### 🟡 Faz 2 — Bluetooth & Cihaz Bağlantısı `devam ediyor`

- [ ] **İzinler & Altyapı**
  - [ ] AndroidManifest — BLE izinleri (SCAN, CONNECT, LOCATION)
  - [ ] Dinamik izin isteme (ActivityResultContracts)
  - [ ] İzin rationale dialog
- [ ] **Cihaz Tarama & Kayıt**
  - [ ] `DeviceScanScreen` UI — tarama animasyonu + cihaz listesi
  - [ ] BLE Scanner — `BluetoothLeScanner.startScan()`
  - [ ] ScanFilter — "HayatinRitmi" cihaz adı filtresi
  - [ ] Cihaz bilgisini DataStore'a kaydetme
  - [ ] Otomatik yeniden bağlanma
- [ ] **GATT Bağlantısı**
  - [ ] `connectGatt()` + `BluetoothGattCallback`
  - [ ] Servis/Karakteristik keşfi (UUID)
  - [ ] EKG veri karakteristiğine NOTIFY aboneliği
  - [ ] MTU ve Connection Interval optimizasyonu
- [ ] **Veri Protokolü (ESP32 ↔ Android)**
  - [ ] Paket formatı: `[Header][Channel][Timestamp][ECG_24bit][Checksum]`
  - [ ] 24-bit signed ADC → µV dönüşümü
  - [ ] Pil seviyesi ve sensör durumu okuma
  - [ ] Lead-off detection (elektrot teması kaybı)
- [ ] **Sinyal İşleme**
  - [ ] Ring buffer (son 10 saniye = 2500 sample)
  - [ ] Baseline wander kaldırma (HPF 0.5 Hz)
  - [ ] 50/60 Hz notch filtre
  - [ ] R-peak tespiti → BPM hesaplama
  - [ ] HRV analizi (SDNN, RMSSD)
- [ ] **Canlı EKG Grafiği**
  - [ ] ProModeScreen → gerçek veriden Canvas çizim
  - [ ] 25 mm/s kağıt hızı simülasyonu
  - [ ] EKG grid overlay
  - [ ] ≥30 FPS performans hedefi
- [ ] **Foreground Service**
  - [ ] Arka plan BLE bağlantı koruma
  - [ ] Kalıcı bildirim ("EKG izleniyor")
  - [ ] EKG verisini CSV/binary dosyaya kaydetme

### 🔴 Faz 3 — Acil Durum & Raporlama `planlandı`

- [ ] Aritmi / Taşikardi / Bradikardi tespiti
- [ ] ST segment elevasyonu/çökmesi analizi
- [ ] Acil durum SMS + konum gönderme
- [ ] Otomatik 112 arama
- [ ] PDF rapor oluşturma (EKG grafiği + metrikler)
- [ ] Doktora e-posta ile gönderme

### ⚪ Faz 4 — Veri Saklama & Senkronizasyon `planlandı`

- [ ] Room Database (User, EcgSession, EcgAlert tabloları)
- [ ] Kayıt/Giriş doğrulaması
- [ ] Geçmiş EKG kayıtları listesi
- [ ] WorkManager ile bulut senkronizasyonu

---

## 🔧 Donanım

| Bileşen | Model | Açıklama |
|---|---|---|
| **Mikrodenetleyici** | ESP32-C3/S3 | BLE 5.0, düşük güç tüketimi |
| **EKG Sensörü** | ADS1293 | Tek kanal, 24-bit ADC, 250 Hz |
| **Giyilebilir** | Akıllı Tişört | Kumaşa entegre kuru elektrotlar |
| **Güç** | LiPo 3.7V | USB-C şarj |

### BLE Veri Protokolü

```
┌──────────┬──────────┬────────────┬────────────┬──────────┐
│ Header   │ Channel  │ Timestamp  │ ECG Value  │ Checksum │
│ 1 byte   │ 1 byte   │ 4 bytes    │ 3 bytes    │ 1 byte   │
│ 0xAA     │ 0x00     │ uint32_ms  │ int24_adc  │ XOR      │
└──────────┴──────────┴────────────┴────────────┴──────────┘

ADC → Voltaj Dönüşümü:
  voltaj_µV = (adc_value × 2.4V) / (2²³ × 6)
  Sonuç: ±400 µV aralığında EKG sinyali
```

---

## 📸 Ekran Görüntüleri

<div align="center">

| Giriş Ekranı | Dashboard | Pro Mod (EKG) | Acil Durum |
|:---:|:---:|:---:|:---:|
| *Yakında* | *Yakında* | *Yakında* | *Yakında* |

</div>

---

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

---

## 📄 Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakınız.

---

## 🙏 Teşekkürler

- **TÜBİTAK** — 2209-A Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı
- **Texas Instruments** — ADS1293 EKG AFE
- **Espressif** — ESP32 BLE SoC
- **Google** — Jetpack Compose, Material 3

---

<div align="center">

**Hayatın Ritmi** ile kalp sağlığınız artık cebinizde. ❤️‍🔥

<sub>TÜBİTAK 2209-A Projesi • 2026</sub>

</div>
