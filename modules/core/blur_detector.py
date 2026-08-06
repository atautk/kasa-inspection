import cv2


class BlurDetector:
    """
    Laplacian varyansı yöntemiyle bir görüntünün net mi bulanık mı
    olduğunu tespit eder. Görüntüdeki kenarlar keskinse (odak doğru,
    kamera temiz) varyans yüksek çıkar; görüntü bulanıksa (odak
    kaymış, lens kirli/buğulu, kamera titriyor) varyans düşük çıkar.

    Yanlış NG tespitlerinin bir kısmı aslında kamera netliğiyle
    ilgili olabilir - bu erkenden fark edilip operatöre bildirilsin
    diye kullanılır (bkz. InspectionUIController._maybe_check_blur).
    """

    def compute_sharpness(self, image) -> float:

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
