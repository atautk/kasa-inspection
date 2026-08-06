from dataclasses import dataclass, field
from pathlib import Path

from .camera_channel import CameraChannel


@dataclass(slots=True)
class Band:
    id: str
    name: str
    root: Path

    reference: Path
    roi: Path
    models: Path

    camera: int = 0
    threshold: float = 3.0
    arduino_port: str = ""
    version: str = "1.0"

    # Kamera titremesi/geçici gürültü nedeniyle OK<->NG durumu tek bir
    # karede yanlışlıkla değişebilir. Bir değişikliğin loglanıp
    # bildirilmesi için bu kadar ardışık karede tutarlı kalması
    # gerekir - bkz. InspectionLogger.
    confirm_frames: int = 3

    # Aynı kasayı farklı açılardan izleyen EK kameralar. Birincil
    # kamera (camera/reference/roi alanları) burada YER ALMAZ - bu
    # sayede tek kameralı bandlar hiç değişmeden çalışmaya devam eder.
    cameras: list = field(default_factory=list)

    # Vardiya bazlı üretim takibi: bir vardiyada üretilmesi beklenen
    # kasa sayısı ve vardiyanın kaç saat sürdüğü. 0 = kapalı (hiç
    # takip/uyarı yapılmaz) - bkz. InspectionUIController.
    shift_target_count: int = 0
    shift_duration_hours: float = 8.0

    # Kamera netliği uyarısı: Laplacian varyansı bu değerin altına
    # düşerse görüntü "bulanık" sayılır - bkz. BlurDetector.
    blur_threshold: float = 100.0

    # Referans fotoğrafı yaşlanma hatırlatıcısı: reference.png (ve
    # varsa ek kamera kanallarının referansları) bu kadar gündür
    # yenilenmediyse hatırlat - ışık/kamera koşulları zamanla
    # kayabilir. 0 = kapalı.
    reference_max_age_days: int = 0

    # Açıksa, her onaylı log olayında ROI bazında referans/canlı
    # kırpma görüntü çiftleri diske kaydedilir (ileride bir görüntü
    # sınıflandırma modeli eğitmek için) - bkz. TrainingDataManager.
    # Varsayılan kapalı: yeni bir disk kullanım davranışı, bilinçli
    # olarak açılmalı.
    training_data_collection_enabled: bool = False