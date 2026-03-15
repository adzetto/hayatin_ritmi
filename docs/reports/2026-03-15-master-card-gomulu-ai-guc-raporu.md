# Master Card Uzerinde Gomulu AI Guc ve Fizibilite Raporu

Tarih: 15 Mart 2026

## Kisa Sonuc

Bu depodaki aktif model, mobil tarafta calisan `DCA-CNN INT8` modelidir: `319,768` bayt (`312.3 KiB`), giris sekli `[1, 2500, 12]`, 10 saniyelik pencere, 12 kanal EKG, her 10 saniyede bir cikarim. Kaynak: [ArrhythmiaClassifier](../../mobile/app/src/main/java/com/hayatinritmi/app/processing/ArrhythmiaClassifier.kt), [master implementation status](../plans/2026-03-master-implementation-status.md).

En kritik sonuc su: bu modeli bugunku proje kartina "telefondan alip oldugu gibi master karta gommek" mevcut kart bilesenleriyle pratik degildir. Ana neden islem gucu degil, once bellek uyumsuzlugudur:

- `STM32F103C8T6`: `64 KB Flash / 20 KB SRAM` sinirinda. Model dosyasi tek basina sigmaz.
- `nRF52832`: `512 KB Flash / 64 KB RAM` ile model dosyasini flash tarafinda tasiyabilir; ancak tahmini INT8 iki-buyuk tensore dayali gecici aktivasyon ihtiyaci bile `~80 KB` duzeyindedir. Scratch buffer, tensor arena, stack ve BLE/DSP yukleri eklendiginde `64 KB RAM` siniri asilir.

Bu nedenle mevcut kartta iki makul yol vardir:

1. Kisa vadede AI cikarimini telefonda tutmak.
2. Gercekten karta gomulu AI isteniyorsa karti AI-MCU / NPU sinifina tasimak.

Bu raporda "master card" ifadesini, proje icindeki ana kart / sensorkart olarak yorumladim. Depoda bu isim acikca sabitlenmis degil.

## 1. Projeden Dogrulanan Baslangic Verileri

### 1.1 Aktif model

- Aktif mobil model: `ecg_dca_cnn_int8.tflite`
- Boyut: `319,768` bayt (`312.3 KiB`)
- Fallback model: `ecg_model_int8.tflite`
- Boyut: `237,152` bayt (`231.6 KiB`)
- Giris: `12 x 2500` EKG penceresi, `250 Hz`, `10 s`
- Cikarim periyodu: her `2500` ornekte bir, yani yaklasik her `10 s`

Yerel kaynaklar:

- [ArrhythmiaClassifier](../../mobile/app/src/main/java/com/hayatinritmi/app/processing/ArrhythmiaClassifier.kt)
- [README](../../README.md)
- [Master implementation status](../plans/2026-03-master-implementation-status.md)

### 1.2 Donanim baglami

Depoda iki farkli donanim anlatimi var:

- [README](../../README.md): `4 x ADS1293 + STM32F103C8T6 + nRF52832`, yani 12-derivasyonlu akisa yakin bir kurgu.
- [Research proposal](../research_proposal.txt): `ADS1293 + STM32F103C8T6 + nRF52832`, daha cok 3-kanal / erken prototip kurgusu.

Bu raporda ikisini birlikte degerlendirdim:

- 12 kanal sistem varsayimi: analog on uc guc yukunun kabaca `4 x ADS1293` uzerinden gitmesi
- 3 kanal sistem varsayimi: tek `ADS1293` ile calisan daha kucuk prototip

## 2. Model Kaynak Ayak Izi

Asagidaki iki satir dogrudan depodaki mimariden turetilmistir; bunlar resmi vendor verisi degil, repo-temelli muhendislik hesabidir.

- Yaklasik hesap yukü: `19.54 MMAC` / inference (`39.09 MFLOP`, MAC=2 FLOP varsayimi)
- En buyuk tek INT8 ara tensor: `40,064` bayt
- En buyuk iki tensor ayni anda gerektiren INT8 durum: `80,064` bayt

Bu ne anlama geliyor?

- `STM32F103C8T6` tarafinda hem flash hem SRAM duvarina carpilir.
- `nRF52832` tarafinda flash yeterli olabilir ama `64 KB RAM`, yalnizca iki buyuk tensor icin bile yetmez.
- Fallback `DS-1D-CNN` modeli daha kucuk olsa da ic blok kanal genislikleri benzer oldugu icin aktivasyon RAM problemi buyuk olasilikla devam eder.

Dolayisiyla problem yalnizca model dosyasi boyutu degil; asil darbogaz `activation + scratch + runtime arena` tarafidir.

