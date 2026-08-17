"""Product compositing via Gemini image generation, plus the automated
rejection gate. See design.md "Compositing the planters" for the reasoning
behind the scale-anchor prompt and the rejection criteria.

Falls back to services/classical_compositing.py (a free, local, non-AI
cutout-and-shadow method) when Gemini can't generate an image at all —
see that module's docstring for why and its limitations.
"""
from __future__ import annotations

import logging
from pathlib import Path

from google import genai
from google.genai import types

from app.config import get_settings
from app.products import Product
from app.schemas import CompositeAttempt, CompositeResult, FrontageResult
from app.services import classical_compositing, image_store, vision

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2
UK_DOOR_HEIGHT_M = "1.98-2.10"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=get_settings().gemini_api_key)
    return _client


COMPOSITE_PROMPT = """You are compositing a real product photo into a real street-facing \
venue frontage photo for a sales visual. Precision and photorealism matter — this will be \
shown to the venue owner as "what your entrance could look like."

Image 1 is the venue frontage (the scene). Image 2 is the client's actual planter product \
photograph (the reference object) — "{product_name}": {product_description}

Task: add the exact planter product shown in Image 2 into Image 2's real position — placed \
naturally on the ground immediately beside the entrance in Image 1, wherever there is clear \
pavement space closest to the doorway.

Scale: use the doorway visible in Image 1 as your real-world scale reference — a UK commercial \
door is typically {door_height}m tall. The product's container is approximately \
{product_height}m tall ({product_note}). Scale the planter so its proportions relative to the \
doorway match these real measurements exactly — do not guess a generic size.

Fidelity: keep the planter's container material, colour, shape and the plants/foliage \
identical to Image 2. Do not invent a different container or generic plant — reuse the exact \
product shown.

Integration: match the lighting direction, colour temperature and camera perspective already \
present in Image 1. Add a believable contact shadow grounding the planter to the pavement. \
Do not alter the building facade, signage, windows, door, brickwork, people, vehicles, or any \
other element of Image 1 — only add the planter.

Output the final composited photo as a single image."""


def build_composite_prompt(product: Product) -> str:
    """The default prompt used by the automated pipeline. Exposed publicly
    so the manual demo playground (routers/demo.py) can show it as an
    editable starting point rather than duplicating it."""
    return COMPOSITE_PROMPT.format(
        product_name=product.name,
        product_description=product.description,
        door_height=UK_DOOR_HEIGHT_M,
        product_height=product.reference_height_m,
        product_note=product.reference_note,
    )


def _generate(frontage_bytes: bytes, frontage_mime: str, product_bytes: bytes, product_mime: str, prompt: str) -> tuple[bytes, str] | None:
    settings = get_settings()
    parts = [
        types.Part.from_bytes(data=frontage_bytes, mime_type=frontage_mime),
        types.Part.from_bytes(data=product_bytes, mime_type=product_mime),
        types.Part.from_text(text=prompt),
    ]
    try:
        response = _get_client().models.generate_content(
            model=settings.gemini_image_model,
            contents=[types.Content(role="user", parts=parts)],
        )
        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    return part.inline_data.data, part.inline_data.mime_type or "image/png"
        logger.warning("Gemini image generation returned no inline image data")
        return None
    except Exception:
        logger.exception("Gemini image generation call failed")
        return None


def _scale_note(product: Product) -> str:
    return (
        f"Scaled against a {UK_DOOR_HEIGHT_M}m doorway reference; "
        f"product container ~{product.reference_height_m}m ({product.reference_note})"
    )


