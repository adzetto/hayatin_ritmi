# 🚀 TÜBİTAK 2209-A Proje İlerleme ve Görev Takibi

Bu dosya, projenin geliştirme sürecini adım adım takip etmek için oluşturulmuştur.

**Proje Başlığı:** Çok Kanallı Adaptif Yapay Zekâ Tabanlı Taşınabilir EKG Analiz Sistemi
**Başvuru Sahibi:** İsmail Sakci | **Danışman:** Mehmet Zübeyir Ünlü
**Kurum:** İzmir Yüksek Teknoloji Enstitüsü

## 📅 Genel Durum
- **Başlangıç Tarihi:** 19 Şubat 2026
- **Mevcut Faz:** FAZ 3 (Acil Durum & Yapay Zeka Entegrasyonu)
- **Hedef:** ADS1293 + STM32 + nRF52832 tabanlı EKG tişörtüyle BLE bağlantısı kurmak, canlı veri almak, DCA-CNN ile analiz etmek ve acil durum uyarısı göndermek.
- **Mimari:** Repository Pattern (Mock/Real BLE abstraction) + ViewModel + Manual DI

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
- [x] **Ham EKG Verisi (ADS1293)**
    - [x] 10-byte paket: `[Header:0xAA][Kanal:1B][Timestamp:4B LE uint32][EKG:3B BE int24][Checksum:XOR]`
    - [x] `EcgPacketParser.kt` — Header doğrulama, checksum XOR, 24-bit sign extension
    - [x] Örnekleme hızı: 250 Hz (`BleConstants.SAMPLE_RATE_HZ`)
- [x] **Voltaj Dönüşümü**
    - [x] `EcgSample.fromRawAdc()` — `voltageUv = (rawAdc * 2.4V) / (2^23 * 6) * 1_000_000`
- [x] **Veri Modelleri (Kotlin)**
    - [x] `EcgSample.kt` — timestamp, channel, rawAdc, voltageUv + `fromRawAdc()` companion
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
    - [x] Gerçekçi PQRST dalga formu şablonu (250 nokta/döngü)
    - [x] ~72 BPM temel hız + sinüzoidal HRV
    - [x] Baseline wander (0.3 Hz), 50 Hz hat gürültüsü, rastgele kas artefaktı
    - [x] 10-byte BLE paketi üretimi (header + channel + timestamp + ADC + XOR checksum)

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

## 🔄 FAZ 3: Sinyal Kalitesi, Yapay Zeka & Acil Durum
**Amaç:** Araştırma önerisindeki ileri sinyal işleme, DCA-CNN yapay zeka modeli ve acil durum sistemini implement etmek.
**Kaynak:** 2209-A Araştırma Önerisi Formu — Bölüm 3 (DSP), Bölüm 4 (DCA-CNN), Bölüm 5 (Mobil Uygulama)

### 3.1 — İleri Sinyal İşleme (Araştırma Önerisinden)
- [ ] **Bazal Düzeltme (Moving Average L=256)**
    - [ ] Kayan ortalama ile DC ofset ve bazal sürüklenme kaldırma
    - [ ] O(1) kümülatif toplam farkı ile gerçek zamanlı güncelleme
- [ ] **6. Derece Butterworth Bant Geçiren (0.5–40 Hz)**
    - [ ] Bilinear dönüşüm ile SOS (Second-Order Section) tasarımı
    - [ ] Mevcut EcgFilter'ı SOS tabanlı 6. derece Butterworth'a yükseltme
- [ ] **Dalgacık Tabanlı Gürültü Azaltma (Daubechies-4)**
    - [ ] 4-6 seviye çok çözünürlüklü ayrıştırma
    - [ ] Donoho evrensel eşiği: `τ = σ * sqrt(2 * ln(N))`, σ = MAD/0.6745
    - [ ] Yumuşak eşikleme (soft thresholding) — P ve T dalgaları korunur
    - [ ] IDWT ile gürültüsü azaltılmış sinyal elde etme
- [ ] **Sinyal Kalite Kontrolü (SNR & PRD)**
    - [ ] Her 10 saniyelik segment için SNR hesaplama
    - [ ] Eşik altı segmentleri (<12 dB) eleme veya yeniden işleme
    - [ ] PRD (Percent Root Mean Square Difference) raporlama
    - [ ] Kalite skoru UI'a yansıtma (sinyal kalitesi göstergesi)

### 3.2 — Gürültü Modellemesi & Simülasyon
- [ ] **Kontrollü Gürültü Enjeksiyonu**
    - [ ] Kas gürültüsü (20-200 Hz geniş bant): `s_kas[n]`
    - [ ] Elektrot artefaktı (düşük frekans + ani sıçramalar): `s_elektrot[n]`
    - [ ] Hedef SNR (6-18 dB) için α katsayısı kapalı formda ayarlama
- [ ] **Çok Kanallı Korelasyon Matrisi** (Gelecek: 3 kanal desteği)
    - [ ] Kanal kovaryans matrisi `R_xx` kestirimi
    - [ ] PCA ile ortak-mod gürültü bastırma
    - [ ] Tutarlılık denetimi: İskemi vs. artefakt ayrımı

