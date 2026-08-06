import traceback


class FrameProcessor:

    # Bu iki köşenin marker ID'leri TÜM modellerde sabittir (sadece
    # geometri/perspektif için). Bunların dışındaki HERHANGİ bir
    # marker "sol-üst tanı marker'ı" adayı sayılır - hangi modelin
    # (varsa) o ID'ye sahip olduğuna bakılmaksızın, sadece 0 nolu
    # köşe rolüne (LocalizationEngine'in beklediği) genel/model-
    # bağımsız şekilde eşlenir. Bu sayede localization.py'ye HİÇ
    # dokunulmadan hem bilinen hem de henüz tanımlanmamış (bilinmeyen)
    # kasalar normal şekilde lokalize edilebilir.
    RESERVED_CORNER_IDS = {1, 2, 3}

    def __init__(
        self,
        aruco,
        localizer,
        reference_frame
    ):
        self.aruco = aruco
        self.localizer = localizer
        self.reference_frame = reference_frame

    # -------------------------------------------------
    # Frame İşleme
    # -------------------------------------------------

    def process(self, frame):

        if frame is None:

            return {

                "success": False,

                "error": "Frame is None",

                "frame": None,

                "markers": {},

                "identity_marker_id": None,

                "localization": None,

                "reference": None

            }

        try:

            markers = self.aruco.detect(frame)

            identity_marker_id = self._select_identity_marker(markers)

            mapped_markers = markers

            if identity_marker_id not in (None, 0):

                mapped_markers = dict(markers)
                mapped_markers[0] = mapped_markers.pop(identity_marker_id)

            localization = self.localizer.update(
                mapped_markers
            )

            reference = None

            if localization["frame_corners"] is not None:

                reference = self.reference_frame.generate(

                    frame,

                    localization["frame_corners"]

                )

            return {

                "success": True,

                "error": None,

                "frame": frame,

                "markers": markers,

                "identity_marker_id": identity_marker_id,

                "localization": localization,

                "reference": reference

            }

        except Exception as e:

            traceback.print_exc()

            return {

                "success": False,

                "error": str(e),

                "frame": frame,

                "markers": {},

                "identity_marker_id": None,

                "localization": None,

                "reference": None

            }

    # -------------------------------------------------

    def _select_identity_marker(self, markers):
        """
        1/2/3 dışında görülen marker ID'lerinden birini "sol-üst tanı
        marker'ı" adayı olarak seçer. Böyle bir marker yoksa None
        döner (sıradan RECOVERY/ESTIMATE/FAIL davranışı bozulmaz).
        Birden fazla aday varsa (nadir - gürültü ya da iki kasa aynı
        anda görünüyor) en büyük (kameraya en yakın/güvenilir olan)
        tercih edilir.
        """

        candidates = [
            marker_id for marker_id in markers
            if marker_id not in self.RESERVED_CORNER_IDS
        ]

        if not candidates:
            return None

        if len(candidates) > 1:

            candidates.sort(
                key=lambda marker_id: markers[marker_id].area,
                reverse=True
            )

        return candidates[0]