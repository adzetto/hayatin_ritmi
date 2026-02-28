# 🚀 TÜBİTAK 2209-A Proje İlerleme ve Görev Takibi

Bu dosya, projenin geliştirme sürecini adım adım takip etmek için oluşturulmuştur.

**Proje Başlığı:** Çok Kanallı Adaptif Yapay Zekâ Tabanlı Taşınabilir EKG Analiz Sistemi
**Başvuru Sahibi:** İsmail Sakci | **Danışman:** Mehmet Zübeyir Ünlü
**Kurum:** İzmir Yüksek Teknoloji Enstitüsü

## 📅 Genel Durum
- **Başlangıç Tarihi:** 19 Şubat 2026
- **Mevcut Faz:** FAZ 5 (Doğrulama & Test) — **AI + DSP + Room DB + Auth + Export + Backpressure + Parser + Accessibility tamamlandı ✅**
- **Hedef:** ADS1293 + STM32 + nRF52832 tabanlı EKG tişörtüyle BLE bağlantısı kurmak, canlı veri almak, DCA-CNN ile analiz etmek ve acil durum uyarısı göndermek.
- **AI Durumu:** DCA-CNN eğitildi (261K param, AUC=0.968 12-lead, adaptif 1/3/12 kanal), QAT fine-tuned (AUC=0.9535, drop -0.001), TFLite INT8 (312 KB, 0.90ms/inference). Gürültü dayanıklılık: AUC 0.958 @ SNR 6dB. Python 22/22 test geçti.
- **Mimari:** Clean Architecture + **Hilt DI** — `domain/` (model + interface) → `data/` (bluetooth + repository + local + recording + export) → `presentation/` (screen + viewmodel) → `di/` (AppModule + DatabaseModule) | Room + SQLCipher + PBKDF2

### 🗂️ Proje Yapısı (İki Paralel Dizin)
| Dizin | Amaç | Derleme |
|---|---|---|
| `app/hayatin_ritmi/` | FAZ 1-2 prototipi, tüm ekranlar + BLE | ✅ Derlenir (Gradle 8.9) |
| `mobile/` | **Aktif üretim projesi** — Clean Architecture, FAZ 3 hedefli | ✅ Derlenir (Gradle 8.13, 24 Şub 2026 düzeltmesiyle) |

### 🔀 Pull Request Geçmişi (24 Şubat 2026)
| PR | Branch | Yazar | Değişiklikler |
|---|---|---|---|
| #1 | `feature/light-mode` | ONURKULAN | Light/Dark tema altyapısı: `LightColorScheme`, `isSystemInDarkTheme()`, 9 ekran + CommonComponents MaterialTheme token'larına geçiş |
| #2 | `feature/izinler` | ONURKULAN | AndroidManifest: `SEND_SMS`, `CALL_PHONE`, `ACCESS_FINE/COARSE_LOCATION`; SettingsScreen runtime izin akışı (`rememberLauncherForActivityResult`) |

### 🔧 Derleme Düzeltmeleri (24 Şubat 2026)
- ✅ `mobile/` — Java 25 uyumsuzluğu: `gradle.properties` → `org.gradle.java.home=C:\\Program Files\\Android\\Android Studio\\jbr` (Java 21 JBR)
- ✅ `BleEcgRepository.kt` + `MockEcgRepository.kt` — Eksik `EcgPacketParser` import'u eklendi
- ✅ `CommonComponents.kt` — `Icons.Default.ChevronRight` yok (extended pakette bile mevcut değil) → `Icons.AutoMirrored.Filled.ArrowForwardIos` ile değiştirildi
- ✅ `DeviceScanScreen.kt` — Eksik `DeviceScanViewModel` import'u eklendi (`presentation.viewmodel` paketi)
- **BUILD SUCCESSFUL** — 35 actionable task, 37 saniye

---

## ✅ FAZ 1: UI Arayüzü & Navigasyon (TAMAMLANDI)
**Amaç:** Uygulamanın iskeletini kurmak ve tüm ekranları HTML tasarımlarına birebir uyumlu hale getirmek.

- [x] **UI İskeletinin Kurulması**
    - [x] `LoginScreen` (Giriş Ekranı) — Glassmorphism, EKG animasyonu, Biyometrik Bottom Sheet
    - [x] `SignUpScreen` (Kayıt Ekranı) — Underline inputlar, yan yana layout, OPSİYONEL badge
    - [x] `ForgotPasswordScreen` (Şifre Sıfırlama) — 2 adımlı OTP doğrulama akışı
    - [x] `DashboardScreen` (Ana Ekran) — Breathing circle, AI notu, glass kartlar
    - [x] `ProModeScreen` (Canlı EKG Arayüzü) — Scanline animasyonu, HRV/SpO2 kartlar
    - [x] `EmergencyScreen` (Acil Durum Arayüzü) — Alarm, geri sayım, 112 çağrı
    - [x] `SettingsScreen` (Ayarlar Ekranı) — PRO/Sakin toggle, renkli menü ikonları
    - [x] `NotificationScreen` (Bildirim Ayarları) — Kilitli/açılabilir toggle'lar
