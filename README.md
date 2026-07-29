# Kasa Inspection

ArUco marker tabanlı hizalama ile çalışan, kamera görüntüsünden ürün üzerindeki
gözlerin (ROI) dolu/boş durumunu tespit eden bir kalite kontrol sistemi.
PySide6 (Qt) tabanlı iki uygulamadan oluşur: **Configurator** (kurulum) ve
**Inspection** (canlı kontrol).

## Özellikler

**Configurator**
- Band (istasyon) oluşturma, listeleme, doğrulama
- Kamera ile referans görüntü çekimi (ArUco ile otomatik hizalama)
- Sürüklenebilir polygon tabanlı ROI editörü
- Model yönetimi — her model için beklenen ROI durumları (dolu/boş)
- Değişim eşiği (hassasiyet) ayarı
- Band'ı `.zip` olarak dışa/içe aktarma (başka bir makineye taşımak için)

**Inspection**
- Band/model seçip canlı kontrolü başlatma
- ArUco ile otomatik hizalama, karede karede ROI karşılaştırma
- NG (hatalı) durumunda görsel banner + sesli uyarı
- Inspection geçmişi: her OK/NG geçişi SQLite'a (`inspection_log.db`) loglanır,
  NG anındaki kare otomatik kaydedilir
- Geçmiş penceresi: kayıt tablosu, ROI bazında detay, tek tek ROI düzeltme
  (yanlış tespiti işaretleyip düzeltme), istatistikler (model/ROI bazında
  OK-NG oranı), Excel'e aktarma

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

İlk kullanımda Configurator'dan bir band oluşturup (kamera, referans fotoğraf,
ROI'ler, en az bir model) tamamlaman gerekir; Inspection o bandı seçip
çalıştırır.

## Testler

Core motorlar (ArUco lokalizasyon, karar mantığı, inspection loglama) için
birim testleri:

```bash
python -m pytest tests/ -v
```

## Proje Yapısı

```
apps/
  launcher.py        # Ana menü
  configurator.py     # Configurator giriş noktası
  inspection.py       # Inspection giriş noktası

modules/
  core/               # UI'dan bağımsız çekirdek: ArUco, lokalizasyon,
                      # perspektif düzeltme, karşılaştırma, karar motoru
  configuration/       # Band/Model/Reference yönetimi, inspection logger,
                      # NG kare kaydetme, Excel/zip dışa-içe aktarma
  controllers/         # Core motorları birleştiren, UI'dan bağımsız akış
  ui/
    configurator/      # Configurator ekranları
    inspection/         # Inspection ekranı, geçmiş/istatistik penceresi

configuration/
  band_XX/            # Her istasyon için: band.json, roi.json,
                      # reference.png, models/*.json
                      # (inspection_log.db ve ng_captures/ çalışma zamanı
                      # verisidir, git'e girmez)

tests/                # Birim testleri
```

## Bağımlılıklar

- **PySide6** — arayüz
- **opencv-contrib-python** — ArUco algılama, görüntü işleme
- **numpy** — matris/vektör işlemleri
- **openpyxl** — Excel dışa aktarma
- **pytest** — testler
