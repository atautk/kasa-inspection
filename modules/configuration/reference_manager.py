from __future__ import annotations

import cv2
from pathlib import Path

from .band import Band


class ReferenceManager:

    # -------------------------------------------------

    def exists(self, target) -> bool:

        if isinstance(target, Band):
            return target.reference.exists()

        return Path(target).exists()

    # -------------------------------------------------

    def load(self, target):

        if isinstance(target, Band):
            filename = target.reference
        else:
            filename = Path(target)

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

        if isinstance(target, Band):
            filename = target.reference
        else:
            filename = Path(target)

        cv2.imwrite(
            str(filename),
            image
        )

    # -------------------------------------------------

    def delete(self, target):

        if isinstance(target, Band):
            filename = target.reference
        else:
            filename = Path(target)

        if filename.exists():
            filename.unlink()

    # -------------------------------------------------

    def replace(self, target, image):

        self.delete(target)

        self.save(target, image)