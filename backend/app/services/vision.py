"""Gemini vision-judgement calls.

Three judgement calls share one pattern: send an image (or images) plus a
prompt that demands strict JSON back, parse it defensively, and fall back to
a safe "reject" if the model output can't be parsed. Used for:
  1. frontage "fit" scoring during venue selection (services/fit.py)
  2. frontage-image usability scoring during capture (services/frontage.py)
  3. composite QA / rejection criteria (services/compositing.py)
"""
from __future__ import annotations

import json
import logging
import re

from google import genai
from google.genai import types

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=get_settings().gemini_api_key)
    return _client


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).rsplit("```", 1)[0].strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output: {text[:200]!r}")
    return json.loads(match.group(0))


def judge_json(
    prompt: str,
    images: list[tuple[bytes, str]],
    *,
    default_on_error: dict,
) -> dict:
    """Send prompt + images to Gemini, expect a JSON object back.

    images: list of (raw_bytes, mime_type). default_on_error is returned
    (never raised) if the call or parse fails, so a flaky vision call always
    resolves to a reject-shaped result rather than crashing the pipeline.
    """
    settings = get_settings()
    parts = [types.Part.from_bytes(data=data, mime_type=mime) for data, mime in images]
    parts.append(types.Part.from_text(text=prompt))

    try:
        response = _get_client().models.generate_content(
            model=settings.gemini_vision_model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(temperature=0.1),
        )
        return _extract_json(response.text or "")
    except Exception:
        logger.exception("Gemini vision judgement call failed; defaulting to reject")
        return default_on_error


FIT_PROMPT = """You are screening street-facing venue photos for an outdoor-planter \
sales prospecting tool. The client sells design-led planters to independent cafes, \
restaurants and salons whose entrances are bare or under-dressed.

Venue name: {name}
Venue type: {venue_type}

Look at the attached photo of this venue's frontage/entrance and answer strictly as JSON:
{{
  "is_street_facing_entrance": true/false,
  "frontage_is_bare_or_underdressed": true/false,
  "planters_would_visibly_help": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "one or two sentences, specific to what you see"
}}

Reject (frontage_is_bare_or_underdressed=false) if the frontage already has substantial \
greenery/planting, is not actually street-facing (e.g. a mall unit, a food court stall), \
or the photo doesn't show the entrance at all. Only JSON, no other text."""


def judge_frontage_fit(image_bytes: bytes, mime: str, name: str, venue_type: str) -> dict:
    default = {
        "is_street_facing_entrance": False,
        "frontage_is_bare_or_underdressed": False,
        "planters_would_visibly_help": False,
        "confidence": 0.0,
        "reasoning": "Vision judgement call failed; defaulting to reject.",
    }
    return judge_json(
        FIT_PROMPT.format(name=name, venue_type=venue_type),
        [(image_bytes, mime)],
        default_on_error=default,
    )


USABILITY_PROMPT = """You are quality-checking a candidate frontage photo for "{name}", \
before it gets used as the base image for a product-compositing pipeline sent to venue \
owners. At 5,000+ venues/week this check runs unattended, so be strict and literal.

Answer strictly as JSON:
{{
  "shows_entrance_clearly": true/false,
  "reasonably_front_on": true/false,
  "unobstructed": true/false,
  "usable": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "one or two sentences"
}}

usable must be true only if shows_entrance_clearly, reasonably_front_on, and unobstructed \
are all true. Reject photos that are heavily angled/side-on, mostly blocked by people, \
vehicles or scaffolding, too dark/blurry to read the doorway, or that show the wrong \
building entirely. Only JSON, no other text."""


def judge_frontage_usability(image_bytes: bytes, mime: str, name: str) -> dict:
    default = {
        "shows_entrance_clearly": False,
        "reasonably_front_on": False,
        "unobstructed": False,
        "usable": False,
        "confidence": 0.0,
        "reasoning": "Vision judgement call failed; defaulting to reject.",
    }
    return judge_json(USABILITY_PROMPT.format(name=name), [(image_bytes, mime)], default_on_error=default)


QA_PROMPT = """You are the final automated quality gate before a composited "planters \
installed" image is sent to a venue owner as a sales visual. Compare the ORIGINAL frontage \
photo (first image) against the COMPOSITED result (second image), which should show the \
same building with the client's planter product ("{product_name}") added near the entrance.

Answer strictly as JSON:
{{
  "building_unaltered": true/false,
  "product_matches_reference": true/false,
  "scale_plausible": true/false,
  "perspective_plausible": true/false,
  "has_grounding_and_shadow": true/false,
  "no_visual_artifacts": true/false,
  "accepted": true/false,
  "reasoning": "two or three sentences explaining the verdict, specific to this image"
}}

accepted must be true only if ALL other checks are true. Reject if: the building facade, \
signage, windows or door were altered or warped; the planter looks like a generic AI \
plant rather than matching the reference product's container shape/material/colour; the \
planter is obviously too large/small for the doorway; it floats, clips through geometry, \
or lacks a contact shadow; or there are warped edges, duplicated geometry, or other \
artifacts. This gate exists so nothing embarrassing reaches a venue owner — be strict. \
Only JSON, no other text."""


ENTRANCE_PROMPT = """Look at this street-facing venue photo for "{name}". Find the main \
entrance door/doorway, tight to its frame — this is used to crop the photo in closer around \
the entrance for a sales visual, so precision matters. Answer strictly as JSON using integer \
coordinates on a 0-1000 scale (0=left/top edge of the image, 1000=right/bottom edge) - a \
normalized coordinate space, NOT pixels:
{{
  "entrance_visible": true/false,
  "left": 0-1000,
  "top": 0-1000,
  "right": 0-1000,
  "bottom": 0-1000,
  "confidence": 0.0-1.0,
  "reasoning": "one sentence"
}}
left/top/right/bottom is the tight bounding box of the entrance door itself (frame to frame, \
threshold to lintel), not the whole building. Set entrance_visible to false if no doorway is \
clearly visible. Only JSON, no other text."""


def detect_entrance(image_bytes: bytes, mime: str, name: str) -> dict:
    default = {
        "entrance_visible": False,
        "confidence": 0.0,
        "reasoning": "Vision judgement call failed; defaulting to no detection.",
    }
    return judge_json(ENTRANCE_PROMPT.format(name=name), [(image_bytes, mime)], default_on_error=default)


def judge_composite_quality(
    original_bytes: bytes,
    original_mime: str,
    composite_bytes: bytes,
    composite_mime: str,
    product_name: str,
) -> dict:
    default = {
        "building_unaltered": False,
        "product_matches_reference": False,
        "scale_plausible": False,
        "perspective_plausible": False,
        "has_grounding_and_shadow": False,
        "no_visual_artifacts": False,
        "accepted": False,
        "reasoning": "Vision judgement call failed; defaulting to reject.",
    }
    return judge_json(
        QA_PROMPT.format(product_name=product_name),
        [(original_bytes, original_mime), (composite_bytes, composite_mime)],
        default_on_error=default,
    )
