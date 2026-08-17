"""Last-resort frontage source: the venue's own website og:image.

Used only when Street View has no usable frame (no coverage, or every
heading attempt fails the usability check) and Google Place photos are
also unusable/absent.
"""
from __future__ import annotations

import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def fetch_website_og_image(website_url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(website_url, headers={"User-Agent": "Mozilla/5.0 (compatible; PlanterProspectBot/1.0)"})
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
            if not tag or not tag.get("content"):
                return None
            image_url = urljoin(website_url, tag["content"])
            image_resp = await client.get(image_url)
            if image_resp.status_code != 200:
                return None
            return image_resp.content
    except Exception:
        logger.exception("Website og:image fallback failed for %s", website_url)
        return None
