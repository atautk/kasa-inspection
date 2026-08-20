from dataclasses import dataclass, field
from pathlib import Path

from .camera_channel import CameraChannel
from .shift_window import ShiftWindow


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

    # Vardiya pencereleri: kullanıcının tanımladığı, gün içindeki
    # sabit saat aralıkları (ör. "Sabah" 07:30-15:30). Üretim hedefi/
    # tempo takibi YOK - sadece pencere içinde kaç kasa incelendiğini
    # gösterir (bkz. ShiftTrackingMixin) ve istatistiklerdeki vardiya
    # bazlı NG trendini bu pencerelere göre gruplar (bkz.
    # InspectionLogger.compute_shift_trend). Boş liste = kapalı.
    shifts: list = field(default_factory=list)

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

    # Otomatik yedekleme: açıksa, inspection_log.db + ng_captures/
    # periyodik olarak auto_backup_destination'a kopyalanır - bkz.
    # BackupManager, InspectionUIController._maybe_run_auto_backup.
    # keep_count kadar en son yedek tutulur, gerisi otomatik silinir
    # (0 = temizlik yapma, sınırsız birikir).
    auto_backup_enabled: bool = False
    auto_backup_destination: str = ""
    auto_backup_interval_hours: float = 24.0
    auto_backup_keep_count: int = 30
    last_auto_backup_at: str = ""