## 3. Resmi Kaynaklardan Bilesen Guc Verileri

### 3.1 Mevcut kart bilesenleri

| Bilesen | Resmi veri | Karta etkisi |
|---|---:|---|
| ADS1293 | `0.3 mW/channel` | 3 kanal prototipte `~0.9 mW`, 12 kanal (4 x ADS1293) yapida `~3.6 mW` |
| nRF52832 CPU | `58 uA/MHz` | `64 MHz`'te kabaca `~3.7 mA`; `3.0 V` kabul edilirse `~11.1 mW` |
| nRF52832 CPU + radyo | `9.2 mA` (CoreMark + TX0/RX) | `3.0 V` kabul edilirse `~27.6 mW` |
| STM32F103 run mode | `32.8 mA @ 72 MHz` (peripherals disabled), `50 mA` (all peripherals enabled) | `3.3 V` kabul edilirse `~108 mW` ila `~165 mW` teorik aktif guc |

Buradaki ilk onemli gozlem:

- Analog on uc gucu tek haneli mW mertebesinde.
- MCU / BLE / AI hesaplama yukleri bunu kolayca gecebilir.
- Yani gomulu AI kararinda ana mesele sensor gucu degil, bellek ve hesap tarafidir.

## 4. Mevcut Kartta Gomulu AI Olursa Ne Olur?

### 4.1 STM32F103C8T6 uzerinde

Bu secenek pratikte elenir.

Neden:

- `64 KB Flash`, `312 KB` aktif modeli tutamaz.
- `20 KB SRAM`, `~80 KB` cift-tensor INT8 tepe ihtiyacinin bile cok altinda.
- Ustelik Cortex-M3 sinifinda DSP/NPU yok.

Sonuc:

- `DCA-CNN` imkansiza yakin
- `DS-1D-CNN` fallback modeli de flash ve SRAM sinirlarina takilir
- Bu islemcide model transplantasyonu yerine modelin tamamen yeniden tasarlanmasi gerekir

### 4.2 nRF52832 uzerinde

Bu secenek kagit uzerinde STM32'den daha yakindir ama halen "oldugu gibi gecis" icin uygun degildir.

Artılar:

- `512 KB Flash`, her iki INT8 modeli de sigdirabilir.
- Cortex-M4F + DSP talimatlari, STM32F103'e gore cok daha uygun.

Eksiler:

- `64 KB RAM`, repo-temelli `~80 KB` cift-tensor ihtiyacinin altinda.
- BLE stack, stack/heap, DMA ve filtreleme ile birlikte gercek alan daha da daralir.

Birinci derece tahmin:

- Eğer bu model, literaturdeki bir Cortex-M4F ECG modeli kadar verimli calisabilseydi bile enerji tuketimi inference basina `~45 mJ` mertebesine cikardi.
- Bu da `10 saniyede 1 inference` ritminde yalniz AI cikarimi icin ortalama `~4.5 mW` demektir.
- Aynı kabul ile gecikme sinifi da `~1.5-4 s / inference` bandina kayar.

