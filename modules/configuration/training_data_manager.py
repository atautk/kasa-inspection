import shutil
from datetime import datetime
from pathlib import Path

import cv2


class TrainingDataManager:
    """
    Her ROI için referans/canlı kırpma görüntü çiftini, kural tabanlı
    sistemin o anda okuduğu görsel duruma (DOLU/BOŞ) göre klasörleyerek
    diske kaydeder. Amaç: ileride bir görüntü sınıflandırma modeli
    eğitmek için insan gözetiminde büyüyen bir veri seti biriktirmek.

    Klasör yapısı - herhangi bir görüntü sınıflandırma eğitim scripti
    tarafından doğrudan (klasör adı = etiket) okunabilecek şekilde:

        band_XX/training_data/<ROI_ADI>/<DURUM>/<zaman>_reference.png
        band_XX/training_data/<ROI_ADI>/<DURUM>/<zaman>_current.png

    Sadece onaylı (debounce'dan geçmiş) log olaylarında çağrılır, her
    karede değil - bkz. InspectionUIController._tick_impl.

    Bir operatör düzeltmesi (correct_roi) geldiğinde OTOMATİK yeniden
    etiketleme YAPILMAZ - bir düzeltme görsel tespit hatası da olabilir,
    model yapılandırma farkı da olabilir; ikisini koddan ayırt edemeyiz.
    Bunun yerine flag_for_review() ile "elle gözden geçirilmeli" işareti
    bırakılır.
    """

    FOLDER_NAME = "training_data"

    # "Yeterlilik" için kaba bir kural - küçük/kontrollü bir ikili
    # (DOLU/BOŞ) görüntü sınıflandırma görevi için genel kabul gören
    # kalın çizgiler. Görüntü çeşitliliğine ve seçilecek model
    # mimarisine göre gerçek ihtiyaç değişir - bu KESİN bir bilimsel
    # eşik değil, sadece "hâlâ çok erken" ile "denemeye başlanabilir"
    # arasını ayırt etmeye yarayan bir gösterge.
    INSUFFICIENT_THRESHOLD = 50
    LOW_THRESHOLD = 200
    ADEQUATE_THRESHOLD = 500

    SUFFICIENCY_LABELS = {
        "none": "Veri yok",
        "insufficient": "Çok az",
        "low": "Az",
        "moderate": "Makul",
        "adequate": "Yeterli"
    }

    # -------------------------------------------------

    def save(
        self,
        band,
        roi_name: str,
        state: str,
        reference_crop,
        current_crop
    ) -> dict:

        if reference_crop is None or current_crop is None:
            return None

        folder = band.root / self.FOLDER_NAME / roi_name / state
        folder.mkdir(parents=True, exist_ok=True)

        base_name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        reference_path = folder / f"{base_name}_reference.png"
        current_path = folder / f"{base_name}_current.png"

        counter = 1

        while current_path.exists():

            reference_path = folder / f"{base_name}_{counter}_reference.png"
            current_path = folder / f"{base_name}_{counter}_current.png"

            counter += 1

        cv2.imwrite(str(reference_path), reference_crop)
        cv2.imwrite(str(current_path), current_crop)

        return {
            "reference": str(reference_path),
            "current": str(current_path)
        }

    # -------------------------------------------------

    def flag_for_review(self, image_paths: dict):
        """
        image_paths: save()'in döndürdüğü {"reference": ..., "current": ...}
        sözlüğü. current dosyasının yanına boş bir .flagged_for_review
        dosyası bırakır - ileride veri seti kürasyonu yapılırken bu
        örneklerin elle kontrol edilmesi gerektiğini işaretler.
        """

        if not image_paths:
            return

        current_path = image_paths.get("current")

        if not current_path:
            return

        flag_path = Path(current_path).with_suffix(".flagged_for_review")
        flag_path.touch(exist_ok=True)

    # -------------------------------------------------
    # Toplanan Veri Özeti
    # -------------------------------------------------

    def compute_summary(self, band) -> dict:
        """
        {roi_name: {state: {"count": N, "flagged": M}}} döner.
        count: kaydedilmiş örnek (referans+canlı çifti) sayısı.
        flagged: bunlardan kaçının bir operatör düzeltmesi sonrası
        "elle gözden geçirilmeli" işaretlendiği.
        """

        folder = band.root / self.FOLDER_NAME

        summary = {}

        if not folder.exists():
            return summary

        for roi_folder in sorted(folder.iterdir()):

            if not roi_folder.is_dir():
                continue

            roi_name = roi_folder.name
            summary[roi_name] = {}

            for state_folder in sorted(roi_folder.iterdir()):

                if not state_folder.is_dir():
                    continue

                state = state_folder.name

                count = len(list(state_folder.glob("*_current.png")))
                flagged = len(
                    list(state_folder.glob("*.flagged_for_review"))
                )

                summary[roi_name][state] = {
                    "count": count,
                    "flagged": flagged
                }

        return summary

    # -------------------------------------------------

    def assess_sufficiency(self, count: int) -> str:
        """
        count: bir ROI için düşünülen sınıflardan EN AZ örneğe sahip
        olanın sayısı (darboğaz sınıf) - bu sayede hem toplam hacim
        hem de sınıf dengesizliği tek bir göstergeye yansır.
        """

        if count <= 0:
            return self.SUFFICIENCY_LABELS["none"]

        if count < self.INSUFFICIENT_THRESHOLD:
            return self.SUFFICIENCY_LABELS["insufficient"]

        if count < self.LOW_THRESHOLD:
            return self.SUFFICIENCY_LABELS["low"]

        if count < self.ADEQUATE_THRESHOLD:
            return self.SUFFICIENCY_LABELS["moderate"]

        return self.SUFFICIENCY_LABELS["adequate"]

    # -------------------------------------------------

    def clear(self, band):

        shutil.rmtree(band.root / self.FOLDER_NAME, ignore_errors=True)
