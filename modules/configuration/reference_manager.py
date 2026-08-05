from __future__ import annotations

import cv2
from pathlib import Path


class ReferenceManager:
    """
    target: Band, CameraChannel veya doğrudan bir Path/str olabilir.
    Band ve CameraChannel'ın ikisi de bir "reference" Path alanına
    sahip - hangi tür olduğuna bakmaksızın onu kullanırız (duck
    typing). Böylece birincil kamera (Band) ve ek kamera kanalları
    (CameraChannel) aynı kod yoluyla çalışır.
    """

    # -------------------------------------------------

    def _resolve(self, target) -> Path:

        reference = getattr(target, "reference", None)

        if reference is not None:
            return reference

        return Path(target)

    # -------------------------------------------------

    def exists(self, target) -> bool:

        return self._resolve(target).exists()

    # -------------------------------------------------

    def load(self, target):

        filename = self._resolve(target)

        if not filename.exists():
            return None

        image = cv2.imread(str(filename))

        if image is None:
            raise RuntimeError(
                f"Reference okunamadı : {filename}"
            )

        return image

    # -------------------------------------------------

    def save(self, target, image):

        filename = self._resolve(target)

        cv2.imwrite(
            str(filename),
            image
        )

    # -------------------------------------------------

    def delete(self, target):

        filename = self._resolve(target)

        if filename.exists():
            filename.unlink()

    # -------------------------------------------------

    def replace(self, target, image):

        self.delete(target)

        self.save(target, image)