Bu rakamlar dogrudan nRF52832 olcumu degildir; [ECG-TCN](#kaynaklar) calismasindaki Cortex-M4F enerji verimliliginin sizin `DCA-CNN` MAC yukune yansitilmasiyla elde edilmis `ilk-derece tahmin`dir. Gercek sonuc bundan daha kotu olabilir; cunku sizin modeliniz tek lead TCN degil, 12-kanal CNN tabanli daha buyuk bir agdir.

Sonuc:

- `nRF52832`, "bu modeli oldugu gibi karta tasima" icin uygun degil.
- Ama cok daha kucuk, tek/uc kanal, baskadan tasarlanmis tiny model icin hala aday olabilir.

## 5. Guc ve Fizibilite Senaryolari

### 5.1 Senaryo ozeti

| Senaryo | Fizibilite | Guc/enerji yorumu | Karar |
|---|---|---|---|
| Mevcut kart, ayni `DCA-CNN` | Cok dusuk | RAM once biter; guc ikinci problem olur | `No-go` |
| Mevcut kart, `DS-1D-CNN` fallback | Dusuk | Flash sigabilir ama aktivasyon RAM duvari surer | `No-go` |
| Mevcut kart, yeni tiny model | Orta | Ancak baska mimari gerekir | `Mumkun ama yeniden tasarimla` |
| `STM32H735` sinifi MCU revizyonu | Yuksek | Resmi ST benchmarklarinda aktif inference gucu `~300 mW` bandinda, enerji `2.59-16.5 mJ` | `Mumkun` |
| `STM32N6` sinifi NPU revizyonu | Cok yuksek | `600 GOPS`, `3 TOPS/W`, `4.2 MB RAM`; resmi ST benchmarklarinda `2.72-12.85 mJ` | `Cok uygun` |
| `MAX78000 / MAX78002` sinifi AI-MCU | Yuksek | ULP AI icin en guclu aday; resmi MAX78000 KWS olcumu `0.14 mJ`, `2 ms`, 10 s duty-cycle senaryosunda `6.58-8.3 mW` ortalama guc | `Batarya-odakli en guclu yon` |

### 5.2 STM32H735 sinifi MCU ne saglar?

ST'nin resmi benchmark sayfasinda `STM32H735G-DK` icin su referanslar var:

- `KWS`: `65 KB` flash agirlik, `24 KB` aktivasyon, `8.16 ms`, `2.59 mJ`, `96 mA`
- `YAMNet`: `187 KB` flash agirlik, `117 KB` aktivasyon, `50.4 ms`, `16.5 mJ`, `99 mA`

Bu sinif MCU, sizin modele artik bellek acisindan anlamli bir alan acar:

- `1 MB flash`
- `564 KB RAM`

Bu ne demek?

- Modeli NPU olmadan da karta gommek mumkun olur.
- Ama aktif inference gucu tek haneli mW degil, yuzlerce mW anlik banda cikar.
- Yine de inference seyrekse ortalama guc kabul edilebilir kalabilir.

### 5.3 STM32N6 ne saglar?

ST'nin resmi verilerine gore `STM32N6` ailesi:

- `600 GOPS`
- `3 TOPS/W`
- `4.2 MB` contiguous RAM

Ayni ST benchmark sayfasinda `STM32N6x7` icin ornekler:

- `KWS`: `2.72 mJ`, `12.1 ms`, `225 mW`
- `YAMNet 1024`: `3.2 mJ`, `9.7 ms`, `332 mW`
- Daha buyuk vision modellerinde `12.85 mJ` seviyelerine cikiliyor

Sizin ECG modeli bu cihazda:

- rahat sigar
- gelecekte daha buyuk veya coklu-sensor fusion modellerine de alan birakir
- ama anlik aktif guc yine yuksek olur

Buna ragmen `10 saniyede 1 inference` gibi bir senaryoda ortalama guc hala dusuk kalir; asil bedel, kart karmasikligi ve BOM artisi olur.

### 5.4 MAX78000 / MAX78002 neden dikkat cekiyor?

`MAX78000` resmi urun sayfasi ve uygulama notlari su sinifi gosteriyor:

- `442 KB` 8-bit weight kapasitesi
- `512 KB` CNN data memory
- `time-series` ve `health signal analysis` gibi kullanimlara yonelik konumlama
- resmi referans uygulamada `keyword spotting` icin `2.0 ms`, `0.14 mJ`
- guc optimize edilmis 10 saniyelik dinleme senaryosunda `6.58-8.3 mW` ortalama guc

Bu sayilar dogrudan sizin DCA-CNN modelinizin olcumu degildir; ancak "batarya odakli gomulu AI-MCU" sinifinin ne kadar verimli olabilecegini gosteriyor.

`MAX78002` ise daha guclu ve daha genis guvenlik payi saglar:

- `2 MB` 8-bit weight memory
- `1.3 MB` CNN data memory
- `2.5 MB flash`

Bu nedenle, eger hedef "telefonu aradan cikarmak ve AI'yi karta gercekten gommek" ise:

- en dusuk ortalama guc icin `MAX78000 / MAX78002`
- en genis esneklik ve entegrasyon kolayligi icin `STM32N6`

ikilisi teknik olarak en anlamli adaylar olarak gorunuyor.

## 6. Ne Oneriyorum?

### 6.1 Kisa vadeli onerim

Urunlesme hizi hedefleniyorsa:

- mevcut karti sensor + BLE + on-isleme karti olarak birakin
- `DCA-CNN` cikarimini telefonda tutun
- karttan telefona tam waveform yerine kalite skoru, ozet ozellikler veya olay bazli kesit gondermeyi optimize edin

Neden:

- mevcut kartta model sigmiyor
- kart revizyonu olmadan AI'yi karta alma riski yuksek
- telefon zaten TFLite cikarimini cok dusuk gecikmeyle yapiyor

### 6.2 Gercekten karta gomulu AI istiyorsaniz

Iki temiz yol var:

1. `Rev-B / Rev-C kart + AI-MCU`
   - batarya oncelikliyse `MAX78002`
   - ekosistem ve genel esneklik oncelikliyse `STM32N6`

2. `Mevcut nRF52 sinifina ozel yeni tiny model`
   - tek lead veya 3 lead
   - cok daha dar kanal genislikleri
   - hedef: `<= 150 KB` agirlik, `<= 48 KB` arena, `<= 5 MMAC`

Bu ikinci yol, bugunku `DCA-CNN`'i tasimak degil; neredeyse yeni bir model ailesi tasarlamak anlamina gelir. Literatürde bunun dogru yonu var: `ECG-TCN` benzeri, tek/az kanalli ve giyilebilir odakli mimariler.

### 6.3 Nihai karar

Benim teknik kararim su:

- `mevcut master card + mevcut DCA-CNN`: uygun degil
- `mevcut master card + yeni tiny model`: ancak buyuk mimari sadeleme ile mumkun
- `kart revizyonu + AI-MCU/NPU`: dogru yol

En dengeli yol:

- kisa vadede telefonda inference
- orta vadede `MAX78002` veya `STM32N6` tabanli AI revizyonu

## 7. Aksiyon Plani

Eger bu yonu secerseniz bir sonraki mantikli teknik adimlar sunlar:

1. Fiziksel kartin gercekten `3 kanal` mi `12 kanal` mi oldugunu sabitleyin.
2. Gecikme hedefini sabitleyin: `<=1 s`, `<=5 s`, yoksa `10 s pencere sonu` yeterli mi?
3. Buna gore iki teknik kol acin:
   - `Track A`: telefonda inference + kartta olay/ozellik cikarma
   - `Track B`: `MAX78002` ve `STM32N6` uzerinde PoC port
4. AI karta alinacaksa ilk PoC'yi dogrudan `DCA-CNN` ile degil, once daha kucuk bir 1-lead / 3-lead surrogate model ile yapin.

## Kaynaklar

### Proje ici kaynaklar

- [README](../../README.md)
- [ArrhythmiaClassifier](../../mobile/app/src/main/java/com/hayatinritmi/app/processing/ArrhythmiaClassifier.kt)
- [Master implementation status](../plans/2026-03-master-implementation-status.md)
- [Research proposal](../research_proposal.txt)

### Resmi ve akademik dis kaynaklar

- [STMicroelectronics, STM32F103C8 product page](https://www.st.com/en/microcontrollers-microprocessors/stm32f103c8.html)
- [Nordic, nRF52832 Product Specification v1.9 PDF](https://docs.nordicsemi.com/en-US/bundle/nRF52832_PS_v1.9/resource/nRF52832_PS_v1.9.pdf)
- [Texas Instruments, ADS1293 product page](https://www.ti.com/product/ADS1293)
- [ST, STM32H735xG datasheet](https://www.st.com/resource/en/datasheet/stm32h735vg.pdf)
- [ST wiki, STM32Cube.AI model performances](https://wiki.st.com/stm32mcu/wiki/AI%3ASTM32Cube.AI_model_performances)
- [ST, STM32N6 series product page](https://www.st.com/en/microcontrollers-microprocessors/stm32n6-series.html)
- [Analog Devices, MAX78000 product page](https://www.analog.com/en/products/max78000.html)
- [Analog Devices, Keyword Spotting Using the MAX78000](https://www.analog.com/en/resources/design-notes/keywords-spotting-using-the-max78000.html)
- [Analog Devices, Developing Power-Optimized Applications on the MAX78000](https://www.analog.com/en/resources/app-notes/2022/07/16/12/56/developing-power-optimized-apps-on-the-max78000.html)
- [Analog Devices EngineerZone, MAX78000 vs STM32H7 comparison note](https://ez.analog.com/other-products/w/documents/31473/how-does-the-max78000-performance-compare-against-the-stm32h7-which-uses-a-cortex-m7-with-dsp)
- [Analog Devices, MAX78002 product page](https://www.analog.com/en/products/max78002.html)
- [ECG-TCN: Wearable Cardiac Arrhythmia Detection with a Temporal Convolutional Network (arXiv)](https://arxiv.org/abs/2103.13740)

## Notlar

- Bu rapor bir `bench power measurement` raporu degil, kaynak temelli bir fizibilite ve guc butcesi raporudur.
- `DCA-CNN` MAC, FLOP ve aktivasyon degerleri repo mimarisinden turetilmis muhendislik hesaplaridir.
- M4F uzerindeki `~45 mJ / inference` tahmini, `ECG-TCN` calismasindaki enerji verimliliginin sizin modele ilk-derece yansitilmasidir; dogrudan olcum degildir.
