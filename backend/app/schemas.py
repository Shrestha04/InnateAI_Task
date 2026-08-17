from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VenueType(str, Enum):
    cafe = "cafe"
    restaurant = "restaurant"
    salon = "salon"
    other = "other"


class VenueCandidate(BaseModel):
    venue_id: str  # OSM "node/12345" / "way/12345" style id
    name: str
    address: str | None = None
    postcode: str | None = None
    lat: float
    lng: float
    venue_type: VenueType
    osm_tags: dict[str, str] = Field(default_factory=dict)
    website: str | None = None
    osm_photo_url: str | None = None  # OSM `image`/`wikimedia_commons` tag, if present


class FitVerdict(BaseModel):
    accepted: bool
    score: float = Field(ge=0, le=1)
    reasoning: str
    signals: dict[str, str] = Field(default_factory=dict)


class ScoredVenue(BaseModel):
    venue: VenueCandidate
    fit: FitVerdict


class FrontageAttempt(BaseModel):
    source: str  # "mapillary" | "osm_photo" | "website_og"
    accepted: bool
    reasoning: str
    image_path: str | None = None
    heading_deg: float | None = None
    fov_deg: float | None = None
    image_ref: str | None = None  # source-specific image id, e.g. Mapillary image id


class FrontageResult(BaseModel):
    venue_id: str
    accepted: bool
    final_source: str | None = None
    image_path: str | None = None
    image_url: str | None = None
    heading_deg: float | None = None
    fov_deg: float | None = None
    reasoning: str
    entrance_zoomed: bool = False
    entrance_confidence: float | None = None
    attempts: list[FrontageAttempt] = Field(default_factory=list)


class Product(BaseModel):
    id: str
    name: str
    description: str
    image_path: str
    image_url: str
    reference_height_m: float
    reference_note: str
    visual_height_m: float  # container + planting, tallest point in the reference photo


class CompositeAttempt(BaseModel):
    attempt_number: int
    image_path: str | None
    image_url: str | None
    accepted: bool
    reasoning: str
    checks: dict[str, bool] = Field(default_factory=dict)


class CompositeResult(BaseModel):
    venue_id: str
    product_id: str
    accepted: bool
    method: str = "gemini"  # "gemini" | "classical" — which backend produced final_image
    final_image_path: str | None = None
    final_image_url: str | None = None
    reasoning: str
    scale_note: str
    attempts: list[CompositeAttempt] = Field(default_factory=list)


class VenuePipelineResult(BaseModel):
    venue: VenueCandidate
    fit: FitVerdict
    frontage: FrontageResult | None = None
    composite: CompositeResult | None = None
    product: Product | None = None


class PipelineRunResult(BaseModel):
    requested_count: int
    candidates_considered: int
    rejected_venues: list[ScoredVenue] = Field(default_factory=list)
    results: list[VenuePipelineResult] = Field(default_factory=list)
