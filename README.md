# Hayatın Ritmi — Yapay Zeka Destekli Taşınabilir EKG Analiz Sistemi

**TÜBİTAK 2209-A Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı**

> Çok Kanallı Adaptif Yapay Zekâ Tabanlı Taşınabilir EKG Analiz Sistemi

**Başvuru Sahibi:** İsmail Sakci | **Danışman:** Doç. Dr. Mehmet Zübeyir Ünlü
**Kurum:** İzmir Yüksek Teknoloji Enstitüsü — Elektrik-Elektronik Mühendisliği

---

## Proje Özeti

Giyilebilir EKG tişörtü ile sürekli kalp ritmi takibi yapan, yapay zeka (DCA-CNN) ile aritmi tespit eden ve acil durumlarda otomatik uyarı gönderen uçtan uca bir sağlık izleme sistemi.

**Donanım:** 4× ADS1293 (12 derivasyonlu, 24-bit, 250 Hz ADC) + STM32F103C8T6 (MCU) + nRF52832 (BLE 5.0)
**Yazılım:** Kotlin + Jetpack Compose + TensorFlow Lite
**Mimari:** Repository Pattern (Mock/Real BLE abstraction) + ViewModel + Manual DI

---

## Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Dil | Kotlin 2.0.21 |
| UI Framework | Jetpack Compose + Material 3 |
| Tasarım Dili | Glassmorphism + Neon/Cyberpunk Dark Theme |
| Reaktif Veri | Kotlin Coroutines + StateFlow |
| BLE | Android BluetoothLeScanner + GATT Client |
| Sinyal İşleme | IIR Filters (HPF/Notch/LPF), Pan-Tompkins R-Peak, 12-Lead Fusion |
| Yapay Zeka | DCA-CNN → TFLite INT8 (QAT) |
| Veritabanı | Room + SQLCipher (KVKK uyumlu) |
| Build | AGP 8.7.3, Gradle 8.9, Compose BOM 2024.11.00 |
| Min/Hedef SDK | 24 (Android 7.0) / 35 (Android 15) |

---

## Proje Durumu

| Faz | Durum | Açıklama |
|---|---|---|
| FAZ 1 | ✅ Tamamlandı | UI Arayüzü & Navigasyon (10 ekran) |
| FAZ 2 | ✅ Tamamlandı | Bluetooth & Cihaz Bağlantısı (28 Kotlin dosyası) |
| FAZ 3 | 🔄 Devam Ediyor | Sinyal Kalitesi, DCA-CNN AI & Acil Durum |
| FAZ 4 | ⏳ Planlandı | Room DB, Kullanıcı Yönetimi & KVKK |
| FAZ 5 | ⏳ Planlandı | Doğrulama, Test & Yaygınlaştırma |

Detaylı görev takibi: [`ILERLEME_DURUMU.md`](ILERLEME_DURUMU.md)

---

## Dosya Yapısı

