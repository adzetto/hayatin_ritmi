# Master Card Üzerinde Gömülü Yapay Zekâ Uygulanabilirliği ve Güç Tüketimi Araştırma Raporu

Tarih: 15 Mart 2026

## 1. Amaç ve Kapsam

Bu raporun amacı, proje deposunda yer alan mevcut yapay zekâ modelinin mobil telefondan alınarak proje ana kartı üzerinde gömülü biçimde çalıştırılmasının teknik olarak ne ölçüde uygulanabilir olduğunu incelemektir. İnceleme dört eksende yürütülmüştür:

| İnceleme ekseni | Açıklama |
|---|---|
| Model ayak izi | Model dosya boyutu, giriş boyutu, yaklaşık işlem yükü, ara bellek gereksinimi |
| Mevcut kart sınırları | STM32F103C8T6, nRF52832 ve ADS1293 bileşenlerinin bellek ve güç sınırları |
| Güç bütçesi | Analog ön uç, MCU, BLE ve olası AI yüklerinin ortalama ve anlık etkisi |
| Alternatif gömülü AI platformları | Daha yüksek bellekli MCU, NPU ve ultra düşük güçlü AI-MCU seçenekleri |

Bu raporda “master card” ifadesi, depoda tanımlanan ana kart / sensör kartı mimarisi olarak ele alınmıştır. Depoda bu isim açık bir donanım revizyon kodu olarak sabitlenmemiştir.

## 2. Depodan Doğrulanan Proje Bağlamı

### 2.1 Aktif model ve çalışma biçimi

Projede mobil tarafta aktif olarak kullanılan model `DCA-CNN INT8` modelidir. Aynı dosyada daha küçük bir `DS-1D-CNN INT8` yedek modeli de tutulmaktadır.

| Özellik | DCA-CNN INT8 | DS-1D-CNN INT8 |
|---|---:|---:|
| Dosya adı | `ecg_dca_cnn_int8.tflite` | `ecg_model_int8.tflite` |
| Yerel dosya boyutu | `319,768` bayt | `237,152` bayt |
| Yaklaşık boyut | `312.3 KiB` | `231.6 KiB` |
| Giriş biçimi | `[1, 2500, 12]` | `[1, 2500, 12]` |
| Pencere uzunluğu | `10 s` | `10 s` |
| Örnekleme | `250 Hz` | `250 Hz` |
| Kanal sayısı | `12` | `12` |
| Kullanım durumu | Birincil model | Yedek model |

### 2.2 Çıkarım döngüsü

| Parametre | Değer |
|---|---:|
| Kanal başına örnek sayısı | `2500` |
| Toplam örnek matrisi | `12 × 2500` |
| Çıkarım aralığı | Her `2500` örnekte bir |
| Zaman karşılığı | Yaklaşık her `10 s` |

### 2.3 Depoda görülen donanım tanımları

Depoda iki farklı donanım anlatımı birlikte yer almaktadır.

| Kaynak | Donanım tanımı | Yorum |
|---|---|---|
| `README.md` | `4 × ADS1293 + STM32F103C8T6 + nRF52832` | 12 derivasyonlu, daha geniş kart kurgusu |
| `research_proposal.txt` | `ADS1293 + STM32F103C8T6 + nRF52832` | 3 kanallı / erken prototip kurgusu |

Bu nedenle güç bütçesi tablolarında hem 3 kanallı hem 12 kanallı senaryo verilmiştir.

## 3. Modelin Nicel Kaynak Ayak İzi

Bu bölümdeki hesaplar depo içindeki `DCA-CNN` mimarisinden türetilmiştir. Bu değerler doğrudan üretici ölçümü değil, mimari tabanlı mühendislik hesabıdır.

### 3.1 Yaklaşık işlem yükü

| Metrik | Değer |
|---|---:|
| Yaklaşık toplam MAC | `19.54 MMAC` |
| Yaklaşık toplam FLOP | `39.09 MFLOP` |
| Çıkış sınıfı | `55` |
| Giriş boyutu | `12 × 2500` |

### 3.2 Alt sınır ara bellek gereksinimi

| Bellek metriği | INT8 | FP32 |
|---|---:|---:|
| En büyük tek ara tensör | `40,064` bayt | `160,256` bayt |
| İki büyük tensörün eşzamanlı alt sınırı | `80,064` bayt | `320,256` bayt |
| Hesap türü | Mimari tabanlı alt sınır | Mimari tabanlı alt sınır |

