# Kongre Bildirisi Ozeti (Taslak)

## Baslik

Cok Kanalli Adaptif Yapay Zeka Tabanli Tasinabilir EKG Erken Uyari Sistemi:
Hayatin Ritmi

## Ozet

Kardiyovaskuler olaylarda erken farkindalik, klinik sonuclari dogrudan etkileyen
kritik bir faktordur. Bu calismada, tasinabilir bir EKG donanimi ile Android tabanli
bir analiz uygulamasini birlestiren, uc-uctan bir erken uyari sistemi sunulmustur.
Sistem mimarisi; BLE tabanli veri iletimi, gercek zamanli sinyal isleme, hafif
siniflandirma modelleri (TFLite), yerel sifreli veri saklama ve raporlama modulunden
olusur. Uygulama tarafinda Room + SQLCipher, PBKDF2 tabanli kimlik dogrulama,
CSV/PDF export ve acil durum akislarini destekleyen modul yapisi uygulanmistir.

Yazilim dogrulama surecinde Python AI testleri (22/22) ve Android testleri (78/78)
tamamlanmis; toplam 100/100 test basarili olarak gecmistir. Ayrica baglanti stabilitesi,
enerji/veri tamponu yonetimi ve erisilebilirlik gereksinimleri icin backpressure,
parser ve WCAG yardimci katmanlari eklenmistir. Bu ciktilar, saha pilotuna
hazirlik amacli bir runbook, SUS olcek seti ve otomatik metrik raporlama araci ile
desteklenmistir.

Calismanin bir sonraki adimi, ADS1293 tabanli prototip ile 60+ saat saha kaydi
uzerinden hedef metriklerin (dogruluk, gecikme, yanlis alarm, kullanilabilirlik)
dogrulanmasidir. Sunulan altyapi, akademik ve urunlesme odakli ileri calismalara
dogrudan aktarilabilir niteliktedir.

## Anahtar Kelimeler

ECG, tasinabilir saglik, Bluetooth Low Energy, TensorFlow Lite, erken uyari
