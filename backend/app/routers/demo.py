"""Manual compositing playground: upload a frontage photo, pick a product,
edit the Gemini prompt, and see the result directly — separate from the
automated pipeline, for experimenting with the compositing prompt itself.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.products import PRODUCTS_BY_ID
from app.services import compositing, image_store

router = APIRouter(prefix="/api/demo", tags=["demo"])


class PromptTemplateResponse(BaseModel):
    product_id: str
    prompt: str


@router.get("/prompt-template", response_model=PromptTemplateResponse)
async def get_prompt_template(product_id: str) -> PromptTemplateResponse:
    product = PRODUCTS_BY_ID.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Unknown product_id '{product_id}'")
    return PromptTemplateResponse(product_id=product_id, prompt=compositing.build_composite_prompt(product))


class DemoGenerateResponse(BaseModel):
    frontage_image_url: str
    product_id: str
    method: str
    qa_passed: bool
    image_url: str | None
    reasoning: str
    checks: dict[str, bool]
    prompt_used: str | None


@router.post("/generate", response_model=DemoGenerateResponse)
async def generate(
    frontage: UploadFile,
    product_id: str = Form(...),
    prompt: str | None = Form(None),
) -> DemoGenerateResponse:
    product = PRODUCTS_BY_ID.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Unknown product_id '{product_id}'")

    frontage_bytes = await frontage.read()
    if not frontage_bytes:
        raise HTTPException(status_code=400, detail="Empty upload")

    stem = f"demo_frontage_{abs(hash(frontage_bytes)) % 10_000_000}"
    _, frontage_url = image_store.save_image(frontage_bytes, stem)

    final_prompt = prompt or compositing.build_composite_prompt(product)

    try:
        result = await compositing.generate_demo_composite(frontage_bytes, product, final_prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc

    return DemoGenerateResponse(
        frontage_image_url=frontage_url,
        product_id=product_id,
        method=result["method"],
        qa_passed=result["qa_passed"],
        image_url=result["image_url"],
        reasoning=result["reasoning"],
        checks=result["checks"],
        prompt_used=result["prompt_used"],
    )