Bu tabloya `tensor arena`, `scratch buffer`, çalışma zamanı üst verisi, BLE tamponu, DSP tamponu ve stack dahil değildir. Bu nedenle gerçek çalışma zamanı gereksinimi tablodaki değerlerden daha yüksektir.

### 3.3 Çıkarım için kritik sonuç

| İnceleme konusu | Teknik sonuç |
|---|---|
| Model ağırlık boyutu | `STM32F103C8T6` flash sınırını aşar |
| Ara bellek alt sınırı | `nRF52832` RAM sınırını tek başına zorlar |
| Çıkarım periyodu | Seyrek çıkarım ortalama gücü düşürür; ancak anlık aktif bellek gereksinimini çözmez |

## 4. Mevcut Kart Bileşenlerinin Resmî Teknik Sınırları

### 4.1 Mevcut kartta geçen temel bileşenler

| Bileşen | Temel kapasite / güç verisi | Teknik anlamı |
|---|---|---|
| STM32F103C8T6 | `64 KB Flash`, `20 KB SRAM`, `72 MHz` | Mevcut modeli doğrudan taşıyamaz |
| nRF52832 | `512 KB Flash`, `64 KB RAM`, `64 MHz Cortex-M4F` | Flash yeterli olabilir; RAM tarafı kritik darboğazdır |
| ADS1293 | `0.3 mW / kanal` düşük güç AFE | Analog ön uç gücü düşüktür; toplam bütçede belirleyici kalem çoğu zaman AI değildir |

### 4.2 Resmî güç verileri

| Bileşen | Resmî veri | Yaklaşık güç karşılığı |
|---|---:|---:|
| ADS1293 | `0.3 mW / kanal` | Doğrudan üretici verisi |
| nRF52832 CPU | `58 µA / MHz` | `64 MHz` için yaklaşık `3.7 mA` |
| nRF52832 CPU + radyo | `9.2 mA` | `3.0 V` kabulü ile yaklaşık `27.6 mW` |
| STM32F103C8T6 run mode | `32.8 mA @ 72 MHz` | `3.3 V` kabulü ile yaklaşık `108 mW` |
| STM32F103C8T6, tüm çevre birimleri etkin | `50 mA @ 72 MHz` | `3.3 V` kabulü ile yaklaşık `165 mW` |

### 4.3 Analog ön uç güç bütçesi

| Senaryo | ADS1293 sayısı | Kanal sayısı | Yaklaşık analog güç |
|---|---:|---:|---:|
| Erken prototip | `1` | `3` | `0.9 mW` |
| Genişletilmiş kart | `4` | `12` | `3.6 mW` |

Bu tablo, analog ön uç gücünün düşük olduğunu; toplam bütçede belirleyici kalemin çoğu senaryoda MCU, BLE ve olası AI çalıştırma yükü olduğunu göstermektedir.

## 5. Mevcut Kart Üzerinde Gömülü Çalıştırma Analizi

### 5.1 STM32F103C8T6 üzerinde değerlendirme

| İnceleme başlığı | Değer | Sonuç |
|---|---:|---|
| Flash kapasitesi | `64 KB` | `312.3 KiB` aktif model sığmaz |
| SRAM kapasitesi | `20 KB` | Ara bellek alt sınırının altında kalır |
| Çekirdek tipi | Cortex-M3 | DSP/NPU avantajı yok |
| Sonuç | — | Doğrudan gömülü çıkarım için uygun değil |

### 5.2 nRF52832 üzerinde değerlendirme

| İnceleme başlığı | Değer | Sonuç |
|---|---:|---|
| Flash kapasitesi | `512 KB` | Her iki INT8 model de teorik olarak sığabilir |
| RAM kapasitesi | `64 KB` | `~80 KB` ara bellek alt sınırının altında kalır |
| Çekirdek tipi | Cortex-M4F | İşlem yeteneği artar, ancak bellek problemi sürer |
| BLE birlikte çalışma yükü | Var | Kullanılabilir RAM daha da azalır |
| Sonuç | — | Mevcut modeli olduğu gibi taşımak için uygun görünmez |

## 6. Güç Tüketimi Tahminleri

### 6.1 Cortex-M4F tabanlı türetilmiş çıkarım tahmini

Bu bölümdeki değerler, `ECG-TCN` çalışmasında verilen Cortex-M4F enerji verimliliğinin, depodaki `DCA-CNN` işlem yüküne ilk derece yansıtılmasıyla elde edilmiştir. Bu değerler doğrudan `nRF52832` üzerinde yapılmış ölçüm değildir.

