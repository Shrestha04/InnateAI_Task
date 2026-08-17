"""Free, local, non-AI compositing fallback.

Used automatically when the Gemini image-generation model isn't available
(free-tier keys return zero image-generation quota — see design.md
"Compositing the planters" for the full story). This produces a real
result — the actual product cutout, scaled from the same doorway-height
reference math as the AI path — but it is honestly a cutout-and-shadow
paste, not photorealistic generation: no perspective warp, no physically
simulated relighting. It exists so the pipeline always produces *something*
inspectable, with that limitation surfaced rather than hidden.

Pipeline:
  1. Gemini vision (free, text-output) locates the door bounding box and a
     ground-level placement point, in Gemini's native 0-1000 coordinate
     space (see _DOOR_PROMPT).
  2. Door pixel height + the same UK-doorway-height assumption used by the
     Gemini path gives real-world metres-per-pixel for this photo.
  3. rembg (local U^2-Net-family segmentation, no API) cuts the product out
     of its reference photo.
  4. The cutout is scaled to the product's known visual_height_m using that
     metres-per-pixel figure, then pasted at the detected ground point with
     a soft synthetic drop shadow.
"""
from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFilter

from app.products import Product
from app.schemas import CompositeAttempt
from app.services import image_store, vision

logger = logging.getLogger(__name__)

UK_DOOR_HEIGHT_M = 2.04
REMBG_MODEL = "isnet-general-use"

_rembg_session = None


def _get_rembg_session():
    global _rembg_session
    if _rembg_session is None:
        import onnxruntime
        from rembg import new_session

        # onnxruntime's default CPU memory arena pre-allocates and never
        # shrinks, so RSS grows by ~650MB on every single remove() call and
        # never comes back down (verified: two calls back-to-back took the
        # process past 1.6GB). Disabling the arena/mem-pattern trades a
        # little inference speed for a flat ~380MB footprint regardless of
        # call count — necessary to fit in a 512MB free-tier container.
        sess_opts = onnxruntime.SessionOptions()
        sess_opts.enable_cpu_mem_arena = False
        sess_opts.enable_mem_pattern = False
        _rembg_session = new_session(REMBG_MODEL, sess_opts=sess_opts)
    return _rembg_session


DOOR_PROMPT = """Look at this street-facing building photo. Find the main entrance door.
Answer strictly as JSON using integer coordinates on a 0-1000 scale (0=left/top edge of the
image, 1000=right/bottom edge of the image) - this is a normalized coordinate space, NOT pixels:
{
  "door_visible": true/false,
  "door_top": 0-1000,
  "door_bottom": 0-1000,
  "ground_placement_x": 0-1000,
  "ground_placement_y": 0-1000,
  "reasoning": "..."
}
door_top/door_bottom is the tight vertical bounding box of the door itself (frame to frame),
door_bottom should sit right at the ground/threshold level. ground_placement_x/y is a point
on the pavement/ground immediately beside the door (left or right, whichever has clear open
space), where a planter could realistically stand - y should be the ground level at that spot
(may differ slightly from door_bottom due to camera perspective)."""


def _detect_door(frontage_bytes: bytes) -> dict:
    default = {"door_visible": False}
    return vision.judge_json(DOOR_PROMPT, [(frontage_bytes, "image/jpeg")], default_on_error=default)


def _cutout_product(product_bytes: bytes) -> Image.Image:
    import io

    from rembg import remove

    product_img = Image.open(io.BytesIO(product_bytes))
    cutout = remove(product_img, session=_get_rembg_session())
    bbox = cutout.getbbox()
    if bbox:
        cutout = cutout.crop(bbox)
    return cutout


def composite_classical(frontage_bytes: bytes, product: Product, attempt_number: int, venue_id: str) -> CompositeAttempt:
    import io

    door = _detect_door(frontage_bytes)
    if not door.get("door_visible"):
        return CompositeAttempt(
            attempt_number=attempt_number,
            image_path=None,
            image_url=None,
            accepted=False,
            reasoning="Classical fallback: no door detected in the frontage photo to anchor scale/placement.",
        )

    frontage = Image.open(io.BytesIO(frontage_bytes)).convert("RGB")
    w, h = frontage.size

    door_top_px = door["door_top"] / 1000 * h
    door_bottom_px = door["door_bottom"] / 1000 * h
    door_height_px = max(door_bottom_px - door_top_px, 1.0)
    meters_per_px = UK_DOOR_HEIGHT_M / door_height_px
    target_height_px = max(int(product.visual_height_m / meters_per_px), 10)

    ground_x = int(door["ground_placement_x"] / 1000 * w)
    ground_y = int(door["ground_placement_y"] / 1000 * h)

    product_bytes = open(product.image_path, "rb").read()
    cutout = _cutout_product(product_bytes)

    scale = target_height_px / cutout.height
    target_width_px = max(int(cutout.width * scale), 1)
    cutout_resized = cutout.resize((target_width_px, target_height_px), Image.LANCZOS)

    shadow_layer = Image.new("RGBA", frontage.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_w = int(target_width_px * 0.9)
    shadow_h = max(6, int(target_height_px * 0.12))
    shadow_draw.ellipse(
        [ground_x - shadow_w // 2, ground_y - shadow_h // 2, ground_x + shadow_w // 2, ground_y + shadow_h // 2],
        fill=(0, 0, 0, 130),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(4, shadow_h // 2)))

    canvas = frontage.convert("RGBA")
    canvas.alpha_composite(shadow_layer)
    paste_x = ground_x - target_width_px // 2
    paste_y = ground_y - target_height_px
    canvas.alpha_composite(cutout_resized, (paste_x, paste_y))

    out_bytes_io = io.BytesIO()
    canvas.convert("RGB").save(out_bytes_io, format="JPEG", quality=92)

    stem = f"{venue_id.replace('/', '_')}_composite_{product.id}_classical_attempt{attempt_number}"
    path, url = image_store.save_image(out_bytes_io.getvalue(), stem)

    return CompositeAttempt(
        attempt_number=attempt_number,
        image_path=str(path),
        image_url=url,
        accepted=True,
        reasoning=(
            "Classical cutout-and-shadow fallback (Gemini image generation unavailable on this key's "
            "tier): real product cutout, scaled from the detected doorway height, placed at a "
            "vision-detected ground point with a synthetic shadow. Not photorealistic AI compositing — "
            "no perspective warp or physically simulated relighting. Door detection: "
            f"{door.get('reasoning', '')}"
        ),
        checks={"method_classical_fallback": True},
    )
