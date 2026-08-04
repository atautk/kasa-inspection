import cv2
import numpy as np


class InspectionEngine:

    MARGIN = 8

    # -------------------------------------------------
    # Polygon Crop
    # -------------------------------------------------

    def crop_polygon(self, image, points):

        if image is None:
            return np.array([])

        polygon = np.array(points, dtype=np.int32)

        x, y, w, h = cv2.boundingRect(polygon)

        x += self.MARGIN
        y += self.MARGIN

        w -= self.MARGIN * 2
        h -= self.MARGIN * 2

        x = max(0, x)
        y = max(0, y)

        w = min(w, image.shape[1] - x)
        h = min(h, image.shape[0] - y)

        if w <= 0 or h <= 0:

            return np.array([])

        # Önce (küçük) sınırlayıcı dikdörtgene kırp, maskeyi de sadece
        # bu kırpılmış bölge boyutunda oluştur - tüm görüntü boyutunda
        # maske + bitwise_and yapmak, özellikle küçük ROI'lerde
        # gereksiz yere pahalıydı (ölçüm: ~50x daha yavaş).

        cropped = image[y:y + h, x:x + w]

        local_polygon = polygon - [x, y]

        mask = np.zeros((h, w), dtype=np.uint8)

        cv2.fillPoly(mask, [local_polygon], 255)

        return cv2.bitwise_and(
            cropped,
            cropped,
            mask=mask
        )

    # -------------------------------------------------
    # Analyze (İleride AI için kullanılacak)
    # -------------------------------------------------

    def analyze(self, crop):

        gray = cv2.cvtColor(
            crop,
            cv2.COLOR_BGR2GRAY
        )

        blur = cv2.GaussianBlur(
            gray,
            (5, 5),
            0
        )

        mean = float(np.mean(blur))

        std = float(np.std(blur))

        edges = cv2.Canny(
            blur,
            75,
            150
        )

        edge_count = int(
            cv2.countNonZero(edges)
        )

        _, binary = cv2.threshold(
            blur,
            128,
            255,
            cv2.THRESH_BINARY
        )

        white_ratio = (

            cv2.countNonZero(binary)

            /

            binary.size

        ) * 100

        return {

            "mean": round(mean, 2),

            "std": round(std, 2),

            "edge_count": edge_count,

            "white_ratio": round(
                white_ratio,
                2
            )

        }

    # -------------------------------------------------
    # Preprocess
    # -------------------------------------------------

    def preprocess(self, image):

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        gray = cv2.GaussianBlur(
            gray,
            (9, 9),
            0
        )

        return gray

    # -------------------------------------------------
    # Difference
    # -------------------------------------------------

    def difference(
        self,
        reference_crop,
        current_crop
    ):

        reference = self.preprocess(
            reference_crop
        )

        current = self.preprocess(
            current_crop
        )

        diff = cv2.absdiff(
            reference,
            current
        )

        return diff

    # -------------------------------------------------
    # Threshold
    # -------------------------------------------------

    def threshold(self, diff):

        _, binary = cv2.threshold(

            diff,

            40,

            255,

            cv2.THRESH_BINARY

        )

        return binary

    # -------------------------------------------------
    # Morphology
    # -------------------------------------------------

    def morphology(
        self,
        binary
    ):

        kernel = np.ones(
            (3, 3),
            np.uint8
        )

        binary = cv2.morphologyEx(

            binary,

            cv2.MORPH_OPEN,

            kernel

        )

        binary = cv2.morphologyEx(

            binary,

            cv2.MORPH_CLOSE,

            kernel

        )

        return binary

    # -------------------------------------------------
    # Compare
    # -------------------------------------------------

    def compare(
        self,
        reference_crop,
        current_crop
    ):

        diff = self.difference(

            reference_crop,

            current_crop

        )

        binary = self.threshold(diff)

        binary = self.morphology(binary)

        changed = cv2.countNonZero(
            binary
        )

        total = (
            binary.shape[0]
            *
            binary.shape[1]
        )

        if total == 0:

            ratio = 0

        else:

            ratio = (

                changed

                /

                total

            ) * 100

        return {

            "reference": reference_crop,

            "current": current_crop,

            "difference": diff,

            "binary": binary,

            "changed_pixels": changed,

            "change_ratio": round(
                ratio,
                2
            )

        }