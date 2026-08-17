"""Populate the Results showcase page the same way the real app would:
discover independent restaurants via OSM, run each through the actual
frontage-capture pipeline (Mapillary -> OSM photo -> website fallback,
usability gate, entrance zoom), and keep the first 5 that succeed.

Not part of the app runtime — run manually.
"""
from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import VenueType  # noqa: E402
from app.services import frontage, osm  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "results"
TARGET = 5


def slugify(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


async def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    candidates = await osm.discover_venues(max_results=60)
    restaurants = [v for v in candidates if v.venue_type == VenueType.restaurant and not osm.is_chain(v.name)]
    print(f"{len(restaurants)} independent restaurant candidates from OSM")

    saved = 0
    for venue in restaurants:
        if saved >= TARGET:
            break
        print(f"\n=== {venue.name} ({venue.address}) ===")
        result = await frontage.capture_frontage(venue)
        print(f"  accepted={result.accepted} source={result.final_source} entrance_zoomed={result.entrance_zoomed}")
        if result.accepted and result.image_path:
            slug = slugify(venue.name)
            dest = RESULTS_DIR / f"{slug}-before.jpg"
            shutil.copy(result.image_path, dest)
            print(f"  saved -> {dest}")
            saved += 1
        else:
            print(f"  skip: {result.reasoning}")

    print(f"\nSaved {saved}/{TARGET}")


if __name__ == "__main__":
    asyncio.run(main())