| Türetilmiş metrik | Değer |
|---|---:|
| Yaklaşık çıkarım enerjisi | `~45 mJ / inference` |
| Sadece AI için 10 saniyede bir çıkarım durumunda ortalama güç | `~4.5 mW` |
| Yalnız CPU için kaba gecikme bandı | `~4.1 s / inference` |
| CPU + radyo güç düzeyine göre kaba gecikme bandı | `~1.65 s / inference` |

Bu tablodaki gecikme değerleri, enerji-verimlilik tabanlı ters hesaplamadır. Bellek yetersizliği çözülemediği sürece bu sayılar pratik çalıştırma garantisi vermez.

### 6.2 Kart seviyesinde güç kalemlerinin göreli etkisi

| Güç kalemi | Düşük uç senaryo | Yüksek uç senaryo | Not |
|---|---:|---:|---|
| Analog ön uç | `0.9 mW` | `3.6 mW` | 3 kanal ve 12 kanal karşılığı |
| nRF52832 CPU | `~11.1 mW` | `~27.6 mW` | Yalnız CPU ve CPU+radyo göreli aralık |
| STM32F103 aktif çalışma | `~108 mW` | `~165 mW` | Çevre birimi etkinliğine bağlı |
| DCA-CNN türetilmiş AI ortalama gücü | `~4.5 mW` | — | Sadece 10 saniyede bir çıkarım varsayımı altında |

Bu tablo iki önemli sonucu gösterir:

| Gözlem | Teknik anlamı |
|---|---|
| Analog güç çok düşüktür | AI entegrasyonu öncelikle bellek ve anlık aktif güç problemidir |
| Seyrek çıkarım ortalama gücü düşürür | Ancak flash ve RAM darboğazını ortadan kaldırmaz |

## 7. Alternatif Gömülü AI Platformları

### 7.1 Daha yüksek bellekli MCU ve AI-MCU seçenekleri

| Platform | Bellek / hız bilgisi | Resmî veya referans performans verisi | Bu proje açısından anlamı |
|---|---|---|---|
| STM32H735 | `1 MB Flash`, `564 KB RAM` | ST benchmarklarında `2.59 mJ` ile `16.5 mJ` arası örnekler | Bellek açısından anlamlı rahatlama sağlar |
| STM32N6 | `600 GOPS`, `3 TOPS/W`, `4.2 MB RAM` | ST benchmarklarında `2.72 mJ` ile `12.85 mJ` arası örnekler | NPU sınıfı çözüm; daha büyük modeller için de güvenli alan sunar |
| MAX78000 | `442 KB` ağırlık belleği, `512 KB` CNN veri belleği | Resmî KWS örneğinde `2 ms`, `0.14 mJ` | Ultra düşük güçlü AI-MCU sınıfı |
| MAX78002 | `2 MB` ağırlık belleği, `1.3 MB` CNN veri belleği, `2.5 MB Flash` | Daha geniş CNN bellek marjı | Çok kanallı veya daha büyük model ailesi için daha elverişli |

### 7.2 Karşılaştırmalı uygulanabilirlik tablosu

| Platform | Modelin ağırlıkları | Ara bellek alt sınırı | Güç açısından yorum | Genel uygulanabilirlik |
|---|---|---|---|---|
| STM32F103C8T6 | Sığmaz | Sığmaz | Aktif güç yüksek, bellek yetersiz | Düşük |
| nRF52832 | Teorik olarak sığar | Sınırı aşar | Ortalama güç yönetilebilir olsa da RAM kritik | Düşük |
| STM32H735 | Sığar | Sığma olasılığı yüksektir | Anlık güç yükselir, fakat uygulanabilir | Orta-Yüksek |
| STM32N6 | Rahatlıkla sığar | Rahatlıkla sığar | NPU sayesinde daha elverişli | Yüksek |
| MAX78000 | Modelin küçültülmesine bağlı | Mimari uyarlamaya bağlı | ULP AI için güçlü aday | Orta-Yüksek |
| MAX78002 | Daha geniş marj sunar | Daha geniş marj sunar | ULP AI için daha güvenli alan | Yüksek |

## 8. Teknik Sonuçlar

### 8.1 Bulguların özeti

