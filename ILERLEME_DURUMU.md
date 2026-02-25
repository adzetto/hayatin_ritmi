# 🚀 TÜBİTAK 2209-A Proje İlerleme ve Görev Takibi

Bu dosya, projenin geliştirme sürecini adım adım takip etmek için oluşturulmuştur.

**Proje Başlığı:** Çok Kanallı Adaptif Yapay Zekâ Tabanlı Taşınabilir EKG Analiz Sistemi
**Başvuru Sahibi:** İsmail Sakci | **Danışman:** Mehmet Zübeyir Ünlü
**Kurum:** İzmir Yüksek Teknoloji Enstitüsü

## 📅 Genel Durum
- **Başlangıç Tarihi:** 19 Şubat 2026
- **Mevcut Faz:** FAZ 3 (İleri DSP, DS-1D-CNN AI & Acil Durum Sistemi) — **AI Modeli Eğitildi ✅**
- **Hedef:** ADS1293 + STM32 + nRF52832 tabanlı EKG tişörtüyle BLE bağlantısı kurmak, canlı veri almak, DS-1D-CNN ile analiz etmek ve acil durum uyarısı göndermek.
- **AI Durumu:** DS-1D-CNN eğitildi (Macro AUC=0.9517), TFLite INT8 export tamamlandı (231.6 KB, 0.84 ms/inference)
- **Mimari:** Clean Architecture — `domain/` (model + interface) → `data/` (bluetooth + repository) → `presentation/` (screen + viewmodel) | Repository Pattern (Mock/Real BLE abstraction) + ViewModel + Manual DI

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
| `domain/model/AiPrediction.kt` | DCA-CNN tahmin sonucu (label, confidence, probs, inferenceMs) |
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

### 3.2 — Gürültü Modellemesi & Simülasyon (MockBleManager Güncellemesi)
> **Dosya:** `mobile/.../data/bluetooth/MockBleManager.kt` — FAZ 3.2 ileriki aşamada
- [ ] **Gerçekçi Artefakt Enjeksiyonu**
    - [ ] Kas gürültüsü (20–200 Hz geniş bant): `α = √(P_x / (P_s × 10^(-SNR/10)))`
    - [ ] Elektrot artefaktı: düşük frekans (<1Hz) dalgalanma + ani sıçramalar
    - [ ] Kontrollü SNR hedefleme: 6–18 dB aralığında segment bazında farklı tohumlarla
- [ ] **Çok Kanallı Simülasyon (3 Kanal)**
    - [ ] Lead I, II, III: Einthoven (Lead III = Lead II - Lead I)
    - [ ] Her kanala bağımsız gürültü modeli

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
    - [ ] `mobile/app/src/main/assets/ecg_model_int8.tflite` olarak Android projesine gömme (sonraki adım)

### 3.4 — Android TFLite Inference Modülü ✅
> **Dosya:** `mobile/app/src/main/java/.../processing/ArrhythmiaClassifier.kt`
- [x] **TFLite Interpreter Kurulumu**
    - [x] Reflection tabanlı yükleme — TFLite bağımlılığı eklenince otomatik aktive olur
    - [x] Model mevcut değilse → otomatik mock mod (kural tabanlı tahmin)
    - [x] Giriş tensor: `[1, 2500, 12]` (channels-last INT8), çıkış: `[1, 55]` (float32 sigmoid)
    - [x] INT8 quantization: scale=0.0909, zero_point=-9
- [x] **10 Saniyelik Pencere Yönetimi**
    - [x] Her 2500 örnekte `RingBuffer.getAll()` → `ArrhythmiaClassifier.classify()`
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
    - [x] DCA-CNN güven ≥ 0.80 ve kritik sınıf → `AlertLevel.RED`
    - [x] DCA-CNN güven ≥ 0.80, non-normal → `AlertLevel.YELLOW`
    - [x] DCA-CNN güven < 0.55 → `AlertLevel.RECHECK`
- [x] **Uyarı Seviyesi StateFlow**
    - [x] `AlertLevel` enum: NONE/ELECTRODE_OFF/LOW_SIGNAL/RECHECK/YELLOW/RED
    - [x] `EcgViewModel._alertLevel: MutableStateFlow<AlertLevel>` — her 1 saniyede güncelleme
- [ ] **Renk Kodlu UI Güncellemesi** (sonraki aşama)
    - [ ] `DashboardScreen` breathing circle rengi: Emerald(NONE)/Amber(YELLOW)/AlarmRed(RED)
    - [ ] `ProModeScreen` AI tahmin + sinyal kalite kartı
    - [ ] `AlertLevel.RED` → otomatik `EmergencyScreen` navigasyonu

