import cv2
import numpy as np


class ROIAutoDetector:
    """
    Referans fotoğrafındaki bölme çizgileriyle (kasa gözlerinin
    duvarları/kenarları) sınırlı kapalı hücreleri bularak otomatik
    ROI poligonları üretir.

    Yöntem: adaptif eşikleme ile çizgileri çıkarıp, kapalı hücreleri
    "delik" (contour hiyerarşisinde iç kontur) olarak yakalar. Bu,
    kasa gözleri arasında görünür duvar/çizgi olduğu sürece çalışır;
    tamamen düz, bölmesiz bir yüzeyde hücre bulamaz.
    """

    MIN_AREA_RATIO = 0.01
    MAX_AREA_RATIO = 0.35
    APPROX_EPSILON_RATIO = 0.02

    def detect(self, image: np.ndarray) -> list:

        if image is None:
            return []

        if image.ndim == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        height, width = gray.shape[:2]
        image_area = height * width

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        binary = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV,
            25,
            10
        )

        kernel = np.ones((5, 5), np.uint8)

        closed = cv2.morphologyEx(
            binary, cv2.MORPH_CLOSE, kernel, iterations=2
        )

        contours, hierarchy = cv2.findContours(
            closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )

        if hierarchy is None:
            return []

        hierarchy = hierarchy[0]

        candidates = []

        for i, contour in enumerate(contours):

            # Sadece kapalı "delik" konturlar = gerçek hücreler.
            if hierarchy[i][3] == -1:
                continue

            area = cv2.contourArea(contour)
            area_ratio = area / image_area

            if area_ratio < self.MIN_AREA_RATIO:
                continue

            if area_ratio > self.MAX_AREA_RATIO:
                continue

            perimeter = cv2.arcLength(contour, True)

            approx = cv2.approxPolyDP(
                contour, self.APPROX_EPSILON_RATIO * perimeter, True
            )

            if len(approx) != 4:
                continue

            if not cv2.isContourConvex(approx):
                continue

            points = [
                [float(p[0][0]), float(p[0][1])]
                for p in approx
            ]

            candidates.append(points)

        return self._sort_reading_order(candidates)

    # -------------------------------------------------
    # Okuma Sırası (yukarıdan aşağı, soldan sağa)
    # -------------------------------------------------

    def _sort_reading_order(self, candidates: list) -> list:

        if not candidates:
            return []

        items = []

        heights = []

        for points in candidates:

            xs = [p[0] for p in points]
            ys = [p[1] for p in points]

            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)

            heights.append(max(ys) - min(ys))

            items.append((cx, cy, points))

        row_threshold = max(sorted(heights)[len(heights) // 2] / 2, 10)

        items.sort(key=lambda item: item[1])

        rows = []

        for cx, cy, points in items:

            placed = False

            for row in rows:

                if abs(row["y"] - cy) < row_threshold:

                    row["items"].append((cx, points))
                    placed = True
                    break

            if not placed:
                rows.append({"y": cy, "items": [(cx, points)]})

        ordered = []

        for row in rows:

            row["items"].sort(key=lambda item: item[0])

            for _, points in row["items"]:
                ordered.append(points)

        return ordered
