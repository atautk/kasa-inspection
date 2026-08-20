from dataclasses import dataclass


@dataclass(slots=True)
class ShiftWindow:
    """
    Sabit bir vardiya penceresi (ör. "Sabah" 07:30-15:30). Üretim
    hedefi/tempo takibi YOK - sadece pencere içinde kaç kasa
    incelendiğini göstermek (bkz. ShiftTrackingMixin) ve
    istatistiklerdeki vardiya bazlı NG trendini bu pencerelere göre
    gruplamak (bkz. InspectionLogger.compute_shift_trend) için
    kullanılır.
    """

    id: str
    name: str
    start: str  # "HH:MM"
    end: str    # "HH:MM"
    operator: str = ""  # bu vardiyada çalışan operatörün adı, "" = atanmamış