### 3.3 — DCA-CNN Yapay Zeka Modeli
- [ ] **Model Mimarisi (Dynamic Channel-Aware CNN)**
    - [ ] Adaptive Channel Convolution (ACC) katmanı: `W_c = W_base + ΔW_c`
    - [ ] Öğrenilebilir gate katsayıları: `g_c = σ(α_c)` — kullanılmayan kanallar otomatik sıfırlanır
    - [ ] Squeeze-and-Excitation kanal dikkat mekanizması (reduction ratio r=4)
    - [ ] Faz regülarizasyonu: Konvolüsyon çekirdeğinin frekans cevabı kontrolü (λ_φ=0.01)
- [ ] **Eğitim Stratejisi**
    - [ ] Veri kümeleri: MIT-BIH Arrhythmia + PTB-XL + saha verileri
    - [ ] Hasta bağımsız 70-15-15 bölme (eğitim/doğrulama/test)
    - [ ] Veri artırma: Gaussian gürültü, bazal sürüklenme, kanal dropout, zaman ölçekleme
    - [ ] 10 saniyelik kayar pencereler, 5 saniye örtüşmeli
    - [ ] AdamW optimizer, lr=1e-3, cosine annealing (her 5 epoch)
    - [ ] Kayıp: `L = L_CE + λ_g * L_gate + λ_φ * L_phase`
    - [ ] Erken durdurma: 5 epoch gelişme yoksa
- [ ] **Model Dönüşümü & Gömme**
    - [ ] PyTorch → ONNX → TensorFlow Lite dönüşümü
    - [ ] QAT (Quantization-Aware Training) ile INT8 nicemleme (PTQ yerine, medikal hassasiyet için)
    - [ ] Hedef: <2.1 MB model boyutu, <38ms çıkarım (3 kanal), <22ms (tek kanal)
    - [ ] TFLite Interpreter ile Android'de gömülü çıkarım
    - [ ] Model `assets/` klasöründe, `ByteBuffer` tensor girişi

### 3.4 — Acil Durum Algoritması & Uyarı Sistemi
- [ ] **Aritmi Tespiti**
    - [ ] Anormal R-R interval paterni tespiti (irregüler aralıklar)
    - [ ] Taşikardi uyarısı (BPM > 120, sürekli 30 saniye)
    - [ ] Bradikardi uyarısı (BPM < 50, sürekli 30 saniye)
    - [ ] DCA-CNN model çıkışı ile doğrulama
- [ ] **ST Segment Analizi**
    - [ ] ST segment elevasyonu/çökmesi tespiti (miyokard enfarktüsü şüphesi)
    - [ ] Referans izoelektrik hattan sapma ölçümü (≥0.1 mV threshold)
    - [ ] "Emin değilim → tekrar ölçüm" kuralı (gereksiz alarm oranı ≤%5)
- [ ] **Lead-Off Detection**
    - [ ] Elektrot teması kaybı tespiti (empedans izleme)
    - [ ] "Elektrot teması kesildi" uyarısı
    - [ ] Kullanıcıya yeniden konumlandırma yönergesi
- [ ] **Renk Kodlu Uyarı UI**
    - [ ] Yeşil (u < δ₁): Normal — "Güvendesiniz"
    - [ ] Sarı (δ₁ ≤ u < δ₂): Dikkat — "Dikkat, kontrol önerilir"
    - [ ] Kırmızı (u ≥ δ₂): Kritik — Acil durum paneli otomatik açılır
    - [ ] Renk geçişleri: `τ_c * dy_c/dt + y_c = c_c(u)` (yumuşak animasyon)

### 3.5 — Yakını Arama / SMS & Konum
- [ ] **SMS Gönderme**
    - [ ] `SEND_SMS` izni ve `SmsManager.sendTextMessage()`
    - [ ] GPS/Network konum alma (`ACCESS_FINE_LOCATION`)
    - [ ] SMS içeriği: "ACIL DURUM — [Kullanıcı Adı] kalp ritmi anomalisi tespit edildi. Konum: [lat, lon]"
- [ ] **Otomatik Arama**
    - [ ] 112 acil çağrı intent'i (kullanıcı onayı ile)
    - [ ] Kayıtlı yakın kişilere sıralı arama
- [ ] **Konum Tabanlı Topluluk Uyarısı** (Faydalı Model/Patent hedefi)
    - [ ] Mesafeye göre uyarı gönderme sistemi konsepti

### 3.6 — Doktor Raporlama
- [ ] **EKG Kayıt Geçmişi**
    - [ ] Geçmiş EKG oturumlarının listelenmesi (tarih/saat/süre/ort BPM)
    - [ ] CSV veri dışa aktarma
- [ ] **PDF Rapor Oluşturma**
    - [ ] EKG grafiği (25 mm/s standart format) + metrikler
    - [ ] Hasta bilgileri, kan grubu, acil kişi
    - [ ] DCA-CNN analiz sonuçları ve güven skoru
- [ ] **E-posta ile Gönderme**
    - [ ] Kayıtlı doktor e-posta adresine PDF ek olarak gönderme

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