### 3.6 — Acil Durum Sistemi (SMS + Arama + Konum) — Kısmen ✅
> PR #2 ile izinler zaten eklendi: `SEND_SMS`, `CALL_PHONE`, `ACCESS_FINE_LOCATION`
- [x] **EmergencyViewModel.kt oluşturuldu**
    - [x] `SmsManager.sendMultipartTextMessage()` — kayıtlı acil kişiye SMS
    - [x] SMS şablonu: BPM, AI etiketi, konum URL'si (lat/lon mevcut değilse "Konum alınamadı")
    - [x] `PendingIntent` ile SMS gönderim onay takibi
    - [x] `callEmergencyServices()` — `Intent.ACTION_CALL tel:112`
    - [x] `StateFlow<Boolean> smsSent`, `StateFlow<String?> smsError`
- [ ] **GPS Konum Alma** (play-services-location bağımlılığı eklenince)
    - [ ] `FusedLocationProviderClient.getCurrentLocation(HIGH_ACCURACY)`
    - [ ] Network + GPS hibrit, 10s timeout
- [ ] **EmergencyScreen Güçlendirmesi** (sonraki aşama)
    - [ ] EmergencyViewModel bağlantısı + "SMS Gönderildi" / hata durumu UI
    - [ ] Otomatik 10s geri sayım sonrası SMS + 112 arama

### 3.7 — Doktor Raporlama & CSV Export
- [ ] **EKG Oturum Kaydı**
    - [ ] `EcgForegroundService` kayıt modunda `List<EcgSample>` → `ecg_[timestamp].bin` dosyaya yaz
    - [ ] Kayıt başlat/durdur: `ProModeScreen`'deki kayıt butonu → `EcgForegroundService`
- [ ] **CSV Export**
    - [ ] `timestamp_ms, channel, rawAdc, voltageUv, bpm, alert_level` sütunları
    - [ ] `ContentValues` + `MediaStore` ile Downloads klasörüne yaz (Android 10+ scoped storage)
    - [ ] `Intent.ACTION_SEND` ile paylaşım menüsü
- [ ] **PDF Rapor (iTextPDF veya PdfDocument API)**
    - [ ] EKG grafiği: Canvas çizim → Bitmap → PDF sayfası (25 mm/s, 1 mV/cm standart)
    - [ ] Başlık bölümü: Hasta adı, kan grubu, tarih/saat, kayıt süresi
    - [ ] Metrikler bölümü: Ort/Min/Max BPM, SDNN, RMSSD, sinyal kalitesi skoru
    - [ ] AI bölümü: DCA-CNN tahmin etiketi, güven skoru, R-R irregülarite skoru
    - [ ] Uyarı geçmişi: PDF içine tablo formatında acil durum geçmişi
- [ ] **E-posta Gönderme**
    - [ ] `Intent.ACTION_SEND` + `ClipData` ile PDF ek → doktor e-posta adresine

---

## 💾 FAZ 4: Veri Saklama & Senkronizasyon
**Amaç:** Kullanıcı ve EKG verilerini güvenli şekilde saklamak; KVKK uyumlu.

### 4.1 — Room Veritabanı
- [ ] **Tablo Yapısı**
    - [ ] `User` — id, ad, soyad, tel, kanGrubu, acilDurumKisisi, doktorEmail, profilFoto
    - [ ] `EcgSession` — id, userId, baslangicZamani, sure, ortBpm, minBpm, maxBpm, dosyaYolu, kaliteSkor
    - [ ] `EcgAlert` — id, sessionId, tarih, tur (TAŞIKARDI/BRADİKARDİ/ARİTMİ/ST_ANOMALI), seviye, detaylar, modelGuvenSkoru
    - [ ] `DeviceInfo` — id, mac, ad, sonBaglanma, firmwareVersiyon
- [ ] **DAO (Data Access Object)**
    - [ ] `UserDao` — CRUD + giriş doğrulaması
    - [ ] `EcgSessionDao` — kayıt ekleme, tarih bazlı sorgulama, istatistik
    - [ ] `EcgAlertDao` — uyarı ekleme, filtreleme, okunmamış sayısı
- [ ] **Room Database + Migration**
    - [ ] `HayatinRitmiDatabase` — TypeConverters, version yönetimi

