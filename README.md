# Kasa Inspection

ArUco işareti tabanlı hizalama ile çalışan, kamera görüntüsünden ürün
üzerindeki gözlerin dolu/boş durumunu tespit eden bir kalite kontrol
sistemi. PySide6 (Qt) tabanlı üç uygulamadan oluşur: **Ana Menü**,
**Kurulum** ve **İnceleme**. Arayüz Türkçe, kod İngilizce yazılmıştır.

## Özellikler

**Kurulum**
- Band (istasyon) oluşturma, listeleme, doğrulama
- Kamera ile referans görüntü çekimi (ArUco ile otomatik hizalama)
- Sürüklenebilir polygon tabanlı göz editörü — köşe noktalarından tek tek
  boyutlandırma, referans fotoğrafındaki bölme çizgilerinden **otomatik göz
  tespiti**
- **Çoklu kamera desteği** — aynı kasayı farklı açılardan izlemek için
  birincil kameraya ek kamera kanalları tanımlanabilir; her kanalın kendi
  referans fotoğrafı ve göz seti vardır, kanal seçim kutusuyla aralarında
  geçiş yapılır
- Model (recipe) yönetimi — her model için beklenen göz durumları (dolu/boş);
  isteğe bağlı olarak göz başına özel değişim eşiği (override) — checklist
  veya referans fotoğrafına tıklayarak seçilebilir; ek kamera kanallarının
  gözleri listede `KanalAdı:Göz` şeklinde nitelenmiş görünür
- Band'ı `.zip` olarak dışa/içe aktarma (başka bir makineye taşımak için)
- Operatör yönetimi: PIN ile giriş, yeni operatörler yönetici onayı bekler,
  onaylama/silme yetkisi sadece yöneticide
- Giriş/çıkış ve değişiklik logu görüntüleyici (Excel'e aktarılabilir)
- Arduino alarm portu listeleme ve otomatik yeniden bağlanma (demo/sunum
  amaçlı donanım entegrasyonu)
- **Telegram bildirim ayarları** — bot token/chat ID, HATA ve kamera bağlantı
  kopması bildirimlerini ayrı ayrı açma/kapama, emoji reaksiyonuyla HATA'yı
  UYGUN'a çevirme özelliği ve kullanılacak emojinin seçimi
- **Bildirim alıcıları** — telefon numarası paylaşarak (Telegram "kişi
  paylaş" akışıyla) birden fazla alıcıyı bildirimlere ekleme/çıkarma
- Uygulama içi **Testler** sekmesi (sadece geliştirme ortamında) — pytest
  suite'ini arayüzü kilitlemeden çalıştırıp sonuçları okunabilir isimlerle
  gösterir

**İnceleme**
- Band/model seçip canlı kontrolü başlatma
- ArUco ile otomatik hizalama; kareler arası titreşimi azaltan yumuşatma ve
  işaretler kaybolup geri geldiğinde otomatik yeniden kalibrasyon (kilit
  oturana kadar "kalibre ediliyor" göstergesi)
- **Çoklu kamera** tanımlıysa, her kanalın karesi aynı anda işlenir ve
  görüntüler yan yana birleştirilerek gösterilir; genel UYGUN/HATA kararı
  tüm kanalların tüm gözlerinin birleşiminden hesaplanır (herhangi biri
  HATA ise genel sonuç HATA)
- Kamera bağlantısı koparsa otomatik yeniden bağlanma; disk alanı azaldığında
  uyarı
- HATA durumunda görsel banner + sesli uyarı
- **Telegram bildirimleri** — HATA oluştuğunda fotoğraf ve hangi gözlerin
  HATA olduğu bilgisiyle, kamera bağlantısı koptuğunda ise ayrı bir uyarıyla
  tanımlı tüm alıcılara mesaj gönderilir; kamera titremesinden kaynaklı
  yanlış bildirimleri önlemek için ardışık kare onayı (debounce) kullanılır.
  Gönderilen bir HATA mesajına belirlenen emojiyle tepki verilirse kayıt
  otomatik olarak UYGUN'a çevrilir
- Hata Ayıklama penceresi: göz bazında referans/güncel/fark görüntüleri,
  canlı eşik ve onay-karesi (confirm frames) ayarı
- İnceleme geçmişi: her UYGUN/HATA geçişi SQLite'a (WAL modu,
  `inspection_log.db`) loglanır, HATA anındaki kare otomatik kaydedilir
- Geçmiş penceresi: kayıt tablosu, göz bazında detay, tek tek göz düzeltme
  (yanlış tespiti işaretleyip düzeltme — orijinal sonuç ileride model eğitimi
  için saklanır), yedekleme, Excel'e aktarma
- İstatistikler sekmesi: genel UYGUN/HATA dağılımı için pasta grafiği,
  günlük hata oranı trendi, vardiya bazlı hata oranı trendi (bandın tanımlı
  sabit vardiya pencerelerine göre, ör. "Sabah" 07:30-15:30), model/göz
  bazında tablo veya çubuk grafik arasında geçiş

**Ortak**
- PIN tabanlı erişim kontrolü (varsayılan yönetici: `Yönetici` / `0000`,
  ilk girişte değiştirilmesi önerilir)
- Erişebilirlik ayarları (Görünüm menüsü): yazı/arayüz boyutu, yüksek
  kontrast / renk körü dostu UYGUN-HATA renk paleti, sık kullanılan
  butonlarda klavye kısayolları (Alt+harf)
- Tüm önemli işlemler `logs/app.log`'a loglanır (5 MB'ta otomatik döner)