| Bulgu | Teknik sonuç |
|---|---|
| Aktif model boyutu `312.3 KiB` | `STM32F103C8T6` flash sınırını aşar |
| DCA-CNN ara bellek alt sınırı `~80 KB` | `nRF52832` RAM sınırını aşar |
| Analog ön uç gücü `0.9-3.6 mW` aralığındadır | Güç bütçesinin baskın kalemi analog bölüm değildir |
| Seyrek çıkarım ortalama gücü azaltır | Ancak bellek darboğazı devam eder |
| Daha yüksek bellekli AI platformları mevcuttur | Kart revizyonu ile gömülü AI olasılığı belirgin biçimde artar |

### 8.2 Nihai değerlendirme

| İnceleme sorusu | Değerlendirme sonucu |
|---|---|
| Mevcut model mevcut proje kartında olduğu gibi gömülü çalıştırılabilir mi? | Mevcut `STM32F103C8T6 + nRF52832` sınıfında uygun görünmemektedir |
| En kritik sınırlayıcı nedir? | Öncelikle bellek, ikinci olarak etkin çıkarım platformu |
| Güç tüketimi tek başına belirleyici engel midir? | Hayır; asıl engel bellek ve çalışma zamanı altyapısıdır |
| Kart revizyonu ile gömülü çalıştırma mümkün olabilir mi? | Evet; daha yüksek bellekli MCU/NPU ya da AI-MCU sınıfında mümkündür |

## 9. Yöntem ve Sınırlılıklar

| Başlık | Açıklama |
|---|---|
| Doğrudan doğrulanan veriler | Depodaki model dosyaları, mobil çıkarım kodu ve dokümantasyon |
| Dış kaynak verileri | Üretici veri sayfaları, ürün sayfaları ve ST/ADI referans benchmarkları |
| Türetilmiş hesaplar | MAC/FLOP hesabı, ara bellek alt sınırı ve M4F enerji projeksiyonu |
| Sınırlılık | Bu rapor doğrudan kart üzerinde laboratuvar güç ölçümü içermemektedir |
| Sonuçların kullanım şekli | Fizibilite, mimari seçim ve kart revizyonu değerlendirmesi için uygundur |

## 10. Kaynaklar

### 10.1 Proje içi kaynaklar

| Kaynak | Bağlantı |
|---|---|
| Proje ana özeti | [README](../../README.md) |
| Mobil çıkarım sınıfı | [ArrhythmiaClassifier](../../mobile/app/src/main/java/com/hayatinritmi/app/processing/ArrhythmiaClassifier.kt) |
| Model ve benchmark durumu | [Master implementation status](../plans/2026-03-master-implementation-status.md) |
| Araştırma önerisi | [research_proposal.txt](../research_proposal.txt) |

### 10.2 Resmî ve akademik dış kaynaklar

| Kaynak | Bağlantı |
|---|---|
| STMicroelectronics, STM32F103C8 ürün sayfası | https://www.st.com/en/microcontrollers-microprocessors/stm32f103c8.html |
| Nordic, nRF52832 Product Specification v1.9 | https://docs.nordicsemi.com/en-US/bundle/nRF52832_PS_v1.9/resource/nRF52832_PS_v1.9.pdf |
| Texas Instruments, ADS1293 ürün sayfası | https://www.ti.com/product/ADS1293 |
| ST, STM32H735xG veri sayfası | https://www.st.com/resource/en/datasheet/stm32h735vg.pdf |
| ST wiki, STM32Cube.AI model performansları | https://wiki.st.com/stm32mcu/wiki/AI%3ASTM32Cube.AI_model_performances |
| ST, STM32N6 serisi ürün sayfası | https://www.st.com/en/microcontrollers-microprocessors/stm32n6-series.html |
| Analog Devices, MAX78000 ürün sayfası | https://www.analog.com/en/products/max78000.html |
| Analog Devices, Keyword Spotting Using the MAX78000 | https://www.analog.com/en/resources/design-notes/keywords-spotting-using-the-max78000.html |
| Analog Devices, Developing Power-Optimized Applications on the MAX78000 | https://www.analog.com/en/resources/app-notes/2022/07/16/12/56/developing-power-optimized-apps-on-the-max78000.html |
| Analog Devices EngineerZone, MAX78000 ve STM32H7 karşılaştırması | https://ez.analog.com/other-products/w/documents/31473/how-does-the-max78000-performance-compare-against-the-stm32h7-which-uses-a-cortex-m7-with-dsp |
| Analog Devices, MAX78002 ürün sayfası | https://www.analog.com/en/products/max78002.html |
| ECG-TCN: Wearable Cardiac Arrhythmia Detection with a Temporal Convolutional Network | https://arxiv.org/abs/2103.13740 |