### 4.2 — Kullanıcı Kayıt/Giriş
- [ ] **Kayıt Akışı**
    - [ ] SignUpScreen verilerinin Room'a yazılması
    - [ ] Şifre hash'leme (bcrypt veya Argon2)
    - [ ] Profil verilerini DataStore'da cache'leme
- [ ] **Giriş Doğrulaması**
    - [ ] Room'dan kullanıcı sorgulama
    - [ ] Biyometrik giriş (BiometricPrompt API)
    - [ ] Oturum yönetimi (DataStore token)

### 4.3 — Veri Güvenliği & KVKK
- [ ] **Şifreli Depolama**
    - [ ] EKG verileri AES-256 ile şifrelenmiş dosya sistemi
    - [ ] Room veritabanı SQLCipher ile şifreleme
    - [ ] Kullanıcı onaylı veri silme akışı
- [ ] **Anonimleştirme**
    - [ ] Araştırma verilerinde hasta kimliği kaldırma
    - [ ] Sadece gerekli metaveri paylaşımı
- [ ] **Senkronizasyon (Opsiyonel)**
    - [ ] WorkManager ile çevrimdışı veri kuyruğu
    - [ ] İnternet gelince buluta şifreli yükleme

---

## 🔬 FAZ 5: Doğrulama, Test & Yaygınlaştırma
**Amaç:** Sistemi sahada sınamak, performans kriterlerini ölçmek ve yaygın etkiyi gerçekleştirmek.

### 5.1 — Performans Hedefleri (Araştırma Önerisinden)
- [ ] **Doğruluk:** ≥%95 doğruluk eşiği (60 saatlik pilot deneme)
- [ ] **Gecikme:** Şüpheli durumda uyarı ≤1 saniye
- [ ] **Yanlış Alarm:** Gereksiz alarm oranı ≤%5
- [ ] **Kullanıcı Deneyimi:** SUS (System Usability Scale) puanı ≥75
- [ ] **Kararlılık:** Crash-free oranı ≥%98
- [ ] **TFLite Performans:** tek kanal <22ms, üç kanal <38ms, bellek <2.1MB

### 5.2 — Test Stratejisi
- [ ] **Birim Testleri**
    - [ ] `EcgPacketParser` — deterministic test vektörleri ile
    - [ ] `EcgFilter` — bilinen frekans girdileri, filtre cevabı doğrulama
    - [ ] `RPeakDetector` — sentetik PQRST ile BPM doğruluk testi
    - [ ] `RingBuffer` — çoklu iş parçacığı güvenlik testi
- [ ] **Entegrasyon Testleri**
    - [ ] Mock → Repository → ViewModel → UI pipeline end-to-end
    - [ ] BLE bağlantı/bağlantı kesme döngüsü stres testi
- [ ] **Saha Pilot Denemeleri**
    - [ ] En az 60 saatlik EKG kaydı
    - [ ] Farklı aktivite senaryoları (istirahat, yürüyüş, merdiven, koşu)
    - [ ] Elektrot kalitesi ve hareket artefaktı değerlendirmesi

### 5.3 — Yaygın Etki & Çıktılar
- [ ] **Bilimsel Çıktılar**
    - [ ] En az 1 ulusal/uluslararası kongre bildirisi
    - [ ] Teknik rapor + kullanım kılavuzu
    - [ ] Açık kaynak kod ve model bileşenleri (MIT/Apache lisansı)
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
- **Son Build:** ✅ BUILD SUCCESSFUL 33s — Gradle 8.13, Kotlin 2.0.21, AGP 8.7.3 (24 Şub 2026)
- **Kalan Uyarılar:** `BluetoothSearching` deprecated (DeviceScanScreen.kt:111,130) — işlevselliği etkilemez
- **FAZ 3 Durumu:** Domain model, AdvancedEcgProcessor, AlertEngine, ArrhythmiaClassifier, EmergencyViewModel tamamlandı. DS-1D-CNN eğitimi tamamlandı (Macro AUC=0.9517, TFLite INT8=231.6 KB). UI entegrasyonu (DashboardScreen alert renkleri, ProModeScreen AI kartı) ve GPS entegrasyonu sonraki aşamada.
- **AI Model Dokümantasyonu:** `docs/model/MODEL_DOCUMENTATION.md` — Mermaid diyagramları ile mimari, eğitim, test, export detayları
- **Hedef SDK:** 35 (Android 15)
- **AGP:** 8.7.3, **Kotlin:** 2.0.21, **Gradle:** 8.9, **Compose BOM:** 2024.11.00
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
