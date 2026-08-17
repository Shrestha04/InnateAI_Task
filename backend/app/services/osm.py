"""Venue discovery via OpenStreetMap — free, keyless.

Overpass supplies raw venue nodes/ways (name, type, address tags, and
sometimes a photo/website tag); Nominatim fills in address/postcode where
OSM's own tags are incomplete, which is common for small independents. See
design.md "Choosing venues" for the full rationale.
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
import re

import httpx

from app.config import get_settings
from app.schemas import VenueCandidate, VenueType

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

# OSM tag (key, value) pairs to search, mapped to our venue_type.
OSM_QUERIES: list[tuple[str, str, VenueType]] = [
    ("amenity", "cafe", VenueType.cafe),
    ("amenity", "restaurant", VenueType.restaurant),
    ("shop", "hairdresser", VenueType.salon),
    ("shop", "beauty", VenueType.salon),
]

CHAIN_BLOCKLIST = {
    "starbucks", "costa coffee", "costa", "caffe nero", "nero",
    "pret a manger", "pret", "greggs", "mcdonald's", "mcdonalds",
    "burger king", "kfc", "subway", "pizza express", "wagamama",
    "itsu", "leon", "eat.", "byron", "five guys", "nando's", "nandos",
    "toni & guy", "toni and guy", "regis", "supercuts",
}

UK_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE)

# Identifying User-Agent required by Nominatim's usage policy.
OSM_REQUEST_HEADERS = {"User-Agent": "innate-ai-storefront-prospecting-prototype/0.1 (contact: dev@theasynclabs.com)"}


def _normalize(name: str) -> str:
    """Lowercase and strip spaces/punctuation so blocklist matching isn't
    fooled by formatting differences like "PizzaExpress" vs "Pizza Express"."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def is_chain(name: str) -> bool:
    normalized = _normalize(name)
    return any(_normalize(chain) in normalized for chain in CHAIN_BLOCKLIST)


def _bbox_from_center(lat: float, lng: float, radius_m: int) -> tuple[float, float, float, float]:
    """Return (south, west, north, east) for Overpass's bbox filter."""
    dlat = radius_m / 111_320
    dlng = radius_m / (111_320 * math.cos(math.radians(lat)) or 1)
    return (lat - dlat, lng - dlng, lat + dlat, lng + dlng)


def _build_overpass_query(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    bbox_str = f"{south},{west},{north},{east}"
    clauses = "\n".join(
        f'  node["{key}"="{value}"]({bbox_str});\n  way["{key}"="{value}"]({bbox_str});'
        for key, value, _ in OSM_QUERIES
    )
    return f"[out:json][timeout:25];\n(\n{clauses}\n);\nout center tags;"


def _address_from_tags(tags: dict[str, str]) -> str | None:
    parts = [tags.get("addr:housenumber"), tags.get("addr:street")]
    parts = [p for p in parts if p]
    if not parts:
        return None
    line = " ".join(parts)
    if tags.get("addr:city"):
        line += f", {tags['addr:city']}"
    if tags.get("addr:postcode"):
        line += f", {tags['addr:postcode']}"
    return line


def _photo_url_from_tags(tags: dict[str, str]) -> str | None:
    if tags.get("image", "").startswith("http"):
        return tags["image"]
    commons = tags.get("wikimedia_commons")
    if commons and commons.startswith("File:"):
        filename = commons.removeprefix("File:").replace(" ", "_")
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
    return None


async def _reverse_geocode(client: httpx.AsyncClient, lat: float, lng: float) -> tuple[str | None, str | None]:
    try:
        resp = await client.get(
            NOMINATIM_REVERSE_URL,
            params={"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 18, "addressdetails": 1},
            headers=OSM_REQUEST_HEADERS,
        )
        if resp.status_code != 200:
            return None, None
        data = resp.json()
        address = data.get("address", {})
        postcode = address.get("postcode")
        display = data.get("display_name")
        return display, postcode
    except Exception:
        logger.exception("Nominatim reverse geocode failed for %s,%s", lat, lng)
        return None, None


async def discover_venues(max_results: int = 30) -> list[VenueCandidate]:
    settings = get_settings()
    bbox = _bbox_from_center(settings.search_lat, settings.search_lng, settings.search_radius_m)
    query = _build_overpass_query(bbox)

    async with httpx.AsyncClient(timeout=40, headers=OSM_REQUEST_HEADERS) as client:
        try:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
        except Exception:
            logger.exception("Overpass query failed; returning no candidates for this run")
            return []
        elements = resp.json().get("elements", [])
        # Overpass returns elements in a stable order (roughly OSM element
        # ID), so without shuffling, a small max_results always evaluates
        # the exact same leading subset on every run. Shuffle first so
        # repeated runs sample different venues from the full search area.
        random.shuffle(elements)

        candidates: list[VenueCandidate] = []
        for element in elements:
            tags = element.get("tags", {})
            name = tags.get("name")
            if not name:
                continue

            osm_type = None
            for key, value, venue_type in OSM_QUERIES:
                if tags.get(key) == value:
                    osm_type = venue_type
                    break
            if osm_type is None:
                continue

            if element["type"] == "node":
                lat, lng = element["lat"], element["lon"]
            else:
                center = element.get("center")
                if not center:
                    continue
                lat, lng = center["lat"], center["lon"]

            address = _address_from_tags(tags)
            postcode = tags.get("addr:postcode")
            if not postcode and address:
                m = UK_POSTCODE_RE.search(address)
                postcode = m.group(1).upper() if m else None

            if not address or not postcode:
                # Rate-limited per Nominatim's usage policy (max ~1 req/sec).
                display, geocoded_postcode = await _reverse_geocode(client, lat, lng)
                address = address or display
                postcode = postcode or geocoded_postcode
                await asyncio.sleep(1.1)
            # No raw-coordinate placeholder: a venue whose address/postcode is
            # still unresolved after Nominatim stays None here and gets
            # rejected explicitly (with reasoning) in fit.py, rather than
            # silently passed downstream as fake-looking address text.

            candidates.append(VenueCandidate(
                venue_id=f"{element['type']}/{element['id']}",
                name=name,
                address=address,
                postcode=postcode,
                lat=lat,
                lng=lng,
                venue_type=osm_type,
                osm_tags=tags,
                website=tags.get("website") or tags.get("contact:website"),
                osm_photo_url=_photo_url_from_tags(tags),
            ))

            if len(candidates) >= max_results:
                break

    return candidates


async def fetch_osm_photo_bytes(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=OSM_REQUEST_HEADERS)
            if resp.status_code != 200:
                return None
            return resp.content
    except Exception:
        logger.exception("Failed to fetch OSM photo %s", url)
        return None
