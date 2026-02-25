# Kapsamlı Uygulama Planı & Eksik Analizi

> **Tarih:** Haziran 2026  
> **Referans:** TÜBİTAK 2209-A Araştırma Önerisi  
> **Mevcut Durum:** FAZ 1-2 tamamlandı, FAZ 3 büyük oranda tamamlandı  
> **Git:** `https://github.com/adzetto/hayatin_ritmi.git` — `main` branch

---

## 1. GENEL DURUM ÖZETİ

| Bileşen | Araştırma Önerisindeki Hedef | Mevcut Durum | Tamamlanma |
|---|---|---|---|
| UI & Navigasyon (FAZ 1) | Tüm ekranlar, responsive tasarım | ✅ 9 ekran, Dark/Light tema | %100 |
| BLE & Cihaz Bağlantısı (FAZ 2) | GATT, 12-lead, foreground service | ✅ Mock + Real BLE, 43-byte parser | %100 |
| İleri DSP (FAZ 3.1) | Bazal düzeltme, Butterworth, wavelet | ✅ AdvancedEcgProcessor.kt | %100 |
| Gürültü Simülasyonu (FAZ 3.2) | Kas/elektrot artefakt, SNR kontrol | ❌ Henüz başlanmadı | %0 |
| AI Model Eğitimi (FAZ 3.3) | DCA-CNN / DS-1D-CNN | ✅ DS-1D-CNN, AUC=0.9517, TFLite INT8 | %90 |
| Android TFLite Inference (FAZ 3.4) | Gömülü AI, <22ms | ✅ ArrhythmiaClassifier.kt, 0.84ms | %100 |
| Alert Engine (FAZ 3.5) | Kural + AI hibrit karar | ✅ AlertEngine.kt | %100 |
| Acil Durum Sistemi (FAZ 3.6) | SMS + 112 + GPS | ✅ EmergencyViewModel.kt | %100 |
| Doktor Raporlama (FAZ 3.7) | CSV, PDF, e-posta | ❌ Henüz başlanmadı | %0 |
| Room DB & Kullanıcı (FAZ 4) | Room, SQLCipher, KVKK | ❌ Henüz başlanmadı | %0 |
| Test & Doğrulama (FAZ 5) | Unit test, pilot, SUS≥75 | ❌ Henüz başlanmadı | %0 |
| DCA-CNN Mimari (Öneri §4) | Dinamik kanal adaptif CNN | ❌ DS-1D-CNN kullanıldı, DCA-CNN yok | %0 |
| QAT (Öneri §4.1) | Quantization-Aware Training | ❌ Sadece PTQ yapıldı | %0 |
| Çok Kanallı Korelasyon (Öneri §3.6) | PCA, kovaryans matrisi | ❌ Henüz başlanmadı | %0 |
| Veri Artırma / Augmentation (Öneri §4) | Gaussian gürültü, kanal dropout, zaman ölçekleme | ❌ Eğitimde augmentation yok | %0 |
| Sync Word Paket Hizalama (Öneri §5) | Kayan korelasyon ile çerçeve hizalama | ❌ Parser'da basit header kontrolü var | %50 |
| Tampon Doluluğu Yönetimi (Öneri §5) | ρ>0.8 → sensöre yavaşla komutu | ❌ Basit ring buffer var, backpressure yok | %30 |
| Enerji Farkındalığı (Öneri §5) | Pil eğrisi izleme, adaptif veri hızı | ❌ Henüz başlanmadı | %0 |
| WCAG Erişilebilirlik (Öneri §5d) | Yüksek kontrast, dinamik font | ❌ Temel tema var, WCAG uyumu yok | %20 |
| Hilt/Koin DI (Öneri §5c) | Dependency injection framework | ❌ Manuel DI (MainActivity'de) | %30 |
| Kapalı Beta & SUS (Öneri takvim) | SUS≥75, crash-free≥%98 | ❌ Henüz başlanmadı | %0 |
| KVKK & Etik (Öneri risk tablosu) | Anonimleştirme, şifreli depolama | ❌ Henüz başlanmadı | %0 |

---

## 2. EKSİK KISIMLARIN DETAYLI İMPLEMENTASYON PLANI

### 2.1 — DCA-CNN Mimarisi (Araştırma Önerisi §4) 🔴 KRİTİK

**Mevcut Durum:** DS-1D-CNN (Depthwise Separable 1D CNN) eğitildi. Araştırma önerisinde "Dynamic Channel-Aware CNN" (DCA-CNN) mimarisi tanımlanmış — dinamik kanal sayısı (1/3/12), channel attention, gate mekanizması, faz regülarizasyonu.

**Eksikler:**
1. **Dinamik Kanal Gate Mekanizması:** Öneride her kanal için öğrenilebilir gate gc = σ(αc) tanımlanmış (Denklem 14-15). DS-1D-CNN'de bu yok — sabit 12 kanal.
2. **Channel Attention (Squeeze-Excitation):** Öneride SE blokları ile kanal ağırlıklandırma tanımlanmış (Denklem 18-20). DS-1D-CNN'de attention mekanizması yok.
3. **Faz Regülarizasyonu:** Öneride konvolüsyon çekirdeklerinin Fourier dönüşümü ile ideal Butterworth filtre cevabına yakınlaştırma (Denklem 21-22, λ_φ=0.01). Uygulanmadı.
4. **Base Weight + Channel Offset:** Wc = Wbase + ΔWc ayrıştırması (Denklem 13). Uygulanmadı.
5. **Gate Regularization Loss:** Lggate = λg Σ gc² (Denklem 17). Uygulanmadı.

**Uygulama Planı:**
- [ ] PyTorch'ta `DCA_CNN` modül sınıfı oluştur (`ChannelGate`, `SEBlock`, `AdaptiveChannelConv`)
- [ ] Faz regülarizasyonu loss terimi: `phase_regularization_loss()` fonksiyonu — FFT + L2 norm
- [ ] Toplam kayıp: `L_total = L_BCE + λ_gate * L_gate + λ_phase * L_phase`
- [ ] Eğitim: AdamW optimizer, cosine annealing (her 5 epoch), early stopping (5 epoch patience)
- [ ] 1-kanal, 3-kanal, 12-kanal konfigürasyonlarında eğitim ve test
- [ ] Karşılaştırma raporu: DS-1D-CNN vs DCA-CNN (AUC, F1, inference time, model size)

**Dosyalar:**
- `dataset/models/dca_cnn.py` — Model tanımı
- `dataset/train_dca_cnn.py` — Eğitim scripti
- `dataset/evaluate_dca_cnn.py` — Değerlendirme scripti

---

### 2.2 — Quantization-Aware Training (QAT) (Araştırma Önerisi §4.1) 🔴 KRİTİK

**Mevcut Durum:** Sadece PTQ (Post-Training Quantization) yapıldı — 200 kalibrasyon örneği. Macro AUC kaybı -0.018.

**Araştırma Önerisi:** "Yüksek doğruluğun çok önemli olduğu medikal EKG analizi gibi güvenlik-kritik uygulamalarda, QAT ek hesaplama maliyetine rağmen bir zorunluluk olarak değerlendirilmelidir."

**Uygulama Planı:**
- [ ] PyTorch `torch.quantization.prepare_qat()` ile QAT modeli oluştur
- [ ] Fine-tuning: 10-20 epoch, düşük lr (1e-4), fake quantize katmanları ile
- [ ] QAT INT8 model export: PyTorch → ONNX → TFLite INT8
- [ ] Karşılaştırma: PTQ vs QAT INT8 (AUC, F1, inference time)
- [ ] QAT modeli Android'e gömülecek (ecg_model_qat_int8.tflite)

**Hedef:** PTQ'daki -0.018 Macro AUC kaybını ≤-0.005'e düşürmek

---

### 2.3 — Veri Artırma / Data Augmentation (Araştırma Önerisi §4) 🟡 ORTA

**Mevcut Durum:** Eğitimde augmentation kullanılmadı — sadece per-lead z-score normalizasyon.

**Araştırma Önerisi:** "Gaussian gürültü enjeksiyonu, bazal sürüklenme sentetik olarak ekleme, kanal dropout ve zaman ölçekleme teknikleri uygulanmaktadır."

**Uygulama Planı:**
- [ ] `dataset/augmentation.py` — Augmentation fonksiyonları
  - [ ] Gaussian gürültü enjeksiyonu (SNR 6-25 dB arası)
  - [ ] Sentetik bazal sürüklenme (0.1-0.5 Hz sinüzoidal)
  - [ ] Kanal dropout (p=0.1, rastgele 1-2 kanal sıfırla)
  - [ ] Zaman ölçekleme (0.9x - 1.1x resampling)
  - [ ] Amplitüd ölçekleme (0.8x - 1.2x)
- [ ] Eğitim scriptine online augmentation entegrasyonu
- [ ] Augmentation ile yeniden eğitim ve AUC karşılaştırması

---

### 2.4 — Çok Kanallı Korelasyon Matrisi & PCA (Araştırma Önerisi §3.6) 🟡 ORTA

**Mevcut Durum:** Uygulama sadece per-lead bağımsız işleme yapıyor. Kanal arası korelasyon analizi yok.

**Araştırma Önerisi:** Kovaryans matrisi Rxx hesaplama, özayrışım ile PCA, tutarlılık denetimi (iskemik patern vs artefakt ayrımı), morfolojik alt-uzay projeksiyonu.

**Uygulama Planı:**
- [ ] `AdvancedEcgProcessor.kt`'ye `computeCovarianceMatrix()` metodu ekle
- [ ] `eigenDecomposition()` — 12x12 kovaryans matrisinin özdeğer/özvektör ayrıştırması
- [ ] `consistencyCheck()` — Tekil kanal artefakt tespiti (özdeğer dağılımı analizi)
- [ ] `projectToSubspace()` — Enerji baskın alt-uzay seçimi ile gürültü bastırma
- [ ] `SignalQuality` veri sınıfına `channelConsistencyScore` alanı ekle

---

### 2.5 — Gürültü Modellemesi & Simülasyon (FAZ 3.2) 🟡 ORTA

**Mevcut Durum:** MockBleManager'da temel gürültü (baseline wander 0.3Hz, 50Hz hat, rastgele kas artefaktı) var ama araştırma önerisindeki detaylı gürültü modeli uygulanmadı.

**Araştırma Önerisi §3.4:** Kontrollü gürültü: z[n] = x̂[n] + α_kas·s_kas[n] + α_elektrot·s_elektrot[n], kapalı formda SNR hedefleme.

**Uygulama Planı:**
- [ ] `MockBleManager.kt`'ye parametrik gürültü modülleri ekle:
  - [ ] Kas gürültüsü (20-200 Hz geniş bant EMG modeli)
  - [ ] Elektrot artefaktı (ani impedans değişimi, düşük frekans salınım)
  - [ ] SNR kontrol: `α = √(P_x / (P_s × 10^(-SNR/10)))` ile hedef SNR (6-18 dB)
- [ ] Segment bazında farklı gürültü tohumları ile çeşitlendirme
- [ ] Test: AI modelinin farklı SNR seviyelerindeki performansını ölç

---

### 2.6 — Doktor Raporlama & CSV/PDF Export (FAZ 3.7) 🔴 KRİTİK

**Mevcut Durum:** Hiçbir raporlama özelliği yok.

**Araştırma Önerisi §5:** "Çalışma sonunda çalışır prototip, kullanım kılavuzu, teknik rapor ve yeniden kullanılabilir kod/modül seti teslim etmek."

**Uygulama Planı:**

#### 2.6.1 — EKG Oturum Kaydı
- [ ] `EcgForegroundService`'e kayıt modu ekle — `List<EcgSample>` → binary dosyaya yaz
- [ ] `ProModeScreen`'de kayıt butonu (başlat/durdur) + süre göstergesi
- [ ] Dosya formatı: `ecg_[timestamp].bin` — header (sample rate, channels, user info) + raw data

#### 2.6.2 — CSV Export
- [ ] `CsvExporter.kt` — `timestamp_ms, channel, rawAdc, voltageUv, bpm, alert_level` sütunları
- [ ] `ContentValues` + `MediaStore` ile Downloads klasörüne kaydet (scoped storage)
- [ ] `Intent.ACTION_SEND` ile paylaşım menüsü

#### 2.6.3 — PDF Rapor
- [ ] Android `PdfDocument` API veya iTextPDF kütüphanesi
- [ ] Sayfa yapısı:
  - Başlık: Hasta adı, kan grubu, tarih/saat, kayıt süresi
  - EKG Grafiği: Canvas → Bitmap → PDF (25 mm/s, 1 mV/cm standart)
  - Metrikler: Ort/Min/Max BPM, SDNN, RMSSD, sinyal kalitesi
  - AI Analizi: DS-1D-CNN tahmin, güven skoru, R-R irregülarite
  - Uyarı Geçmişi: Tablo formatında
- [ ] PDF sayfasını `FileProvider` ile paylaş

#### 2.6.4 — E-posta Gönderimi
- [ ] `Intent.ACTION_SEND` + `ClipData` ile PDF ek → doktor e-posta adresine
- [ ] Doktor e-posta adresi: Settings ekranından kayıt

---

### 2.7 — Room Veritabanı & Kullanıcı Yönetimi (FAZ 4) 🔴 KRİTİK

**Mevcut Durum:** Veri saklama yok — DataStore sadece cihaz MAC için kullanılıyor.

**Uygulama Planı:**

#### 2.7.1 — Room Database Schema
- [ ] `User` entity — id, ad, soyad, tel, kanGrubu, acilDurumKisisi, doktorEmail, profilFoto
- [ ] `EcgSession` entity — id, userId, başlangıçZamanı, süre, ortBpm, minBpm, maxBpm, dosyaYolu, kaliteSkoru
- [ ] `EcgAlert` entity — id, sessionId, tarih, tür, seviye, detaylar, modelGüvenSkoru
- [ ] `DeviceInfo` entity — id, mac, ad, sonBağlanma, firmwareVersiyon

#### 2.7.2 — DAO'lar
- [ ] `UserDao` — CRUD + giriş doğrulaması sorguları
- [ ] `EcgSessionDao` — kayıt ekleme, tarih bazlı sorgulama, istatistik (son 7/30 gün)
- [ ] `EcgAlertDao` — uyarı ekleme, filtreleme, okunmamış sayısı badge

#### 2.7.3 — Migration & Database Instance
- [ ] `HayatinRitmiDatabase` — Room.databaseBuilder, TypeConverters
- [ ] Version 1 migration stratejisi

#### 2.7.4 — Kullanıcı Kayıt/Giriş
- [ ] `SignUpScreen` → Room'a kullanıcı yazma
- [ ] Şifre hashleme: Argon2 veya bcrypt
- [ ] `LoginScreen` → Room sorgusu ile doğrulama
- [ ] Biyometrik giriş: `BiometricPrompt` API entegrasyonu
- [ ] Oturum yönetimi: DataStore'da session token

#### 2.7.5 — SQLCipher Şifreleme
- [ ] `net.zetetic:android-database-sqlcipher` bağımlılığı
- [ ] `SupportFactory` ile Room database şifreleme
- [ ] Kullanıcı anahtarı: Android Keystore'dan türetilmiş AES-256

---

### 2.8 — KVKK & Veri Güvenliği (FAZ 4.3) 🔴 KRİTİK

**Mevcut Durum:** Herhangi bir veri güvenliği önlemi yok.

**Uygulama Planı:**
- [ ] EKG dosyaları AES-256-GCM ile şifreleme (Android Keystore'dan anahtar)
- [ ] Room veritabanı SQLCipher ile şifreleme
- [ ] Kullanıcı onaylı veri silme akışı — Settings → "Verilerimi Sil" butonu
- [ ] Araştırma verilerinde hasta kimliği kaldırma (anonimleştirme)
- [ ] KVKK aydınlatma metni: Uygulama içi gösterge
- [ ] Sadece gerekli metadata paylaşımı (e-posta/rapor gönderirken)

---

### 2.9 — Dependency Injection (Hilt) (Araştırma Önerisi §5c) 🟡 ORTA

**Mevcut Durum:** Manuel DI — `MainActivity`'de mock nesneler oluşturulup ViewModel'lere veriliyor.

**Araştırma Önerisi:** "Bağımlılıklar Hilt/Koin benzeri enjeksiyon araçlarıyla yönetildiği için test senaryoları kolayca kurgulanır."

**Uygulama Planı:**
- [ ] Hilt bağımlılıkları build.gradle'a ekle (`hilt-android`, `hilt-compiler`, `hilt-navigation-compose`)
- [ ] `@HiltAndroidApp` → Application sınıfı
- [ ] `@AndroidEntryPoint` → MainActivity
- [ ] `@HiltViewModel` → EcgViewModel, DeviceScanViewModel, EmergencyViewModel
- [ ] `@Module` → `BleModule` (BleManager, EcgRepository sağlayıcıları)
- [ ] `@Module` → `DatabaseModule` (Room, DAO sağlayıcıları)
- [ ] `@Module` → `AiModule` (ArrhythmiaClassifier, AdvancedEcgProcessor)
- [ ] Mock/Real geçişi: `@Named` qualifier veya BuildConfig flag

---

### 2.10 — Tampon Yönetimi & Backpressure (Araştırma Önerisi §5) 🟢 DÜŞÜK

**Mevcut Durum:** Basit RingBuffer var, backpressure mekanizması yok.

**Uygulama Planı:**
- [ ] Ring buffer doluluk oranını izle: `ρ = B_k / B_max`
- [ ] `ρ > 0.8` → BLE connection interval artır (sensöre yavaşla)
- [ ] `ρ < 0.3` → Normal hıza dön
- [ ] StateFlow ile doluluk oranını UI'a bildir

---

### 2.11 — Enerji Farkındalığı & Pil Yönetimi (Araştırma Önerisi §5b) 🟢 DÜŞÜK

**Mevcut Durum:** Herhangi bir pil yönetimi yok.

**Uygulama Planı:**
- [ ] `BatteryManager` ile telefon pil seviyesi izleme
- [ ] Düşük pil modunda: UI refresh rate düşür, wavelet işleme devre dışı bırak
- [ ] `dE/dt = -(I_BLE + I_CPU) × V_bat` eğrisini izle
- [ ] `-η` eşiği altında → "Veri toplama yavaşlatıldı" bildirimi

---

### 2.12 — WCAG Erişilebilirlik (Araştırma Önerisi §5d) 🟢 DÜŞÜK

**Mevcut Durum:** Temel dark/light tema var, WCAG uyumu yok.

**Uygulama Planı:**
- [ ] Yüksek kontrast modu (Settings toggle)
- [ ] Dinamik font boyutu (sistem ayarlarına uyum)
- [ ] Dokunmatik hedef minimum 48dp
- [ ] Content descriptions tüm ikonlar için
- [ ] Animasyonları devre dışı bırakma seçeneği (Settings)
- [ ] TalkBack uyumluluğu testi

---

### 2.13 — Sync Word & Gelişmiş Paket Hizalama (Araştırma Önerisi §5) 🟢 DÜŞÜK

**Mevcut Durum:** `EcgPacketParser`'da basit 0xAA header kontrolü. Kayan korelasyon yok.

**Uygulama Planı:**
- [ ] Kayan korelasyon ile sync word arama: `n* = argmax_n Σ s_m · r_{n+m}`
- [ ] Eşik altı → byte kayması → paket eleme + StateFlow ile kullanıcıya bilgi
- [ ] Zaman senkronizasyonu: Her 60s mobil → MCU zaman damgası gönderimi
- [ ] Saat kayması (clock drift) düzeltmesi

---

### 2.14 — Unit Test & Entegrasyon Testleri (FAZ 5.2) 🔴 KRİTİK

**Mevcut Durum:** Hiçbir test yok.

**Uygulama Planı:**

#### Unit Testler
- [ ] `EcgPacketParserTest` — 43-byte çerçeve parse, checksum doğrulama, bozuk paket
- [ ] `EcgFilterTest` — Bilinen frekans girdi, filtre cevabı doğrulama (0.5Hz HPF, 50Hz notch, 40Hz LPF)
- [ ] `RPeakDetectorTest` — Sentetik PQRST ile BPM doğruluk (±2 BPM tolerans)
- [ ] `RingBufferTest` — Thread-safety, overflow, underflow
- [ ] `AdvancedEcgProcessorTest` — Bazal düzeltme, Butterworth SOS, wavelet denoise
- [ ] `AlertEngineTest` — Tüm AlertLevel senaryoları (taşikardi, bradikardi, AF, ST)
- [ ] `ArrhythmiaClassifierTest` — Mock TFLite ile inference pipeline

#### Entegrasyon Testleri
- [ ] Mock → Repository → ViewModel → UI pipeline end-to-end
- [ ] BLE bağlantı/kesme döngüsü stres testi
- [ ] Room DB CRUD döngüsü + migration testi

#### UI Testleri (Compose)
- [ ] `DashboardScreenTest` — AlertLevel'e göre renk değişimi
- [ ] `EmergencyScreenTest` — Geri sayım + SMS tetikleme
- [ ] `ProModeScreenTest` — EKG grafik çizimi + metrik güncelleme

---

### 2.15 — Saha Pilot Denemeleri (FAZ 5.2) 🔴 KRİTİK

**Mevcut Durum:** Donanım henüz hazır değil — pilot denemeler yapılmadı.

**Araştırma Önerisi:** "En az 60 saatlik pilot deneme", "≥%95 doğruluk eşiği"

**Uygulama Planı:**
- [ ] ADS1293 donanım prototipi hazır olduğunda:
  - [ ] 10+ gönüllü ile en az 60 saat kayıt
  - [ ] Senaryo: İstirahat, yürüyüş, merdiven, koşu
  - [ ] Elektrot kalitesi ve hareket artefaktı değerlendirmesi
- [ ] Performans metrikleri:
  - [ ] Doğruluk ≥%95
  - [ ] Gecikme ≤1 saniye
  - [ ] Yanlış alarm ≤%5
  - [ ] Crash-free ≥%98
- [ ] SUS anketi: ≥75 puan hedefi

---

### 2.16 — Bilimsel Çıktılar (FAZ 5.3) 🟡 ORTA

**Uygulama Planı:**
- [ ] En az 1 ulusal/uluslararası kongre bildirisi hazırla
- [ ] Teknik rapor + kullanım kılavuzu
- [ ] GitHub repo'yu temizle ve README güncelle
- [ ] Açık kaynak: MIT/Apache lisansı ile paylaşım
- [ ] HuggingFace'de model + dataset paylaşımı (anonimleştirilmiş)

---

## 3. ÖNCELİK SIRASI VE BAĞIMLILIKLAR

```
Öncelik 1 (Acil — Proje Çekirdeği):
├── 2.7  Room DB & Kullanıcı Yönetimi
├── 2.6  Doktor Raporlama (CSV/PDF)
├── 2.8  KVKK & Veri Güvenliği
└── 2.14 Unit Test & Entegrasyon Testleri

Öncelik 2 (Yüksek — AI Kalitesi):
├── 2.1  DCA-CNN Mimarisi
├── 2.2  QAT (Quantization-Aware Training)
├── 2.3  Data Augmentation
└── 2.4  Çok Kanallı Korelasyon

Öncelik 3 (Orta — Kalite İyileştirme):
├── 2.5  Gürültü Simülasyonu
├── 2.9  Hilt DI
├── 2.16 Bilimsel Çıktılar
└── 2.12 WCAG Erişilebilirlik

Öncelik 4 (Düşük — İnce Ayar):
├── 2.10 Tampon Yönetimi & Backpressure
├── 2.11 Enerji Farkındalığı
├── 2.13 Sync Word Gelişmiş Hizalama
└── 2.15 Saha Pilot (donanıma bağımlı)
```

---

## 4. ARAŞTIRMA ÖNERİSİ TAKVİMİ İLE KARŞILAŞTIRMA

| Takvim | Önerideki Hedef | Mevcut Durum |
|---|---|---|
| 01.11.2025-30.11.2025 | Proje çerçevesi, WBS, risk analizi | ✅ Tamamlandı |
| 01.12.2025-28.02.2026 | Veri + donanım + temel AI + mobil çekirdek | ✅ %90 — AI model eğitildi, mobilden TFLite çalışıyor. Donanım WIP |
| 01.03.2026-30.04.2026 | Entegrasyon + optimizasyon | 🟡 %60 — TFLite Android'de çalışıyor, Room/PDF/test eksik |
| 01.05.2026-30.06.2026 | Kapalı beta + SUS + crash-free | ❌ %0 — Pilot denemeler başlamadı |
| 01.07.2026-31.07.2026 | Nihai rapor + etik/KVKK + DOI | ❌ %0 — KVKK çalışması başlamadı |

---

## 5. GITHUB ISSUE LİSTESİ

Aşağıdaki issue'lar GitHub'da açılacak:

1. **[AI] DCA-CNN Dinamik Kanal Adaptif Mimari Implementasyonu**
2. **[AI] Quantization-Aware Training (QAT) ile INT8 Model Optimizasyonu**
3. **[AI] Data Augmentation Pipeline (Gürültü, Kanal Dropout, Zaman Ölçekleme)**
4. **[DSP] Çok Kanallı Korelasyon Matrisi & PCA Tutarlılık Analizi**
5. **[DSP] Gelişmiş Gürültü Simülasyonu (MockBleManager - Parametrik SNR)**
6. **[Android] Doktor Raporlama - EKG Oturum Kaydı & CSV Export**
7. **[Android] Doktor Raporlama - PDF Rapor Oluşturma**
8. **[Android] Room Database & Kullanıcı Kayıt/Giriş Sistemi**
9. **[Android] KVKK Uyumluluğu & Veri Güvenliği (SQLCipher, AES-256)**
10. **[Android] Hilt Dependency Injection Entegrasyonu**
11. **[Android] Tampon Backpressure & Enerji Farkındalığı Yönetimi**
12. **[Android] WCAG Erişilebilirlik İyileştirmeleri**
13. **[Android] Gelişmiş Sync Word Paket Hizalama (Kayan Korelasyon)**
14. **[Test] Unit Test Suite (Parser, Filter, RPeak, RingBuffer, AlertEngine)**
15. **[Test] Entegrasyon & UI Compose Testleri**
16. **[Validation] Saha Pilot Denemeleri (60 saat, SUS≥75)**
17. **[Docs] Kongre Bildirisi & Teknik Rapor Hazırlığı**
