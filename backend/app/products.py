"""Client product catalogue for the prototype.

Three reference photos, taken directly from the client's own product
photography (see design.md). reference_height_m is the real-world height
we assume for that product's tallest container, used as the scale anchor
when prompting the compositing model — see services/compositing.py.
"""
from __future__ import annotations

from pathlib import Path

from app.schemas import Product

STATIC_PRODUCTS_DIR = Path(__file__).resolve().parent / "static" / "products"

PRODUCTS: list[Product] = [
    Product(
        id="black-cylinder",
        name="Cylinder planter, matte black",
        description=(
            "Large matte-black cylindrical planter, dense mixed evergreen and "
            "architectural foliage planting. Reads well against most facade colours."
        ),
        image_path=str(STATIC_PRODUCTS_DIR / "planter-black-cylinder.jpg"),
        image_url="/static/products/planter-black-cylinder.jpg",
        reference_height_m=0.55,
        reference_note="Container height ~0.55m; planting reaches ~1.1m overall.",
        visual_height_m=1.1,
    ),
    Product(
        id="corten-modular",
        name="Corten steel modular planters",
        description=(
            "Weathered corten-steel modular planter set (tall cube + low cube), "
            "small palm and seasonal red/pink flowering planting."
        ),
        image_path=str(STATIC_PRODUCTS_DIR / "planter-corten-modular.jpg"),
        image_url="/static/products/planter-corten-modular.jpg",
        reference_height_m=0.9,
        reference_note="Tall module ~0.9m; low module ~0.45m; palm adds ~0.8m above container.",
        visual_height_m=1.7,
    ),
    Product(
        id="white-cube",
        name="Cube planters, matte white",
        description=(
            "Pair of matte-white cube planters, compact flowering and evergreen "
            "planting. Suits lighter, minimal shopfronts."
        ),
        image_path=str(STATIC_PRODUCTS_DIR / "planter-white-cube.jpg"),
        image_url="/static/products/planter-white-cube.jpg",
        reference_height_m=0.45,
        reference_note="Container height ~0.45m; planting reaches ~0.9m overall.",
        visual_height_m=0.9,
    ),
]

PRODUCTS_BY_ID = {p.id: p for p in PRODUCTS}


def pick_product_for_venue(venue_type: str) -> Product:
    """Simple deterministic default so every venue gets a plausible product
    without a human picking one; a real system would let the client choose
    per-venue or score fit against facade colour/width."""
    if venue_type == "salon":
        return PRODUCTS_BY_ID["white-cube"]
    if venue_type == "restaurant":
        return PRODUCTS_BY_ID["corten-modular"]
    return PRODUCTS_BY_ID["black-cylinder"]
