from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

IMAGES_URL_PREFIX = "/images"


def save_image(image_bytes: bytes, filename_stem: str) -> tuple[Path, str]:
    """Normalise any incoming image (jpeg/png/webp) to JPEG on disk and
    return (path, public_url) served via the /images static mount."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    path = (Path(__file__).resolve().parent.parent.parent / "data" / "images" / f"{filename_stem}.jpg")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "JPEG", quality=92)
    return path, f"{IMAGES_URL_PREFIX}/{path.name}"


def load_image_bytes(path: Path) -> bytes:
    return path.read_bytes()
