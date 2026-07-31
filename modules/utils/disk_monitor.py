import shutil
from pathlib import Path


def get_free_space_gb(path) -> float:
    """
    Verilen yoldaki (ya da en yakın var olan üst klasördeki) diskte
    kalan boş alanı GB cinsinden döndürür.
    """

    path = Path(path)

    while not path.exists():

        parent = path.parent

        if parent == path:
            break

        path = parent

    usage = shutil.disk_usage(path)

    return usage.free / (1024 ** 3)
