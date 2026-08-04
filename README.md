# Kasa Inspection

ArUco marker tabanlı hizalama ile çalışan, kamera görüntüsünden ürün üzerindeki
gözlerin (ROI) dolu/boş durumunu tespit eden bir kalite kontrol sistemi.
PySide6 (Qt) tabanlı üç uygulamadan oluşur: **Launcher** (ana menü),
**Configurator** (kurulum) ve **Inspection** (canlı kontrol). Arayüz Türkçe,
kod İngilizce yazılmıştır.

## Özellikler

**Configurator**
- Band (istasyon) oluşturma, listeleme, doğrulama
- Kamera ile referans görüntü çekimi (ArUco ile otomatik hizalama)
- Sürüklenebilir polygon tabanlı ROI editörü — köşe noktalarından tek tek
  boyutlandırma, referans fotoğrafındaki bölme çizgilerinden **otomatik ROI
  tespiti**
- Model (recipe) yönetimi — her model için beklenen ROI durumları (dolu/boş);
  isteğe bağlı olarak ROI başına özel değişim eşiği (override) — checklist
  veya referans fotoğrafına tıklayarak seçilebilir
- Band'ı `.zip` olarak dışa/içe aktarma (başka bir makineye taşımak için)
- Operatör yönetimi: PIN ile giriş, yeni operatörler yönetici onayı bekler,
  onaylama/silme yetkisi sadece yöneticide
- Giriş/çıkış ve değişiklik logu görüntüleyici (Excel'e aktarılabilir)
- Arduino alarm portu listeleme ve otomatik yeniden bağlanma (demo/sunum
  amaçlı donanım entegrasyonu)
- Uygulama içi **Testler** sekmesi — pytest suite'ini arayüzü kilitlemeden
  çalıştırıp sonuçları okunabilir isimlerle gösterir

**Inspection**
- Band/model seçip canlı kontrolü başlatma
- ArUco ile otomatik hizalama; kareler arası titreşimi azaltan yumuşatma ve
  markerlar kaybolup geri geldiğinde otomatik yeniden kalibrasyon (kilit
  oturana kadar "kalibre ediliyor" göstergesi)
- Kamera bağlantısı koparsa otomatik yeniden bağlanma; disk alanı azaldığında
  uyarı
- NG (hatalı) durumunda görsel banner + sesli uyarı
- Debug penceresi: ROI bazında referans/güncel/fark görüntüleri, canlı eşik
  ayarı
- Inspection geçmişi: her OK/NG geçişi SQLite'a (WAL modu, `inspection_log.db`)
  loglanır, NG anındaki kare otomatik kaydedilir
- Geçmiş penceresi: kayıt tablosu, ROI bazında detay, tek tek ROI düzeltme
  (yanlış tespiti işaretleyip düzeltme — orijinal sonuç ileride model eğitimi
  için saklanır), yedekleme, Excel'e aktarma
- İstatistikler sekmesi: genel OK/NG dağılımı için pasta grafiği, günlük NG
  oranı trendi, model/ROI bazında tablo veya çubuk grafik arasında geçiş

**Ortak**
- PIN tabanlı erişim kontrolü (varsayılan yönetici: `Yönetici` / `0000`,
  ilk girişte değiştirilmesi önerilir)
- Erişebilirlik ayarları (Görünüm menüsü): yazı/arayüz boyutu, yüksek
  kontrast / renk körü dostu OK-NG renk paleti, sık kullanılan butonlarda
  klavye kısayolları (Alt+harf)
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
python apps/configurator.py   # Band/model/ROI kurulumu
python apps/inspection.py     # Canlı inspection
```

Her iki uygulama da açılışta PIN girişi ister.

## İlk Kullanım

1. **Configurator**'ı aç, PIN ile giriş yap (varsayılan `Yönetici` / `0000`).
2. Yeni bir band oluştur, kamerayla referans fotoğrafı çek.
3. ROI sekmesinde gözleri çiz (elle veya "Otomatik ROI Bul" ile), gerekirse
   köşelerinden boyutlandır.
4. Models sekmesinde en az bir model oluşturup hangi ROI'lerin DOLU olması
   gerektiğini işaretle (isteğe bağlı: ROI başına özel eşik gir).
5. **Inspection**'ı aç, bandı/modeli seç, Başlat'a bas.

## Testler

```bash
python -m pytest tests/ -v
```

Core motorlar (ArUco lokalizasyon, karar mantığı, inspection loglama,
performans-kritik kırpma) ve yapılandırma modülleri (band/model/operatör
yönetimi, doğrulama, yedekleme, dışa/içe aktarma, loglama) için toplam
100'ün üzerinde birim testi vardır. `main` dalına her push/PR'da GitHub
Actions ile otomatik çalışır (`.github/workflows/tests.yml`).

## Proje Yapısı

```
apps/
  launcher.py          # Ana menü
  configurator.py       # Configurator giriş noktası
  inspection.py         # Inspection giriş noktası

modules/
  core/                 # UI'dan bağımsız çekirdek: ArUco, lokalizasyon,
                        # perspektif düzeltme, karşılaştırma, karar motoru,
                        # otomatik ROI tespiti, Arduino iletişimi
  configuration/         # Band/Model/Operatör yönetimi, inspection logger,
                        # doğrulama, yedekleme, NG kare kaydetme,
                        # Excel/zip dışa-içe aktarma
  controllers/           # Core motorları birleştiren, UI'dan bağımsız akış
  utils/                 # Logger (rotasyonlu), disk izleme, erişebilirlik
                        # ayarları, test çalıştırıcı
  ui/
    common/               # Uygulamalar arası ortak bileşenler (login,
                        # erişebilirlik ayarı, grafik widget'ları)
    configurator/         # Configurator ekranları
    inspection/           # Inspection ekranı, geçmiş/istatistik penceresi

configuration/
  band_XX/              # Her istasyon için: band.json, roi.json,
                        # reference.png, models/*.json
                        # (inspection_log.db, ng_captures/ çalışma zamanı
                        # verisidir, operators.json gizli bilgi içerir —
                        # hiçbiri git'e girmez)

tests/                  # Birim testleri
```

## Bağımlılıklar

- **PySide6** — arayüz
- **opencv-contrib-python** — ArUco algılama, görüntü işleme
- **numpy** — matris/vektör işlemleri
- **openpyxl** — Excel dışa aktarma
- **pyserial** — Arduino alarm entegrasyonu (demo)
- **pytest** — testler
