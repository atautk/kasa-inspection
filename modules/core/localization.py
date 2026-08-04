import numpy as np


class LocalizationEngine:

    REQUIRED_MARKERS = [0, 1, 2, 3]

    # Kareler arası titreşimi (jitter) azaltmak için üstel hareketli
    # ortalama (EMA) katsayısı. Düşük değer = daha yumuşak ama gerçek
    # harekete tepkisi daha yavaş; yüksek değer = ham veriye daha yakın.
    SMOOTHING_ALPHA = 0.35

    # "Otomatik yeniden kalibrasyon": markerlar kaybolup NORMAL moda
    # geri dönüldüğünde, tek bir (gürültülü olabilecek) kareye hemen
    # tam güvenmek yerine, kilidin "oturduğunu" kabul etmeden önce bu
    # kadar ardışık NORMAL kare bekleriz.
    SETTLE_FRAMES = 3

    def __init__(self):

        self.last_frame_corners = None
        self.smoothed_corners = None
        self.normal_streak = 0

    # -------------------------------------------------

    def update(self, markers):

        visible = sum(
            marker in markers
            for marker in self.REQUIRED_MARKERS
        )

        mode = self._get_mode(visible)

        self.normal_streak = (
            self.normal_streak + 1 if mode == "NORMAL" else 0
        )

        frame_corners = self._build_frame(markers)

        if frame_corners is not None:

            self.last_frame_corners = frame_corners.copy()

            # Ham konumu kaydettikten SONRA yumuşat - RECOVERY'nin
            # kullandığı last_frame_corners hâlâ ham (smoothing'siz)
            # kalsın, sadece dışarı verilen sonuç yumuşatılsın.
            frame_corners = self._smooth(frame_corners)

        elif visible >= 2:

            # RECOVERY/ESTIMATE: en az 2 marker görünüyor ama bu kare
            # için henüz hesaplanmış bir konum yoksa (ör. ilk kare),
            # son bilinen konumu kullan.
            frame_corners = self.last_frame_corners

        else:

            # FAIL: markerlar (dolayısıyla kasa) tamamen kayboldu.
            # Eski konumu kullanma - kasa geri geldiğinde eski
            # konumla karışmasın diye hafızayı ve yumuşatma durumunu
            # da temizle (aksi halde yeniden kalibrasyon, kaybolmadan
            # önceki konuma doğru yumuşatılmış olur).
            self.last_frame_corners = None
            self.smoothed_corners = None
            frame_corners = None

        return {

            "mode": mode,

            "visible": visible,

            "confidence": self.get_confidence(visible),

            "frame_corners": frame_corners,

            # Kilit yeni oturdu mu (ardışık SETTLE_FRAMES NORMAL kare)
            # yoksa henüz yeniden kalibre mi oluyor?
            "settled": self.normal_streak >= self.SETTLE_FRAMES

        }

    # -------------------------------------------------

    def _smooth(self, corners):

        corners = np.asarray(corners, dtype=np.float32)

        if self.smoothed_corners is None:

            self.smoothed_corners = corners.copy()

        else:

            self.smoothed_corners = (
                self.SMOOTHING_ALPHA * corners
                + (1 - self.SMOOTHING_ALPHA) * self.smoothed_corners
            ).astype(np.float32)

        return self.smoothed_corners.copy()

    # -------------------------------------------------

    def _build_frame(self, markers):

        # ---------- NORMAL ----------

        if all(marker in markers for marker in self.REQUIRED_MARKERS):

            return np.float32([

                markers[0].corners[0],

                markers[1].corners[1],

                markers[2].corners[3],

                markers[3].corners[2]

            ])

        # ---------- FAIL: kurtarmaya yetecek kadar marker yok ----------

        visible = sum(
            marker in markers
            for marker in self.REQUIRED_MARKERS
        )

        if visible < 2:
            return None

        # ---------- RECOVERY / ESTIMATE ----------

        if self.last_frame_corners is None:
            return None

        corners = self.last_frame_corners.copy()

        if 0 in markers:
            corners[0] = markers[0].corners[0]

        if 1 in markers:
            corners[1] = markers[1].corners[1]

        if 2 in markers:
            corners[2] = markers[2].corners[3]

        if 3 in markers:
            corners[3] = markers[3].corners[2]

        return corners

    # -------------------------------------------------

    def _get_mode(self, visible):

        if visible == 4:
            return "NORMAL"

        if visible == 3:
            return "RECOVERY"

        if visible == 2:
            return "ESTIMATE"

        return "FAIL"

    # -------------------------------------------------

    def get_confidence(self, visible):

        table = {

            4: 100,

            3: 90,

            2: 70,

            1: 20,

            0: 0

        }

        return table.get(visible, 0)