```
app/hayatin_ritmi/app/src/main/java/com/hayatinritmi/app/
├── MainActivity.kt                 # NavHost (10 rota) + ViewModel DI
├── ble/
│   ├── BleManager.kt               # Interface: scan, connect, disconnect
│   ├── MockBleManager.kt           # PQRST dalga formu simülatörü (250Hz)
│   ├── RealBleManager.kt           # Android BLE API (GATT + Scanner)
│   └── BlePermissionHelper.kt      # Dinamik izin yönetimi (Android 12+/11-)
├── data/
│   ├── model/
│   │   ├── EcgSample.kt            # timestamp, channel, rawAdc, voltageUv
│   │   ├── DeviceStatus.kt         # pil, elektrot, şarj durumu
│   │   ├── ScannedDevice.kt        # name, macAddress, rssi
│   │   ├── ConnectionState.kt      # DISCONNECTED → SCANNING → CONNECTING → CONNECTED
│   │   └── HrvMetrics.kt           # SDNN, RMSSD
│   ├── BleConstants.kt             # UUID'ler, paket başlığı, örnekleme hızı
│   ├── EcgPacketParser.kt          # 10-byte BLE paket ayrıştırma + XOR checksum
│   ├── EcgRepository.kt            # Interface: observeEcgSamples(), observeDeviceStatus()
│   ├── MockEcgRepository.kt        # Mock → Repository köprüsü
│   └── BleEcgRepository.kt         # Gerçek BLE → Repository köprüsü
├── processing/
│   ├── RingBuffer.kt               # Thread-safe dairesel tampon (2500 sample)
│   ├── EcgFilter.kt                # Cascaded IIR: HPF 0.5Hz → Notch 50Hz → LPF 40Hz
│   └── RPeakDetector.kt            # Pan-Tompkins: derivative → square → MWI → adaptif eşik
├── service/
│   └── EcgForegroundService.kt     # START_STICKY arka plan BLE bağlantısı
├── viewmodel/
│   ├── EcgViewModel.kt             # Filter → RingBuffer → RPeakDetector → StateFlow
│   └── DeviceScanViewModel.kt      # Tarama/bağlantı + DataStore persistance
├── screens/
│   ├── LoginScreen.kt              # Glassmorphism, EKG animasyonu, Biyometrik
│   ├── SignUpScreen.kt             # Underline inputlar, OPSİYONEL badge
│   ├── ForgotPasswordScreen.kt     # 2 adımlı OTP doğrulama
│   ├── DashboardScreen.kt          # Breathing circle, AI notu, glass kartlar
│   ├── ProModeScreen.kt            # Canvas EKG, canlı BPM/HRV/SDNN
│   ├── EmergencyScreen.kt          # Alarm geri sayımı, 112 çağrı
│   ├── SettingsScreen.kt           # PRO/Sakin toggle, cihaz yönetimi
│   ├── NotificationScreen.kt       # Kilitli/açılabilir bildirim toggle
│   └── DeviceScanScreen.kt         # Radar animasyonu, cihaz listesi
└── ui/
    ├── theme/
    │   ├── Color.kt                # 50+ design token
    │   ├── Type.kt                 # MaterialTheme tipografi hiyerarşisi
    │   └── Theme.kt                # darkColorScheme + sistem bar renkleri
    └── components/
        └── CommonComponents.kt     # GlassCard, GradientButton, MetricCard, StatusBadge...
```

---

## BLE Protokolü

```
10-byte paket: [Header:0xAA][Kanal:1B][Timestamp:4B LE][EKG:3B BE int24][Checksum:XOR]

Voltaj dönüşümü: voltageUv = (rawAdc × 2.4V) / (2²³ × 6) × 1,000,000
Örnekleme: 250 Hz | MTU: 247 byte | Filtre: BLE 5.0
```

---

## Sinyal İşleme Pipeline

```
Ham ADC → HPF 0.5Hz (baseline) → Notch 50Hz (şebeke) → LPF 40Hz (kas artefaktı)
       → Pan-Tompkins R-Peak → BPM + HRV (SDNN, RMSSD)
       → RingBuffer (10s / 2500 sample) → 30 FPS UI güncelleme
```

---

## Çalışma Takvimi

| Tarih | Faaliyetler | Katkı |
|---|---|---|
| 11.2025 | Proje çerçevesi, WBS, risk analizi | 12/100 |
| 12.2025–02.2026 | Veri/donanım altyapısı, temel AI, mobil çekirdek | 38/100 |
| 03.2026–04.2026 | Bileşen entegrasyonu ve optimizasyon | 27/100 |
| 05.2026–06.2026 | Kapalı beta, performans ölçümü | 17/100 |
| 07.2026 | Nihai rapor, arşiv, kapanış | 6/100 |

---

## Build

```bash
# gradle.properties içinde Java yolu ayarlı
cd app/hayatin_ritmi
./gradlew assembleDebug
```

**Gereksinimler:** JDK 17+ (Eclipse Temurin önerilir), Android SDK 35

---

## Lisans

Bu proje TÜBİTAK 2209-A kapsamında geliştirilmektedir.