async def composite_for_venue(frontage: FrontageResult, product: Product) -> CompositeResult:
    frontage_bytes = Path(frontage.image_path).read_bytes()
    product_bytes = Path(product.image_path).read_bytes()

    attempts: list[CompositeAttempt] = []
    any_image_generated = False

    prompt = build_composite_prompt(product)
    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        generated = _generate(frontage_bytes, "image/jpeg", product_bytes, "image/jpeg", prompt)
        if generated is None:
            attempts.append(CompositeAttempt(
                attempt_number=attempt_number,
                image_path=None,
                image_url=None,
                accepted=False,
                reasoning="Image generation call failed or returned no image.",
            ))
            continue

        any_image_generated = True
        composite_bytes, composite_mime = generated
        stem = f"{frontage.venue_id}_composite_{product.id}_attempt{attempt_number}"
        path, url = image_store.save_image(composite_bytes, stem)

        qa = vision.judge_composite_quality(frontage_bytes, "image/jpeg", composite_bytes, composite_mime, product.name)
        checks = {k: bool(v) for k, v in qa.items() if isinstance(v, bool)}
        accepted = bool(qa.get("accepted"))

        attempts.append(CompositeAttempt(
            attempt_number=attempt_number,
            image_path=str(path),
            image_url=url,
            accepted=accepted,
            reasoning=qa.get("reasoning", ""),
            checks=checks,
        ))

        if accepted:
            return CompositeResult(
                venue_id=frontage.venue_id,
                product_id=product.id,
                accepted=True,
                method="gemini",
                final_image_path=str(path),
                final_image_url=url,
                reasoning=qa.get("reasoning", ""),
                scale_note=_scale_note(product),
                attempts=attempts,
            )

    # Only fall back to the classical (non-AI) path when Gemini could not
    # generate an image at all across every attempt — e.g. a free-tier key
    # with no image-generation quota. A generation that Gemini *produced*
    # but the QA gate rejected is a real quality reject, not a capability
    # gap, so it stays rejected rather than silently swapping methods.
    if not any_image_generated:
        classical_attempt = classical_compositing.composite_classical(
            frontage_bytes, product, attempt_number=len(attempts) + 1, venue_id=frontage.venue_id
        )
        attempts.append(classical_attempt)
        if classical_attempt.accepted:
            return CompositeResult(
                venue_id=frontage.venue_id,
                product_id=product.id,
                accepted=True,
                method="classical",
                final_image_path=classical_attempt.image_path,
                final_image_url=classical_attempt.image_url,
                reasoning=classical_attempt.reasoning,
                scale_note=_scale_note(product),
                attempts=attempts,
            )

    return CompositeResult(
        venue_id=frontage.venue_id,
        product_id=product.id,
        accepted=False,
        reasoning=f"Rejected after {len(attempts)} attempt(s): {attempts[-1].reasoning if attempts else 'no attempts recorded'}",
        scale_note=_scale_note(product),
        attempts=attempts,
    )


async def generate_demo_composite(frontage_bytes: bytes, product: Product, prompt: str) -> dict:
    """One-shot manual generation for the demo playground (routers/demo.py):
    a single Gemini attempt with a user-editable prompt, QA-scored for
    information but not gated on it — the point of the playground is to see
    what a given prompt actually produces, not to enforce the pipeline's
    accept bar. Falls back to the classical method (ignoring the custom
    prompt, which only applies to the Gemini path) if Gemini can't
    generate at all, same as the automated pipeline.
    """
    product_bytes = Path(product.image_path).read_bytes()
    generated = _generate(frontage_bytes, "image/jpeg", product_bytes, "image/jpeg", prompt)

    if generated is not None:
        composite_bytes, composite_mime = generated
        stem = f"demo_{product.id}_{abs(hash(prompt)) % 10_000_000}"
        path, url = image_store.save_image(composite_bytes, stem)
        qa = vision.judge_composite_quality(frontage_bytes, "image/jpeg", composite_bytes, composite_mime, product.name)
        checks = {k: bool(v) for k, v in qa.items() if isinstance(v, bool)}
        return {
            "method": "gemini",
            "qa_passed": bool(qa.get("accepted")),
            "image_url": url,
            "reasoning": qa.get("reasoning", ""),
            "checks": checks,
            "prompt_used": prompt,
        }

    classical_attempt = classical_compositing.composite_classical(frontage_bytes, product, attempt_number=1, venue_id="demo")
    return {
        "method": "classical",
        "qa_passed": classical_attempt.accepted,
        "image_url": classical_attempt.image_url,
        "reasoning": classical_attempt.reasoning,
        "checks": classical_attempt.checks,
        "prompt_used": None,
    }
