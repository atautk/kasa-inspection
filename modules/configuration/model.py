from dataclasses import dataclass, field


@dataclass(slots=True)
class Model:

    id: str
    name: str

    expected_rois: list[str]

    version: str = "1.0"

    # ROI adı -> bu model için özel değişim eşiği (%). Burada
    # olmayan ROI'ler bandın genel eşiğini kullanır.
    roi_thresholds: dict = field(default_factory=dict)