- [x] **UI İyileştirmeleri (HTML Tasarımlarına Tam Uyumluluk)**
    - [x] Login → EKG animasyonu (Canvas ile draw), Biyometrik Bottom Sheet, "Şifremi Unuttum" linki
    - [x] Underline-style inputlar (HTML premium-input stiline uyumlu)
    - [x] Settings → menü ikon renk çeşitliliği (Mavi/Rose/Yeşil/Amber), PRO/Sakin toggle pill
    - [x] Developer Sign In butonu (Dashboard'a direkt geçiş)
- [x] **Navigasyon Altyapısı**
    - [x] `MainActivity` içinde `NavHost` kurulumu (10 ekran: Login, SignUp, ForgotPassword, Dashboard, ProMode, Emergency, Settings, Notifications, DeviceScan)
    - [x] FloatingNavBar aktif sayfa takibi
- [x] **Kod Kalitesi İyileştirmeleri**
    - [x] Renk tanımlarının `Color.kt` içinde merkezileştirilmesi
    - [x] Deprecated API uyarılarının giderilmesi (0 warning build)

---

## ✅ FAZ 2: Bluetooth & Cihaz Bağlantısı (TAMAMLANDI)
**Amaç:** EKG tişörtüyle BLE üzerinden iletişim kurmak, cihazı kayıt etmek ve canlı veri almak.
**Mimari:** Repository Pattern — `BleManager` (interface) → `MockBleManager` / `RealBleManager`; `EcgRepository` (interface) → `MockEcgRepository` / `BleEcgRepository`

### 2.1 — Bluetooth İzinleri & Altyapı ✅
- [x] **AndroidManifest.xml İzinleri**
    - [x] `BLUETOOTH_SCAN` (Android 12+, `neverForLocation` flag)
    - [x] `BLUETOOTH_CONNECT` (Android 12+)
    - [x] `BLUETOOTH_ADMIN` + `BLUETOOTH` (Android 11 ve altı, `maxSdkVersion=30`)
    - [x] `ACCESS_FINE_LOCATION` (BLE tarama için, `maxSdkVersion=30`)
    - [x] `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_CONNECTED_DEVICE`
    - [x] `POST_NOTIFICATIONS` (Android 13+)
    - [x] `uses-feature android.hardware.bluetooth_le` (required=true)
- [x] **Dinamik İzin İsteme**
    - [x] `BlePermissionHelper.kt` — Android 12+ / 11- ayrımı, `hasAllPermissions()`, `getNotificationPermission()`, `createAppSettingsIntent()`
- [x] **Build Yapılandırması**
    - [x] `libs.versions.toml` — DataStore Preferences 1.1.1, Lifecycle ViewModel Compose 2.8.7
    - [x] `build.gradle.kts` — `implementation` bağımlılıkları
    - [x] `gradle.properties` — `org.gradle.java.home` (Java 25 Temurin)

### 2.2 — BLE Cihaz Tarama & Kayıt ✅
- [x] **Cihaz Tarama (Scanning)**
    - [x] `BluetoothLeScanner.startScan()` ile tarama (`RealBleManager.kt`)
    - [x] `ScanFilter` ile sadece "HayatinRitmi" adlı cihazları filtreleme (`BleConstants.DEVICE_NAME_FILTER`)
    - [x] Tarama sonuçlarını `StateFlow<List<ScannedDevice>>` ile güncelleme (cihaz adı, MAC adresi, RSSI)
    - [x] Tarama süresi limiti (30 saniye timeout, coroutine Job ile)
- [x] **Cihaz Kayıt UI**
    - [x] `DeviceScanScreen.kt` — Radar pulse animasyonu + bulunan cihaz listesi + sinyal gücü çubukları
    - [x] Cihaz seçildiğinde bağlantı başlatma (CircularProgressIndicator ile feedback)
    - [x] Kayıtlı cihaz bilgisini `DataStore Preferences`'a kaydetme (`DeviceScanViewModel.kt`)
    - [x] Settings ekranındaki "Bağlı Cihazlar" kartından `DeviceScanScreen`'e navigasyon
- [x] **Otomatik Yeniden Bağlanma**
    - [x] `DeviceScanViewModel.autoReconnect()` — Son kayıtlı MAC adresine otomatik bağlanma

### 2.3 — GATT Bağlantısı & Servis Keşfi ✅
- [x] **GATT Client Bağlantısı** (`RealBleManager.kt`)
    - [x] `BluetoothDevice.connectGatt()` ile bağlantı kurma (TRANSPORT_LE)
    - [x] `BluetoothGattCallback` — onConnectionStateChange, onServicesDiscovered, onMtuChanged
    - [x] Bağlantı durumu yönetimi: `ConnectionState` enum (DISCONNECTED, SCANNING, CONNECTING, CONNECTED)
- [x] **Servis ve Karakteristik Keşfi**
    - [x] UUID'leri keşfetme (`BleConstants.kt` — ECG_SERVICE_UUID, ECG_DATA_CHAR_UUID, DEVICE_STATUS_CHAR_UUID)
    - [x] EKG veri karakteristiğine abone olma (`setCharacteristicNotification` + CCCD Descriptor yazma)
    - [x] API 33+ / legacy uyumlu `onCharacteristicChanged` dual override
    - [x] MTU optimizasyonu (247 byte, `requestMtu()`)

### 2.4 — Veri Türleri & Protokol ✅
- [x] **Ham EKG Verisi (4× ADS1293 — 12 Derivasyon)**
    - [x] 43-byte çok-kanallı çerçeve: `[Header:0xAA][FrameSeq:1B][Timestamp:4B LE uint32][12×Lead:36B BE int24][Checksum:XOR]`
    - [x] `EcgPacketParser.kt` — 43-byte çerçeve ayrıştırma, her çerçeve 12 `EcgSample` üretir, checksum XOR, 24-bit sign extension
    - [x] Throughput: 250 Hz × 43 byte = 10.750 byte/sn = 86 kbps (BLE 5.0 2 Mbps kapasitesinin %4,3'i)
    - [x] Örnekleme hızı: 250 Hz (`BleConstants.SAMPLE_RATE_HZ`), kanal sayısı: 12 (`BleConstants.CHANNEL_COUNT`)
- [x] **Voltaj Dönüşümü**
    - [x] `EcgSample.fromRawAdc()` — `voltageUv = (rawAdc * 2.4V) / (2^23 * 6) * 1_000_000`
- [x] **Veri Modelleri (Kotlin)**
    - [x] `EcgSample.kt` — timestamp, channel (0–11 = I/II/III/aVR/aVL/aVF/V1–V6), rawAdc, voltageUv + `fromRawAdc()` companion
    - [x] `DeviceStatus.kt` — batteryPercent, isElectrodeConnected, isCharging, signalQuality + `fromByte()` companion
    - [x] `ScannedDevice.kt` — name, macAddress, rssi
    - [x] `ConnectionState.kt` — DISCONNECTED, SCANNING, CONNECTING, CONNECTED
    - [x] `HrvMetrics.kt` — sdnn, rmssd

### 2.5 — Veri İşleme Pipeline ✅
- [x] **Ring Buffer (Dairesel Tampon)** (`RingBuffer.kt`)
    - [x] Son 10 saniye = 2500 sample sabit boyutlu buffer
    - [x] Thread-safe: `ReentrantLock` ile `add()`, `getLastN()`, `getAll()`, `clear()`
- [x] **Gürültü Filtreleme** (`EcgFilter.kt`)
    - [x] HPF 0.5 Hz — Baseline wander kaldırma (1. derece IIR)
    - [x] Notch 50 Hz — Güç hattı gürültüsü filtreleme (2. derece IIR, Q≈30)
    - [x] LPF 40 Hz — Kas artefaktı azaltma (1. derece IIR Butterworth)
    - [x] Cascaded filter chain: HPF → Notch → LPF
- [x] **R-Peak Tespiti (BPM Hesaplama)** (`RPeakDetector.kt`)
    - [x] Basitleştirilmiş Pan-Tompkins: Derivative → Squaring → Moving Window Integration (150ms/37 sample)
    - [x] Adaptif eşik (threshold) ve refractory period (200ms)
    - [x] BPM = 60000 / mean(R-R intervals) (son 10 beat üzerinden)
    - [x] HRV: SDNN (R-R standart sapması), RMSSD (ardışık R-R farkları RMS)

### 2.6 — Canlı EKG Grafiği (ProModeScreen Entegrasyonu) ✅
- [x] **Canvas ile akan grafik** (`RealTimeEcgGraph` Composable)
    - [x] `EcgViewModel.graphPoints` StateFlow'dan gerçek zamanlı çizim
    - [x] X ekseni: son 4 saniye (1000 sample), Y ekseni: voltaj (µV, auto-scale)
    - [x] 25 mm/s kağıt hızı simülasyonu — minor grid (0.04s), major grid (0.2s)
    - [x] NeonRed glow efekti + 3px stroke ana iz
    - [x] Scanline animasyonu (NeonBlue, 3 saniyelik döngü)
- [x] **ViewModel Katmanı** (`EcgViewModel.kt`)
    - [x] `EcgRepository.observeEcgSamples()` → `EcgFilter` → `RingBuffer` → `RPeakDetector`
    - [x] 30 FPS UI güncellemesi (her 8 sample = ~33ms)
    - [x] StateFlow: `graphPoints`, `bpm`, `hrv`, `deviceStatus`, `connectionState`
- [x] **Mock Veri Üreteci** (`MockBleManager.kt`)
    - [x] Standart 12-lead morfoloji simülasyonu — her derivasyon için gerçekçi PQRST genlik/polarite katsayıları
    - [x] ∼72 BPM temel hız + sinüzoidal HRV
    - [x] Baseline wander (0.3 Hz), 50 Hz hat gürültüsü, rastgele kas artefaktı
    - [x] 43-byte çok-kanallı BLE çerçesi üretimi (header + frameSeq + timestamp + 12 lead + XOR checksum)

### 2.7 — Foreground Service (Arka Plan Bağlantısı) ✅
- [x] **EcgForegroundService** (`service/EcgForegroundService.kt`)
    - [x] `startForeground()` ile kalıcı bildirim
    - [x] Notification channel: "ecg_monitoring"
    - [x] `START_STICKY` — sistem tarafından öldürülürse yeniden başlatılır
    - [x] `ACTION_START` / `ACTION_STOP` companion fonksiyonları
    - [x] AndroidManifest'te `foregroundServiceType="connectedDevice"` kaydı

### 2.8 — Ekran Güncellemeleri ✅
- [x] **DashboardScreen** — Dinamik bağlantı durumu (statusText, statusColor), canlı BPM breathing circle
- [x] **SettingsScreen** — `EcgViewModel` + `DeviceScanViewModel` entegrasyonu, dinamik pil yüzdesi, DeviceScan navigasyonu
- [x] **ProModeScreen** — Bağlantı durumu dot (yeşil/sarı/kırmızı), canlı BPM/HRV/SDNN göstergesi
- [x] **MainActivity** — `MockBleManager` → `MockEcgRepository` → `EcgViewModel` + `DeviceScanViewModel` oluşturma, 10 rotaya navigasyon

---

## 🔄 FAZ 3: İleri DSP, DS-1D-CNN Yapay Zeka & Acil Durum Sistemi
**Amaç:** Araştırma önerisindeki ileri sinyal işleme algoritmalarını, DS-1D-CNN modelini eğitmek, TFLite INT8'e dönüştürmek ve acil durum sistemini tam olarak implement etmek.
**Kaynak:** 2209-A Araştırma Önerisi — Bölüm 3 (DSP), Bölüm 4 (AI Model), Bölüm 5 (Mobil Uygulama)
**Takvim (Araştırma Önerisinden):** 01.12.2025–28.02.2026 → 01.03.2026–30.04.2026
**Plan Dosyası:** `docs/plans/2026-02-24-phase3-dsp-ai-emergency-plan.md`

### Yeni Dosyalar (24 Şubat 2026 — BUILD SUCCESSFUL ✅)
| Dosya | Açıklama |
|---|---|
| `domain/model/ArrhythmiaClass.kt` | 6 sınıf enum (NORMAL/TACHY/BRADY/AF/ST/UNKNOWN) |
| `domain/model/AiPrediction.kt` | DS-1D-CNN tahmin sonucu (label, confidence, probs, topPredictions, inferenceMs) |
| `domain/model/AlertLevel.kt` | Uyarı seviyesi (NONE/ELECTRODE_OFF/LOW_SIGNAL/RECHECK/YELLOW/RED) |
| `domain/model/SignalQuality.kt` | SNR (dB), PRD (%), kalite skoru (0-100) |
| `domain/model/AlertEvent.kt` | Acil olay geçmişi (timestamp, level, bpm, lat, lon) |
| `domain/AlertEngine.kt` | Hibrit karar motoru (kural + AI, ≤%5 yanlış alarm hedefi) |
| `processing/AdvancedEcgProcessor.kt` | 6. derece Butterworth SOS + L=256 bazal düzeltme + SNR + db4 wavelet + 12-lead fusion |
| `processing/ArrhythmiaClassifier.kt` | TFLite INT8 çıkarım [1,12,2500] + otomatik mock mod (model yoksa) |
| `presentation/viewmodel/EmergencyViewModel.kt` | SMS (SmsManager), 112 arama (Intent.ACTION_CALL) |

### 3.1 — İleri Sinyal İşleme (Araştırma Önerisi §3) ✅
> **Dosya:** `mobile/.../processing/AdvancedEcgProcessor.kt`
- [x] **Bazal Düzeltme — Kayan Ortalama (L=256)**
    - [x] Pencere uzunluğu L=256 (~1 saniye @ 250Hz) — solunum kaynaklı düşük frekans sürüklenme
    - [x] O(1) kümülatif toplam farkıyla online hesaplama: `x̄[n] = x̄[n-1] + (x[n] - x[n-L]) / L`
    - [x] Düzeltilmiş sinyal: `x̂[n] = x[n] - x̄[n]`
    - [x] Dairesel tampon ile sınır etkisi yönetimi
- [x] **6. Derece Butterworth Bant Geçiren (0.5–40 Hz)**
    - [x] Mevcut `EcgFilter.kt` (1. derece IIR) yerine gerçek 6. derece Butterworth
    - [x] Bilinear dönüşüm + SOS (Second-Order Section) form — 3 ikinci dereceli bölüm
    - [x] Direct Form II transposed — sayısal kararlılık için
    - [x] Tek geçişli (düşük faz kaymalı) — gerçek zamanlı uygulama için
- [x] **Dalgacık Tabanlı Gürültü Azaltma (Daubechies-4)**
    - [x] Daubechies-4 (db4) wavelet — 4 seviye DWT ayrıştırma
    - [x] Gürültü tahmini: `σ ≈ MAD / 0.6745`, Donoho eşiği: `τ = σ√(2lnN)`
    - [x] Yumuşak eşikleme (soft thresholding) — yaklaşıklık katsayıları eşiklenmez
    - [x] `waveletDenoise()` — blok mod (test/kalibrasyon); online mod Butterworth
- [x] **Sinyal Kalite Kontrolü (SNR & PRD)**
    - [x] `SignalQuality` veri sınıfı: snrDb, prd, score (0-100), isAcceptable (SNR≥12)
    - [x] `computeSignalQuality()` — 10 saniyelik pencere RMS/RMSSD oranı proxy SNR
    - [x] `computePrd()` — PRD hesaplama metodu
    - [x] `EcgViewModel` her saniyede `_signalQuality` StateFlow'u günceller

### 3.2 — Gürültü Modellemesi & Simülasyon (§3.4) ✅
> **Dosya:** `mobile/.../data/bluetooth/MockBleManager.kt`
- [x] **Parametrik Gürültü Modeli (§3.4)**
    - [x] `NoiseProfile` enum: CLEAN (40dB), NORMAL (18dB), NOISY (12dB), EXTREME (6dB)
    - [x] Kas gürültüsü (20–200 Hz geniş bant EMG): 3 sinüzoid + rastgele bileşen, `muscleGain` ile ölçekleme
    - [x] Elektrot artefaktı: düşük frekans drift (0.15 Hz) + rastgele spike (p=0.001)
    - [x] Kontrollü SNR hedefleme: `NoiseProfile` ile 6–40 dB arası seçilebilir
- [x] **12 Kanallı Simülasyon**
    - [x] 12 lead PQRST morfoloji simülasyonu (lead-spesifik R/T dalgası ölçekleme)
    - [x] Her kanala bağımsız gürültü (kanal indeksine göre faz farkı)
- [x] **Gürültü Dayanıklılık Testi Sonuçları**
    - [x] SNR 6dB: AUC 0.958 | SNR 12dB: AUC 0.978 | Clean: AUC 0.984

### 3.3 — DS-1D-CNN Yapay Zeka Modeli (Python Eğitim Altyapısı) ✅
> **Platform:** Python 3.11 + PyTorch 2.6.0+cu124 | **GPU:** RTX 4050 Laptop (6 GB VRAM, CUDA 12.4)
> **Dataset:** PhysioNet SPH 12-Lead ECG Arrhythmia (26,395 clean records, 55 SNOMED-CT sınıfı)
> **Mimari Dokümantasyonu:** `docs/model/MODEL_DOCUMENTATION.md`
- [x] **Veri Hazırlığı**
    - [x] `dataset/ecg-arrhythmia/` WFDB kayıtlarını okuma (`wfdb` + `numpy`) — 45,152 ham kayıt
    - [x] Ön-işleme: 2. derece Butterworth bant geçiren (0.5–40 Hz) → downsample (500→250 Hz) → per-lead z-score normalizasyon
    - [x] NaN koruma: `nan_to_num` + `isfinite` kontrolü — 47 dejenere kayıt otomatik elendi
    - [x] Hasta bağımsız 70/15/15 bölme: Train 18,476 / Val 3,959 / Test 3,960 (`train_test_split`, seed=42)
    - [x] 55 SNOMED-CT multi-label: BCEWithLogitsLoss ile çok etiketli sınıflandırma
    - [x] Dataset önbellek: `dataset_cache.npz` (~2.8 GB) — MD5 hash ile değişiklik algılama
- [x] **Model Mimarisi (DS-1D-CNN — Depthwise Separable 1D CNN)**
    - [x] Stem: Conv1d(12→32, k=15, s=2) → BN → ReLU6
    - [x] 5× DSConv blok: DW Conv1d(groups=C) → BN → ReLU6 → PW Conv1d(1×1) → BN → ReLU6
    - [x] Kanal dizisi: 32 → 64 → 128 → 128 → 256 → 256
    - [x] Head: AdaptiveAvgPool1d(1) → Flatten → Dropout(0.3) → Linear(256→128) → BN → ReLU6 → Linear(128→55)
    - [x] Toplam parametre: **176,599** | Toplam nöron (Conv+Linear): **1,047** | FLOPs: **38.7 MFLOPs**
    - [x] PT dosya boyutu: 726.4 KB | ONNX: 694.3 KB
- [x] **Eğitim**
    - [x] Adam optimizer: lr=1e-3 | BCEWithLogitsLoss | Gradient clipping: max_norm=1.0
    - [x] ReduceLROnPlateau: patience=4, factor=0.5 | Early stop patience=10
    - [x] LR takvimi: 1e-3 → 5e-4 (ep15) → 2.5e-4 (ep20)
    - [x] **20/50 epoch eğitildi** (epoch 10'dan sonra 10 epoch iyileşme yok → early stop)
    - [x] **En iyi val AUC: 0.9356** @ Epoch 10
    - [x] Training log: `dataset/models/training_log.csv`
- [x] **Test Seti Değerlendirmesi (3,960 kayıt)**
    - [x] **PyTorch FP32:** Macro AUC=0.9517 | Micro AUC=0.9924 | Micro F1=0.8581 | Hit Rate=0.9568
    - [x] **TFLite INT8:** Macro AUC=0.9334 | Micro AUC=0.9916 | Micro F1=0.8592 | Hit Rate=0.9773
    - [x] Quantization kaybı: Macro AUC'de yalnızca -0.018 fark (3× boyut azaltma karşılığı)
    - [x] 38/55 aktif sınıf test setinde mevcut
    - [x] En iyi sınıflar: SB(0.999), SR(0.999), AFIB(0.999), 3AVB(0.996), RBBB(0.994)
    - [x] Detaylı sonuçlar: `dataset/models/evaluation_results.json`, `dataset/models/tflite_evaluation_results.json`
- [x] **Hız Benchmarkı**
    - [x] GPU single: 1.94 ms (516 ECG/s) | GPU batch=32: 0.95 ms (33,810 ECG/s)
    - [x] ONNX Runtime CPU: 4.56 ms (220 ECG/s)
    - [x] **TFLite INT8 CPU: 0.84 ms (1,185 ECG/s)** — Android için 40% daha hızlı, 3× daha küçük
    - [x] TFLite FP16 CPU: 1.14 ms (878 ECG/s) | TFLite FP32 CPU: 1.18 ms (846 ECG/s)
- [x] **Model Dönüşümü & Export**
    - [x] PyTorch FP32 → ONNX opset 17 (SigmoidWrapper ile probability çıkışı)
    - [x] ONNX → TFLite FP32/FP16 (`onnx2tf`) + TFLite INT8 (200 ECG kalibrasyon örneği ile representative dataset quantization)
    - [x] **Hedef karşılandı:** 231.6 KB model boyutu (<2.1 MB ✅), 0.84 ms inference (<22 ms ✅)
    - [x] Üç varyant: `ecg_model_float32.tflite` (698 KB), `ecg_model_float16.tflite` (359 KB), `ecg_model_int8.tflite` (232 KB)
    - [x] `mobile/app/src/main/assets/ecg_model_int8.tflite` olarak Android projesine gömüldü (237 KB)

### 3.3b — DCA-CNN Dinamik Kanal Adaptif Model (Araştırma Önerisi §4) ✅
> **Platform:** Python 3.11 + PyTorch 2.6.0+cu124 | **GPU:** RTX 4050 Laptop
> **Dataset:** 6 PhysioNet veri seti (54,466 train / 10,312 val)
> **Dosya:** `ai/training/train_dca_cnn.py`
- [x] **DCA-CNN Mimarisi (§4, Denklem 13-22)**
    - [x] ACC katmanı: $W_c = W_{\text{base}} + \Delta W_c$ — paylaşılan temel çekirdek + kanal-spesifik offset
    - [x] Öğrenilebilir kapılar: $g_c = \sigma(\alpha_c)$ — her kanal için soft gate
    - [x] Gate regülarizasyonu: $\mathcal{L}_{\text{gate}} = \lambda_g \sum g_c^2$ (inaktif kanallar)
    - [x] Squeeze-and-Excitation kanal dikkat: global avg pool → FC bottleneck → sigmoid scale
    - [x] Faz regülarizasyonu: $\mathcal{L}_{\text{phase}}$ — FFT + ideal Butterworth referans L2
    - [x] Toplam kayıp: $\mathcal{L} = \mathcal{L}_{\text{BCE}} + \lambda_g \mathcal{L}_{\text{gate}} + \lambda_\phi \mathcal{L}_{\text{phase}}$
    - [x] Toplam parametre: **261,091** (<500K hedefi ✅)
- [x] **Data Augmentation (§4)**
    - [x] Gaussian gürültü (σ=0.05, p=0.5)
    - [x] Bazal sürüklenme (0.1-0.5 Hz sinüzoid, p=0.3)
    - [x] Zaman ölçekleme (±10% resampling, p=0.2)
    - [x] Kanal dropout (p=0.1 per lead, p=0.3)
    - [x] 5 saniyelik örtüşmeli pencereler (`preprocess_with_overlap()`)
- [x] **Channel Dropout Eğitimi**
    - [x] 12-kanal: %50 | 3-kanal (I,II,III): %25 | 1-kanal (Lead II): %25
- [x] **Eğitim Sonuçları**
    - [x] AdamW + CosineAnnealingWarmRestarts (T₀=10, T_mult=2)
    - [x] Mixed precision (AMP) — 6GB VRAM ile eğitim
    - [x] **Val AUC: 0.9513** @ Epoch 25/50 (early stop @ 35)
- [x] **QAT (Quantization-Aware Training, §4.1)**
    - [x] 15 epoch QAT fine-tuning — AUC **0.9535** (FP32'den daha iyi!)
    - [x] AUC kaybı: **-0.001** (hedef < 0.005 ✅)
    - [x] TFLite INT8: **312.3 KB** (<500 KB hedefi ✅)
- [x] **Çapraz-Veri Seti Değerlendirme (12/3/1-lead)**
    - [x] SPH 12-lead: AUC 0.968 | 3-lead: 0.948 | 1-lead: 0.899
    - [x] Georgia 12-lead: AUC 0.864 (DS-1D-CNN'den +2.6%)
    - [x] CPSC2018-Extra 12-lead: AUC 0.833 (DS-1D-CNN'den +4.4%)
- [x] **TFLite Hız Benchmarkı**
    - [x] DCA-CNN INT8: **0.90 ms** (1,105 ECG/s) | FP32: 1.22 ms
    - [x] DS-1D-CNN INT8: 0.55 ms (1,811 ECG/s) — referans
- [x] **Gürültü Dayanıklılık Testi**
    - [x] SNR 6dB: AUC 0.958 | SNR 12dB: 0.978 | Clean: 0.984
- [x] **Android Deploy**
    - [x] `ecg_dca_cnn_int8.tflite` (312 KB) → `mobile/app/src/main/assets/` (primary)
    - [x] `ecg_model_int8.tflite` (232 KB) → fallback model

### 3.3c — Çok Kanallı Korelasyon ve PCA Tutarlılık (§3.6) ✅
> **Dosya:** `mobile/.../processing/AdvancedEcgProcessor.kt`
- [x] Kovaryans matrisi hesaplama: `computeCovarianceMatrix(channels)`
- [x] Baskın özdeğer (power iteration): `dominantEigenvalue(matrix)`
- [x] Tutarlılık analizi: `analyzeMultiChannelConsistency(channels)` → `PcaResult`
    - [x] `dominantRatio`: iskemik patern (yüksek) vs artefakt (düşük) ayrımı
    - [x] `artifactChannels`: varyans oranı > 5x veya < 0.1x olan kanallar
    - [x] `channelConsistencyScore`: 0-100 arası tutarlılık skoru

### 3.4 — Android TFLite Inference Modülü ✅
> **Dosya:** `mobile/app/src/main/java/.../processing/ArrhythmiaClassifier.kt`
- [x] **TFLite Interpreter Kurulumu**
    - [x] Reflection tabanlı yükleme — TFLite bağımlılığı eklenince otomatik aktive olur
    - [x] Model mevcut değilse → otomatik mock mod (kural tabanlı tahmin)
    - [x] Giriş tensor: `[1, 2500, 12]` (channels-last INT8), çıkış: `[1, 55]` (float32 sigmoid)
    - [x] INT8 quantization: scale=0.0909, zero_point=-9
- [x] **10 Saniyelik Pencere Yönetimi**
    - [x] Her 2500 örnekte 12-kanal `multiChannelBuffer` → `ArrhythmiaClassifier.classify(window)`
    - [x] `Dispatchers.Default` coroutine'de arka plan çıkarımı (UI thread'i bloklamaz)
    - [x] `EcgViewModel._aiPrediction: MutableStateFlow<AiPrediction>` eklendi
    - [x] Mock mod: RMSSD/RMS oranı → AF / Normal kural tahmini

### 3.5 — Aritmia Tespit Motoru (Kural Tabanlı + AI Hybrid) ✅
> **Dosya:** `mobile/app/src/main/java/.../domain/AlertEngine.kt`
- [x] **Kural Tabanlı Birincil Kontroller**
    - [x] Elektrot teması kaybı → `AlertLevel.ELECTRODE_OFF`
    - [x] SNR < 12 dB → `AlertLevel.LOW_SIGNAL`
    - [x] Taşikardi: BPM > 120 ve 30 saniye sürekli → `AlertLevel.YELLOW`
    - [x] Bradikardi: BPM < 50 ve 30 saniye sürekli → `AlertLevel.YELLOW`
    - [x] R-R CV > 0.20 ve 30 saniye → `AlertLevel.YELLOW`
- [x] **AI Hybrid Karar**
    - [x] DS-1D-CNN güven ≥ 0.80 ve kritik sınıf → `AlertLevel.RED`
    - [x] DS-1D-CNN güven ≥ 0.80, non-normal → `AlertLevel.YELLOW`
    - [x] DS-1D-CNN güven < 0.55 → `AlertLevel.RECHECK`
- [x] **Uyarı Seviyesi StateFlow**
    - [x] `AlertLevel` enum: NONE/ELECTRODE_OFF/LOW_SIGNAL/RECHECK/YELLOW/RED
    - [x] `EcgViewModel._alertLevel: MutableStateFlow<AlertLevel>` — her 1 saniyede güncelleme
- [x] **Renk Kodlu UI Güncellemesi** ✅
    - [x] `DashboardScreen` breathing circle rengi: Emerald(NONE)/Amber(YELLOW)/AlarmRed(RED)
    - [x] `DashboardScreen` AI Notu kartı dinamik (aiPrediction'dan label + confidence)
    - [x] `ProModeScreen` AI tahmin + sinyal kalite kartı
    - [x] `AlertLevel.RED` → otomatik `EmergencyScreen` navigasyonu (`LaunchedEffect`)

### 3.6 — Acil Durum Sistemi (SMS + Arama + Konum) ✅
> PR #2 ile izinler zaten eklendi: `SEND_SMS`, `CALL_PHONE`, `ACCESS_FINE_LOCATION`
- [x] **EmergencyViewModel.kt oluşturuldu**
    - [x] `SmsManager.sendMultipartTextMessage()` — kayıtlı acil kişiye SMS
    - [x] SMS şablonu: BPM, AI etiketi, konum URL'si (lat/lon mevcut değilse "Konum alınamadı")
    - [x] `PendingIntent` ile SMS gönderim onay takibi
    - [x] `callEmergencyServices()` — `Intent.ACTION_CALL tel:112`
    - [x] `StateFlow<Boolean> smsSent`, `StateFlow<String?> smsError`
- [x] **GPS Konum Alma** ✅
    - [x] `FusedLocationProviderClient.getCurrentLocation(HIGH_ACCURACY)`
    - [x] 10s timeout (`withTimeoutOrNull`), permission check
- [x] **EmergencyScreen Güçlendirmesi** ✅
    - [x] EmergencyViewModel bağlantısı + smsSent/smsError StateFlow UI
    - [x] Otomatik 10s geri sayım sonrası SMS + 112 arama (`LaunchedEffect`)

### 3.7 — Doktor Raporlama & CSV Export ✅
> **Dosyalar:** `data/recording/EcgSessionRecorder.kt`, `data/export/CsvExporter.kt`, `data/export/PdfReportGenerator.kt`
- [x] **EKG Oturum Kaydı**
    - [x] `EcgSessionRecorder` — binary format (32B header + 18B/sample: timestamp, channel, rawAdc, voltageUv)
    - [x] `EcgViewModel.startRecording(userId)` / `stopRecording()` — kayıt başlat/durdur
    - [x] Kayıt sırasında BPM izleme (min/max/avg) → Room'a otomatik kayıt
    - [x] BufferedOutputStream (8KB buffer) ile yüksek throughput
- [x] **CSV Export**
    - [x] `timestamp_ms, channel, rawAdc, voltageUv` sütunları
    - [x] `ContentValues` + `MediaStore.Downloads` ile scoped storage (Android 10+)
    - [x] Legacy API desteği (Android 9-)
    - [x] `Intent.ACTION_SEND` ile paylaşım menüsü
- [x] **PDF Rapor (Android native PdfDocument API)**
    - [x] Sayfa 1: Başlık bar + hasta bilgileri + BPM metrikleri (3 renkli kutu) + sinyal kalitesi
    - [x] Sayfa 2: EKG grafiği (Lead II, 25mm/s standart grid, kırmızı iz)
    - [x] Sayfa 3: DCA-CNN AI tahmin sonuçları + uyarı geçmişi tablosu (15 satır)
    - [x] Disclaimer: "Tanı amaçlı kullanılmaz"
- [x] **E-posta / Paylaşım**
    - [x] `FileProvider` + `Intent.ACTION_SEND` ile PDF/CSV paylaşım (doktor e-posta)

---

## 💾 FAZ 4: Veri Saklama & Senkronizasyon
**Amaç:** Kullanıcı ve EKG verilerini güvenli şekilde saklamak; KVKK uyumlu.

### 4.1 — Room Veritabanı ✅
> **Dosyalar:** `data/local/entity/*.kt`, `data/local/dao/*.kt`, `data/local/HayatinRitmiDatabase.kt`
- [x] **Tablo Yapısı (4 Entity)**
    - [x] `UserEntity` — id, name, surname, phone, bloodType, emergencyContact, doctorEmail, passwordHash, salt, biometricEnabled, createdAt
    - [x] `EcgSessionEntity` — id, userId (FK), startTimeMs, durationMs, avgBpm, minBpm, maxBpm, filePath, qualityScore, aiLabel, aiConfidence, sampleCount
    - [x] `EcgAlertEntity` — id, sessionId (FK), timestampMs, type, level, details, aiConfidence, bpm, lat, lon, isRead
    - [x] `DeviceInfoEntity` — id, mac, name, lastConnectedMs, firmwareVersion, batteryPercent
- [x] **DAO (4 adet)**
    - [x] `UserDao` — CRUD + giriş doğrulaması (phone lookup) + Flow observeById
    - [x] `EcgSessionDao` — kayıt ekleme, tarih bazlı sorgulama, SessionStats aggregate, Flow getSessionsByUser
    - [x] `EcgAlertDao` — uyarı ekleme, filtreleme, okunmamış sayısı (Flow), markAsRead/markAllAsRead
    - [x] `DeviceInfoDao` — UPSERT by MAC, last connected query
- [x] **Room Database**
    - [x] `HayatinRitmiDatabase` — 4 entity, exportSchema=false, fallbackToDestructiveMigration

### 4.2 — Kullanıcı Kayıt/Giriş ✅
> **Dosyalar:** `data/repository/UserRepositoryImpl.kt`, `presentation/viewmodel/AuthViewModel.kt`
- [x] **Kayıt Akışı**
    - [x] `UserRepository.register()` — telefon duplicate kontrolü + Room'a yazma
    - [x] PBKDF2-SHA256 şifre hash'leme (65536 iterasyon, 256-bit, SecureRandom salt)
    - [x] `AuthViewModel` — register state management (Idle/Loading/Success/Error)
- [x] **Giriş Doğrulaması**
    - [x] `UserRepository.authenticate()` — phone lookup + hash karşılaştırma
    - [x] `AuthViewModel.login()` — login state management
    - [x] BiometricPrompt API entegrasyonu (enableBiometric flag)
    - [x] Current user tracking (currentUserId volatile cache)
- [x] **Birim Testleri: 10 test geçti** ✅

### 4.3 — Veri Güvenliği & KVKK ✅
> **Dosya:** `di/DatabaseModule.kt`
- [x] **Şifreli Depolama**
    - [x] SQLCipher şifreleme: `sqlcipher-android:4.6.1` + `SupportOpenHelperFactory`
    - [x] 32-byte SecureRandom passphrase, SharedPreferences'te hex olarak saklama
    - [x] `UserRepository.deleteUser()` — kullanıcı verisi silme
- [x] **Paylaşım Güvenliği**
    - [x] `FileProvider` ile güvenli dosya paylaşımı (CSV/PDF)
    - [x] `FLAG_GRANT_READ_URI_PERMISSION` ile URI bazlı erişim kontrolü
- [ ] **Gelecek (Opsiyonel)**
    - [x] EncryptedFile (Jetpack Security) ile binary kayıt şifreleme
    - [x] WorkManager ile çevrimdışı senkronizasyon

---

## 🔬 FAZ 5: Doğrulama, Test & Yaygınlaştırma
**Amaç:** Sistemi sahada sınamak, performans kriterlerini ölçmek ve yaygın etkiyi gerçekleştirmek.

### 5.1 — Performans Hedefleri (Araştırma Önerisinden)
- [ ] **Doğruluk:** ≥%95 doğruluk eşiği (60 saatlik pilot deneme)
- [ ] **Gecikme:** Şüpheli durumda uyarı ≤1 saniye
- [ ] **Yanlış Alarm:** Gereksiz alarm oranı ≤%5
- [ ] **Kullanıcı Deneyimi:** SUS (System Usability Scale) puanı ≥75
- [ ] **Kararlılık:** Crash-free oranı ≥%98
- [x] **TFLite Performans:** tek kanal <22ms, üç kanal <38ms, bellek <2.1MB (benchmark raporunda sağlandı)

### 5.2 — Test Stratejisi
- [x] **Birim+Entegrasyon Testleri (81/81 geçti)** ✅
    - [x] `EcgFilter` — 5 test (HPF/LPF/Notch frekans cevabı)
    - [x] `RPeakDetector` — 6 test (sentetik PQRST BPM doğruluğu)
    - [x] `RingBuffer` — 7 test (thread safety, overflow, getLastN)
    - [x] `AdvancedEcgProcessor` — 8 test (PCA, kovaryans, eigenvalue, tutarlılık)
    - [x] `AlertEngine` — 7 test (kural tabanlı + AI hibrit karar)
    - [x] `UserRepositoryImpl` — 10 test (kayıt, giriş, PBKDF2, duplicate, biometric)
    - [x] `SessionRepositoryImpl` — 6 test (session CRUD, alert, markAsRead, pending sync)
    - [x] `BackpressureManager` — 10 test (pressure levels, energy modes, battery, drop rate)
    - [x] `SlidingCorrelationParser` — 9 test (frame parsing, fragmentation, checksum, alignment)
    - [x] `AccessibilityUtils` — 10 test (TalkBack descriptions, contrast ratio, WCAG)
    - [x] `BlePipelineIntegrationTest` — 2 test (connected frame pipeline, connect/disconnect stres)
    - [x] `ExampleUnitTest` — 1 test
- [ ] **Entegrasyon Testleri**
    - [x] Mock BLE → Repository pipeline entegrasyon testi
    - [x] BLE bağlantı/bağlantı kesme döngüsü stres testi
- [ ] **Saha Pilot Denemeleri**
    - [x] Pilot yürütme paketi hazırlandı (`docs/validation/` runbook + SUS + CSV şablonları + metrik scripti)
    - [ ] En az 60 saatlik EKG kaydı
    - [ ] Farklı aktivite senaryoları (istirahat, yürüyüş, merdiven, koşu)
    - [ ] Elektrot kalitesi ve hareket artefaktı değerlendirmesi

### 5.3 — Yaygın Etki & Çıktılar
- [ ] **Bilimsel Çıktılar**
    - [x] En az 1 ulusal/uluslararası kongre bildirisi (taslak hazır)
    - [x] Teknik rapor + kullanım kılavuzu
    - [x] Açık kaynak kod ve model bileşenleri (MIT/Apache lisansı)
- [ ] **Prototip Çıktıları**
    - [ ] ADS1293 tabanlı giyilebilir sensör + BLE + mobil uygulama (TRL 4-5)
    - [ ] Mobil uygulama MVP
- [ ] **Gelecek Proje Hazırlıkları**
    - [ ] TÜBİTAK 1001 başvurusu için ön çalışma (klinik doğrulama)
    - [ ] TEYDEB 1501/1507 sanayi iş birliği (üretimleşme)
    - [ ] TÜBİTAK 1512 BİGG ön-kuluçka (girişimcilik)

---

## 📝 Teknik Notlar
- **Donanım:** ADS1293 (3 kanallı, 24-bit, 250 Hz) + STM32F103C8T6 (MCU) + nRF52832 (BLE 5.0) — Araştırma Önerisi Referans
- **Donanım (Prototip/Mock):** ESP32-C3/S3 + ADS1293 (tek kanal EKG), BLE 5.0 — Mevcut Geliştirme
- **Tasarım dili:** Neon/Cyberpunk & Glassmorphism (Koyu Tema)
- **Min SDK:** 24 (Android 7.0)
- **Aktif Proje Dizini:** `mobile/` (Clean Architecture) — `app/hayatin_ritmi/` FAZ 1-2 prototipi
- **Son Build:** ✅ BUILD SUCCESSFUL — Gradle 8.13, Kotlin 2.1.0, AGP 8.7.3, Hilt 2.51.1, Room 2.6.1, SQLCipher 4.6.1 (28 Şub 2026)
- **Test Durumu:** Python AI: 22/22 geçti | Android: 81/81 geçti (12 test suite) | **Toplam: 103/103** ✅
- **FAZ 3 AI Durumu:** ✅ Tüm bileşenler tamamlandı. DCA-CNN (261K param), QAT INT8 (312KB), augmentation, PCA, gürültü modeli, 6 dataset cross-eval.
- **FAZ 4 Durumu:** ✅ Room DB (4 entity, 4 DAO, SQLCipher), PBKDF2 auth, session recording, CSV/PDF export, Hilt DI.
- **FAZ 5 Kısmi:** ✅ BackpressureManager, SlidingCorrelationParser, WCAG AccessibilityUtils, BLE pipeline integration testleri. 81/81 Android test.
- **Pilot Hazırlık Paketi:** ✅ `docs/validation/` altında runbook, SUS formu, CSV şablonları ve `ai/evaluation/pilot_metrics_report.py` eklendi.
- **Kalan Tek Bağımlılık:** ⚪ Saha testlerinin fiziksel donanımla icrası (60 saat pilot).
- **AI Model Dokümantasyonu:** `docs/model/MODEL_DOCUMENTATION.md` + `docs/plans/2026-03-master-implementation-status.md`
- **Aktif AI Modeli:** DCA-CNN INT8 (ecg_dca_cnn_int8.tflite, 312 KB) — DS-1D-CNN fallback (ecg_model_int8.tflite, 232 KB)
- **Hedef SDK:** 35 (Android 15)
- **AGP:** 8.7.3, **Kotlin:** 2.1.0, **Gradle:** 8.13, **Compose BOM:** 2024.11.00
- **Java:** Eclipse Temurin JDK 25.0.2 (gradle.properties ile yapılandırılmış)
- ✅ Build başarılı (assembleDebug) — FAZ 2 tamamlandı
- ⚠️ Dizin adındaki Türkçe karakter (ı) Gradle path sorununa neden oluyor, `hayatin_ritmi` (ASCII) kopyası build için kullanılmalı

---

## 📂 Dosya Yapısı (FAZ 2 Sonrası)

```
app/hayatin_ritmi/app/src/main/java/com/hayatinritmi/app/
├── MainActivity.kt              # NavHost (10 rota) + ViewModel oluşturma
├── ble/
│   ├── BleManager.kt            # Interface: scan, connect, disconnect, observeEcgData
│   ├── MockBleManager.kt        # Simüle PQRST dalga formu üreteci (250Hz)
│   ├── RealBleManager.kt        # Gerçek Android BLE API (GATT + Scanner)
│   └── BlePermissionHelper.kt   # Dinamik izin yönetimi (Android 12+/11-)
├── data/
│   ├── model/
│   │   ├── EcgSample.kt         # timestamp, channel, rawAdc, voltageUv + fromRawAdc()
│   │   ├── DeviceStatus.kt      # batteryPercent, electrode, charging + fromByte()
│   │   ├── ScannedDevice.kt     # name, macAddress, rssi
│   │   ├── ConnectionState.kt   # DISCONNECTED, SCANNING, CONNECTING, CONNECTED
│   │   └── HrvMetrics.kt        # sdnn, rmssd
│   ├── BleConstants.kt          # UUID'ler, PACKET_HEADER, SAMPLE_RATE_HZ
│   ├── EcgPacketParser.kt       # 10-byte BLE paket ayrıştırma + checksum doğrulama
│   ├── EcgRepository.kt         # Interface: observeEcgSamples(), observeDeviceStatus()
│   ├── MockEcgRepository.kt     # BleManager → EcgRepository köprüsü (mock)
│   └── BleEcgRepository.kt      # BleManager → EcgRepository köprüsü (gerçek BLE)
├── processing/
│   ├── RingBuffer.kt            # Thread-safe dairesel tampon (2500 sample, ReentrantLock)
│   ├── EcgFilter.kt             # Cascaded IIR: HPF 0.5Hz → Notch 50Hz → LPF 40Hz
│   └── RPeakDetector.kt         # Pan-Tompkins: derivative → square → MWI → adaptif eşik
├── service/
│   └── EcgForegroundService.kt  # startForeground + notification + START_STICKY
├── viewmodel/
│   ├── EcgViewModel.kt          # ECG pipeline: Filter → RingBuffer → RPeakDetector → StateFlow
│   └── DeviceScanViewModel.kt   # Scan/connect/disconnect + DataStore persistance
├── screens/
│   ├── LoginScreen.kt
│   ├── SignUpScreen.kt
│   ├── ForgotPasswordScreen.kt
│   ├── DashboardScreen.kt       # ✅ Dinamik bağlantı durumu + canlı BPM
│   ├── ProModeScreen.kt         # ✅ Canvas EKG grafik + canlı BPM/HRV/SDNN
│   ├── EmergencyScreen.kt
│   ├── SettingsScreen.kt        # ✅ Dinamik pil + DeviceScan navigasyonu
│   ├── NotificationScreen.kt
│   └── DeviceScanScreen.kt      # ✅ YENİ: Radar animasyonu + cihaz listesi
└── ui/theme/
    ├── Color.kt
    ├── Theme.kt
    └── Type.kt
```

---

## 📅 Çalışma Takvimi (2209-A Araştırma Önerisinden)

| Tarih Aralığı | Faaliyetler | Başarı Ölçütü | Katkı |
|---|---|---|---|
| 01.11.2025–30.11.2025 | Proje çerçevesi, WBS, risk analizi | Onaylı çerçeve ve metodoloji | 12/100 |
| 01.12.2025–28.02.2026 | Veri/donanım altyapısı, temel AI, mobil çekirdek | Veri ≥60 saat; Rev A prototip; val F1 ≥0.90; çalışan mobil | 38/100 |
| 01.03.2026–30.04.2026 | Bileşen entegrasyonu ve optimizasyon | Entegre demo; TFLite ≤40ms; test ≥%90 geçer | 27/100 |
| 01.05.2026–30.06.2026 | Kapalı beta, performans ve kullanılabilirlik ölçümü | SUS ≥75; crash-free ≥%98; gecikme ≤1s; yanlış alarm ≤%5 | 17/100 |
| 01.07.2026–31.07.2026 | Nihai rapor, arşiv, kapanış | Teslimlerin %100'ü kabul; DOI/depo aktif | 6/100 |
