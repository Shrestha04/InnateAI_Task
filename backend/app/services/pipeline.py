"""End-to-end orchestration: discover venues -> score fit -> capture
frontage -> composite. Everything here is unattended/automated per the
brief — no manual curation step.
"""
from __future__ import annotations

import asyncio
import logging

from app import products
from app.schemas import PipelineRunResult, ScoredVenue, VenuePipelineResult
from app.services import compositing, fit, frontage as frontage_service, osm

logger = logging.getLogger(__name__)

FIT_SCORING_CONCURRENCY = 5


async def _bounded_gather(coros, limit: int):
    semaphore = asyncio.Semaphore(limit)

    async def _run(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(*[_run(c) for c in coros])


async def run_pipeline(target_count: int = 3, max_candidates: int = 30) -> PipelineRunResult:
    candidates = await osm.discover_venues(max_results=max_candidates)
    logger.info("Discovered %d raw venue candidates", len(candidates))

    fit_verdicts = await _bounded_gather([fit.score_venue(v) for v in candidates], FIT_SCORING_CONCURRENCY)
    scored = [ScoredVenue(venue=v, fit=f) for v, f in zip(candidates, fit_verdicts)]

    accepted = sorted((s for s in scored if s.fit.accepted), key=lambda s: s.fit.score, reverse=True)
    rejected = [s for s in scored if not s.fit.accepted]
    selected = accepted[:target_count]

    results: list[VenuePipelineResult] = []
    for scored_venue in selected:
        venue = scored_venue.venue
        frontage_result = await frontage_service.capture_frontage(venue)

        product = None
        composite_result = None
        if frontage_result.accepted:
            product = products.pick_product_for_venue(venue.venue_type.value)
            composite_result = await compositing.composite_for_venue(frontage_result, product)

        results.append(VenuePipelineResult(
            venue=venue,
            fit=scored_venue.fit,
            frontage=frontage_result,
            product=product,
            composite=composite_result,
        ))

    return PipelineRunResult(
        requested_count=target_count,
        candidates_considered=len(scored),
        rejected_venues=rejected,
        results=results,
    )
