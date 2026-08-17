"""Orchestrates frontage capture for one venue: try Mapillary frames first,
fall back to an OSM-tagged photo, then the venue website's og:image. Every
attempt is scored by the automated usability check in services/vision.py —
nothing here is manually eyeballed. See design.md "Getting the frontage
image" for the full writeup.

Once a usable frame is found, a second vision call locates the entrance
door itself and the frame is cropped/zoomed tight around it (see
_zoom_to_entrance below) — the doorway, not the whole facade, is what a
venue owner actually needs to see and what compositing scales against.
"""
from __future__ import annotations

import io
import logging

from PIL import Image

from app.schemas import FrontageAttempt, FrontageResult, VenueCandidate
from app.services import fallback_images, image_store, mapillary, osm, vision

logger = logging.getLogger(__name__)

ENTRANCE_MIN_CONFIDENCE = 0.5
TARGET_ASPECT = 4 / 3
MIN_CROP_WIDTH_PX = 1024


def _zoom_to_entrance(image_bytes: bytes, entrance: dict) -> bytes:
    """Crop a wide frontage frame down to a tighter shot around the
    detected entrance bounding box (0-1000 normalized coords), padded for
    context and fitted to a 4:3 frame, then upscaled if the crop is small."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = image.size

    left = entrance["left"] / 1000 * w
    top = entrance["top"] / 1000 * h
    right = entrance["right"] / 1000 * w
    bottom = entrance["bottom"] / 1000 * h
    box_w = max(right - left, 1.0)
    box_h = max(bottom - top, 1.0)

    # Pad around the door so the crop keeps some context (frame, threshold,
    # pavement either side) rather than showing just the door itself.
    pad_x = box_w * 0.9
    crop_left = left - pad_x
    crop_right = right + pad_x
    crop_top = top - box_h * 0.35
    crop_bottom = bottom + box_h * 0.9

    # Fit to a 4:3 frame (matches the UI's display aspect) by growing the
    # shorter dimension around its own centre.
    cur_w = crop_right - crop_left
    cur_h = crop_bottom - crop_top
    if cur_w / cur_h > TARGET_ASPECT:
        extra = (cur_w / TARGET_ASPECT - cur_h) / 2
        crop_top -= extra
        crop_bottom += extra
    else:
        extra = (cur_h * TARGET_ASPECT - cur_w) / 2
        crop_left -= extra
        crop_right += extra

    crop_box = (
        int(max(0, crop_left)),
        int(max(0, crop_top)),
        int(min(w, crop_right)),
        int(min(h, crop_bottom)),
    )
    cropped = image.crop(crop_box)

    if cropped.width < MIN_CROP_WIDTH_PX:
        scale = MIN_CROP_WIDTH_PX / cropped.width
        cropped = cropped.resize((int(cropped.width * scale), int(cropped.height * scale)), Image.LANCZOS)

    out = io.BytesIO()
    cropped.save(out, format="JPEG", quality=92)
    return out.getvalue()


def _apply_entrance_zoom(venue: VenueCandidate, image_bytes: bytes, result: FrontageResult) -> FrontageResult:
    entrance = vision.detect_entrance(image_bytes, "image/jpeg", venue.name)
    if not entrance.get("entrance_visible") or entrance.get("confidence", 0) < ENTRANCE_MIN_CONFIDENCE:
        return result

    try:
        zoomed_bytes = _zoom_to_entrance(image_bytes, entrance)
    except Exception:
        logger.exception("Entrance zoom crop failed for %s; keeping the wide frontage frame", venue.venue_id)
        return result

    stem = f"{venue.venue_id.replace('/', '_')}_frontage_{result.final_source}_entrance"
    path, url = image_store.save_image(zoomed_bytes, stem)
    result.image_path = str(path)
    result.image_url = url
    result.entrance_zoomed = True
    result.entrance_confidence = entrance.get("confidence")
    entrance_reasoning = entrance.get("reasoning", "")
    result.reasoning = f"{result.reasoning} Cropped tighter to the detected entrance: {entrance_reasoning}"
    return result


async def _try_source(
    venue: VenueCandidate,
    source: str,
    image_bytes: bytes,
    *,
    heading: float | None = None,
    fov: float | None = None,
    image_ref: str | None = None,
) -> tuple[FrontageAttempt, FrontageResult | None]:
    verdict = vision.judge_frontage_usability(image_bytes, "image/jpeg", venue.name)
    usable = bool(verdict.get("usable"))
    attempt = FrontageAttempt(
        source=source,
        accepted=usable,
        reasoning=verdict.get("reasoning", ""),
        heading_deg=heading,
        fov_deg=fov,
        image_ref=image_ref,
    )
    if not usable:
        return attempt, None

    stem = f"{venue.venue_id.replace('/', '_')}_frontage_{source}"
    path, url = image_store.save_image(image_bytes, stem)
    attempt.image_path = str(path)
    result = FrontageResult(
        venue_id=venue.venue_id,
        accepted=True,
        final_source=source,
        image_path=str(path),
        image_url=url,
        heading_deg=heading,
        fov_deg=fov,
        reasoning=verdict.get("reasoning", ""),
    )
    result = _apply_entrance_zoom(venue, image_bytes, result)
    return attempt, result


async def capture_frontage(venue: VenueCandidate) -> FrontageResult:
    attempts: list[FrontageAttempt] = []

    # 1. Mapillary: nearby frames ranked by how closely their capture
    #    heading already matches the bearing toward the venue.
    frames = await mapillary.candidate_frames(venue.lat, venue.lng)
    for image_bytes, heading, fov, image_ref in frames:
        attempt, result = await _try_source(venue, "mapillary", image_bytes, heading=heading, fov=fov, image_ref=image_ref)
        attempts.append(attempt)
        if result:
            result.attempts = attempts
            return result

    # 2. OSM-tagged photo (image/wikimedia_commons tag), when present.
    if venue.osm_photo_url:
        image_bytes = await osm.fetch_osm_photo_bytes(venue.osm_photo_url)
        if image_bytes:
            attempt, result = await _try_source(venue, "osm_photo", image_bytes)
            attempts.append(attempt)
            if result:
                result.attempts = attempts
                return result

    # 3. Venue website og:image, last resort.
    if venue.website:
        image_bytes = await fallback_images.fetch_website_og_image(venue.website)
        if image_bytes:
            attempt, result = await _try_source(venue, "website_og", image_bytes)
            attempts.append(attempt)
            if result:
                result.attempts = attempts
                return result

    return FrontageResult(
        venue_id=venue.venue_id,
        accepted=False,
        reasoning="No usable frontage image found across Mapillary, OSM photo, and the venue website.",
        attempts=attempts,
    )