## Kurulum

Python 3.11+ gerekir.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma

En kolayı ana menüden başlatmak:

```bash
python apps/launcher.py
```

Ya da uygulamaları doğrudan çalıştırabilirsin:

```bash
python apps/configurator.py   # Band/model/göz kurulumu (Kurulum)
python apps/inspection.py     # Canlı inceleme (İnceleme)
```

Her iki uygulama da açılışta PIN girişi ister.

## İlk Kullanım

1. **Kurulum**'u aç, PIN ile giriş yap (varsayılan `Yönetici` / `0000`).
2. Yeni bir band oluştur, kamerayla referans fotoğrafı çek.
3. Gözler sekmesinde gözleri çiz (elle veya "Otomatik Göz Bul" ile), gerekirse
   köşelerinden boyutlandır.
4. Modeller sekmesinde en az bir model oluşturup hangi gözlerin DOLU olması
   gerektiğini işaretle (isteğe bağlı: göz başına özel eşik gir).
5. **İnceleme**'yi aç, bandı/modeli seç, Başlat'a bas.

## Testler

```bash
python -m pytest tests/ -v
```

Core motorlar (ArUco lokalizasyon, karar mantığı, inspection loglama,
performans-kritik kırpma) ve yapılandırma modülleri (band/model/operatör
yönetimi, doğrulama, yedekleme, dışa/içe aktarma, loglama, Telegram
bildirimleri, çoklu kamera kanalları) için toplam 190'ın üzerinde birim
testi vardır. `main` dalına her push/PR'da GitHub Actions ile otomatik
çalışır (`.github/workflows/tests.yml`).

## .exe Olarak Paketleme

Band bilgisayarlarına Python kurmadan çalıştırılabilir bir sürüm üretmek için
PyInstaller kullanılır:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements-build.txt
python build_exe.py
```

Çıktı `dist/KasaInspection/` altında üç kardeş klasör olarak oluşur
(`Launcher/`, `Configurator/`, `Inspection/`) - band/model yapılandırması,
loglar ve pencere ayarları bu üç klasörün de bulunduğu ortak üst dizinde
(`dist/KasaInspection/configuration/`, `logs/`, `window_settings.ini`)
paylaşılır. Başka bir bilgisayara taşırken **`KasaInspection` klasörünün
tamamı** (üç alt klasörle birlikte) kopyalanmalı - tek bir `.exe` dosyası
taşımak yeterli değildir. Paketlenmiş sürümde uygulama-içi "Testler" sekmesi
görünmez (pytest ayrı bir bağımlılık, exe'ye dahil edilmez).

## Proje Yapısı

```
apps/
  launcher.py          # Ana menü
  configurator.py       # Kurulum giriş noktası
  inspection.py         # İnceleme giriş noktası

modules/
  core/                 # UI'dan bağımsız çekirdek: ArUco, lokalizasyon,
                        # perspektif düzeltme, karşılaştırma, karar motoru,
                        # otomatik göz tespiti, Arduino iletişimi, Telegram
                        # bildirim gönderimi ve emoji reaksiyon dinleyicisi
  configuration/         # Band/Model/Operatör yönetimi, kamera kanalı
                        # (çoklu açı) tanımları, inceleme logger,
                        # doğrulama, yedekleme, hata kare kaydetme,
                        # Excel/zip dışa-içe aktarma, Telegram ayarları/
                        # alıcıları
  controllers/           # Core motorları birleştiren, UI'dan bağımsız akış
  utils/                 # Logger (rotasyonlu), disk izleme, erişebilirlik
                        # ayarları, test çalıştırıcı
  ui/
    common/               # Uygulamalar arası ortak bileşenler (login,
                        # erişebilirlik ayarı, grafik widget'ları)
    configurator/         # Kurulum ekranları
    inspection/           # İnceleme ekranı, geçmiş/istatistik penceresi

configuration/
  band_XX/              # Her istasyon için: band.json, roi.json,
                        # reference.png, models/*.json
                        # cameras/<kanal_id>/roi.json, reference.png
                        # (ek kamera kanalları, varsa)
                        # (inspection_log.db, ng_captures/ çalışma zamanı
                        # verisidir, operators.json gizli bilgi içerir —
                        # hiçbiri git'e girmez)
  telegram_settings.json     # Bot token / chat ID (gizli, git'e girmez)
  telegram_recipients.json   # Kayıtlı bildirim alıcıları (gizli, git'e girmez)

tests/                  # Birim testleri
```

## Bağımlılıklar

- **PySide6** — arayüz
- **opencv-contrib-python** — ArUco algılama, görüntü işleme
- **numpy** — matris/vektör işlemleri
- **openpyxl** — Excel dışa aktarma
- **pyserial** — Arduino alarm entegrasyonu (demo)
- **requests** — Telegram Bot API (bildirim gönderme, emoji reaksiyon
  dinleme)
- **pytest** — testler
