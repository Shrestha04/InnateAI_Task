from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import IMAGES_DIR, get_settings
from app.routers import demo, pipeline, products

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title="Storefront Planter Prospecting API",
    description="Discovers under-dressed London venue frontages, captures a usable entrance photo, and composites the client's planters onto it.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(pipeline.router)
app.include_router(products.router)
app.include_router(demo.router)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "mapillary_token_configured": bool(settings.mapillary_token),
        "gemini_key_configured": bool(settings.gemini_api_key),
    }
