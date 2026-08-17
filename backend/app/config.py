from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Free-tier Mapillary client token: https://www.mapillary.com/dashboard/developers
    # (no credit card required). Venue discovery itself needs no key (OpenStreetMap
    # Overpass API + Nominatim).
    mapillary_token: str = ""
    gemini_api_key: str = ""

    # Search area: central London, ~ covers Zone 1-2
    search_lat: float = 51.5074
    search_lng: float = -0.1278
    search_radius_m: int = 4000

    # gemini-2.5-flash is deprecated for new projects as of writing; -lite is
    # confirmed working for both text-only and image+text input on the free
    # tier. Image *generation* models (below) have a 0/day free-tier quota
    # on every project regardless of model version — compositing requires a
    # billed Gemini project, there's no free-tier path around it.
    gemini_vision_model: str = "gemini-3.1-flash-lite"
    gemini_image_model: str = "gemini-3.1-flash-image"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    return settings
