"""Combine rule-based signals with a Gemini vision judgement to decide which
discovered venues are actually good candidates: independent, street-facing,
with a bare/under-dressed frontage that planters would visibly improve.

See design.md "Choosing your venues" for the accept/reject bar in prose.
"""
from __future__ import annotations

from app.schemas import FitVerdict, VenueCandidate, VenueType
from app.services import mapillary, osm, vision

ACCEPT_THRESHOLD = 0.55

ALLOWED_TYPES = {VenueType.cafe, VenueType.restaurant, VenueType.salon}


def _rule_reject(venue: VenueCandidate) -> FitVerdict | None:
    """Cheap, auditable rule-based rejects — checked before any vision call
    so a chain or an address-less listing never costs a Gemini request, and
    still shows up (with its reason) in the rejected-candidates list rather
    than silently vanishing at the discovery stage."""
    if osm.is_chain(venue.name):
        return FitVerdict(
            accepted=False,
            score=0.0,
            reasoning=f"'{venue.name}' matches a known chain — excluded in favour of independents.",
            signals={"rule:chain": "reject"},
        )

    if venue.venue_type not in ALLOWED_TYPES:
        return FitVerdict(
            accepted=False,
            score=0.0,
            reasoning=f"Venue type '{venue.venue_type}' is outside cafe/restaurant/salon scope.",
            signals={"rule:type": "reject"},
        )

    if not venue.address or not venue.postcode:
        return FitVerdict(
            accepted=False,
            score=0.0,
            reasoning="Could not resolve a street address and postcode for this venue (OSM tags incomplete, Nominatim reverse-geocode also failed).",
            signals={"rule:address": "reject"},
        )

    return None


async def _best_effort_image(venue: VenueCandidate) -> tuple[bytes, str] | None:
    """Grab whatever image we can cheaply get to make a fit judgement: an
    OSM-tagged photo first (already attached to this venue specifically),
    falling back to the best-matching nearby Mapillary frame."""
    if venue.osm_photo_url:
        image_bytes = await osm.fetch_osm_photo_bytes(venue.osm_photo_url)
        if image_bytes:
            return image_bytes, "image/jpeg"

    frame = await mapillary.fetch_default_frame(venue.lat, venue.lng)
    if frame:
        return frame, "image/jpeg"

    return None


async def score_venue(venue: VenueCandidate) -> FitVerdict:
    rule_reject = _rule_reject(venue)
    if rule_reject is not None:
        return rule_reject

    image = await _best_effort_image(venue)
    if image is None:
        return FitVerdict(
            accepted=False,
            score=0.1,
            reasoning="No OSM photo or Mapillary frame available to assess the frontage.",
            signals={"rule:chain": "pass", "rule:type": "pass", "rule:address": "pass", "image_available": "false"},
        )

    image_bytes, mime = image
    verdict = vision.judge_frontage_fit(image_bytes, mime, venue.name, venue.venue_type.value)

    confidence = float(verdict.get("confidence", 0.0))
    is_fit = bool(
        verdict.get("is_street_facing_entrance")
        and verdict.get("frontage_is_bare_or_underdressed")
        and verdict.get("planters_would_visibly_help")
    )
    score = confidence if is_fit else min(confidence, 0.4)

    return FitVerdict(
        accepted=is_fit and score >= ACCEPT_THRESHOLD,
        score=score,
        reasoning=verdict.get("reasoning", ""),
        signals={
            "rule:chain": "pass",
            "rule:type": "pass",
            "rule:address": "pass",
            "vision:street_facing": str(verdict.get("is_street_facing_entrance")),
            "vision:bare_frontage": str(verdict.get("frontage_is_bare_or_underdressed")),
            "vision:planters_would_help": str(verdict.get("planters_would_visibly_help")),
        },
    )
