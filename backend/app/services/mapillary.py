"""Frontage framing via Mapillary street-level imagery (free tier, Street
View replacement — see design.md "Getting the frontage image").

Unlike Street View's rotatable panoramas, most Mapillary coverage is a
corpus of fixed-perspective photographs, each already captured facing a
particular compass direction (`compass_angle`). So instead of *requesting*
an arbitrary heading, we *search* nearby images and rank them by how close
their capture heading already is to the bearing from that image's position
to the venue — i.e. we look for a photo that was already facing roughly the
right way, falling back to the next-closest if the ideal one doesn't exist.
Panoramic (`is_pano`) captures are skipped: reprojecting an equirectangular
pano to a directional crop is a real feature, just out of scope here.
"""
from __future__ import annotations

import logging
import math

import httpx

from app.config import get_settings

GRAPH_URL = "https://graph.mapillary.com/images"

SEARCH_RADIUS_M = 60
# Mapillary's public fields don't expose a precise per-image field of view;
# ~75deg is a reasonable assumption for typical dashcam/action-cam capture
# rigs that make up most of its coverage. See design.md limitations.
ASSUMED_FOV = 75.0
MAX_CANDIDATES = 3
# How far (degrees) an image's capture heading may be from the ideal
# venue-facing bearing before we stop considering it a "facing it" shot —
# still tried, just ranked behind closer matches.
HEADING_TOLERANCE_DEG = 70

logger = logging.getLogger(__name__)


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    x = math.sin(delta_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def _angular_diff(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def _bbox_around(lat: float, lng: float, radius_m: int) -> str:
    dlat = radius_m / 111_320
    dlng = radius_m / (111_320 * math.cos(math.radians(lat)) or 1)
    # Mapillary bbox order: west,south,east,north (lon,lat,lon,lat)
    return f"{lng - dlng},{lat - dlat},{lng + dlng},{lat + dlat}"


async def _search_images(lat: float, lng: float) -> list[dict]:
    settings = get_settings()
    if not settings.mapillary_token:
        return []
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                GRAPH_URL,
                params={
                    "access_token": settings.mapillary_token,
                    "fields": "id,geometry,compass_angle,computed_compass_angle,is_pano,thumb_2048_url",
                    "bbox": _bbox_around(lat, lng, SEARCH_RADIUS_M),
                    "limit": 30,
                },
            )
            if resp.status_code != 200:
                logger.warning("Mapillary search failed: %s %s", resp.status_code, resp.text[:200])
                return []
            return resp.json().get("data", [])
    except Exception:
        logger.exception("Mapillary search request failed for %s,%s", lat, lng)
        return []


def _ranked_candidates(images: list[dict], venue_lat: float, venue_lng: float) -> list[dict]:
    ranked = []
    for image in images:
        if image.get("is_pano"):
            continue
        geometry = image.get("geometry")
        if not geometry or geometry.get("type") != "Point":
            continue
        img_lng, img_lat = geometry["coordinates"]
        heading = image.get("computed_compass_angle", image.get("compass_angle"))
        if heading is None:
            continue
        bearing_to_venue = _bearing_deg(img_lat, img_lng, venue_lat, venue_lng)
        diff = _angular_diff(heading, bearing_to_venue)
        ranked.append({**image, "_heading": heading, "_diff": diff})
    ranked.sort(key=lambda i: i["_diff"])
    return ranked


async def _fetch_thumb(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            return resp.content
    except Exception:
        logger.exception("Failed to fetch Mapillary thumbnail")
        return None


async def candidate_frames(lat: float, lng: float) -> list[tuple[bytes, float, float, str]]:
    """Yield (image_bytes, heading, fov, image_id) for the best-matching
    nearby Mapillary images, closest-facing first."""
    images = await _search_images(lat, lng)
    ranked = _ranked_candidates(images, lat, lng)[:MAX_CANDIDATES]

    frames = []
    for image in ranked:
        thumb_url = image.get("thumb_2048_url")
        if not thumb_url:
            continue
        image_bytes = await _fetch_thumb(thumb_url)
        if image_bytes:
            frames.append((image_bytes, float(image["_heading"]), ASSUMED_FOV, image["id"]))
    return frames


async def fetch_default_frame(lat: float, lng: float) -> bytes | None:
    """Single best-guess frame for the cheap fit-scoring pass (no retries)."""
    images = await _search_images(lat, lng)
    ranked = _ranked_candidates(images, lat, lng)
    if not ranked:
        return None
    thumb_url = ranked[0].get("thumb_2048_url")
    if not thumb_url:
        return None
    return await _fetch_thumb(thumb_url)
