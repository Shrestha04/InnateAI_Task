# Storefront capture & visualisation

Prototype for Innate AI's planter-prospecting engine. Given a search area in London, it
automatically: discovers independent café/restaurant/salon venues, judges which ones have a
bare/under-dressed frontage the client's planters would visibly improve, captures a
real, well-framed photo of the actual entrance, and composites the client's real product
photography onto it — producing a "what it could look like" sales visual, end to end,
with no manual curation step.

See [`design.md`](./design.md) for the full design write-up (venue selection logic,
frontage-framing approach, imagery-rights position, scale estimation, and rejection
criteria).

## Stack

- **Backend:** FastAPI (Python 3.11+), `google-genai` for Gemini vision + image
  generation, `httpx` for OpenStreetMap / Mapillary, `beautifulsoup4` for the website
  `og:image` fallback scrape, `rembg` + `onnxruntime` + Pillow for the local, non-AI
  compositing fallback (see below).
- **Frontend:** React + TypeScript (Vite), Tailwind CSS, `react-router` (marketing home
  page, the pipeline/demo console, and a static results showcase as separate routes).
- **APIs:** OpenStreetMap (Overpass + Nominatim, no key) for venue discovery, Mapillary
  (free tier) for street-level frontage imagery, Gemini API (`gemini-3.1-flash-lite` for
  vision judgements, `gemini-3.1-flash-image` for compositing).
- No database — the prototype keeps run results in memory (`app/storage.py::RunStore`) and
  generated images on disk (`backend/data/images/`), which is enough for a handful of
  venues per run. See design.md §4 for what changes at production scale.

## Project layout

```
backend/
  app/
    main.py                 FastAPI app, CORS, static mounts, /api/health
    config.py                env-driven settings (API keys, search area, model names)
    schemas.py                all Pydantic response models
    products.py               client's 3-product catalogue (real reference photos)
    storage.py                in-memory run store, keyed by run id
    services/
      osm.py                   OpenStreetMap (Overpass) discovery + Nominatim address fill-in
      fit.py                   rule + vision "is this a good candidate" scoring
      mapillary.py              nearby-image search, bearing/heading-match ranking
      frontage.py              orchestrates mapillary -> osm photo -> website fallback,
                                entrance-zoom crop
      fallback_images.py       venue website og:image scraper
      vision.py                all Gemini vision-judgement prompts/calls (fit, frontage
                                usability, entrance detection, composite QA)
      compositing.py           Gemini image generation + QA rejection gate (primary path)
      classical_compositing.py free, local, non-AI cutout-and-shadow fallback (rembg +
                                door-height scale math), used when Gemini image generation
                                is unavailable on the current key's tier
      image_store.py           saves generated/fetched images to disk
      pipeline.py              end-to-end orchestration: discover -> score -> capture ->
                                composite, bounded-concurrency fit scoring
    routers/
      pipeline.py               POST /api/pipeline/run, GET /api/pipeline/run/{id}
      products.py               GET /api/products
      demo.py                   manual compositing playground: upload a frontage photo,
                                pick a product, edit the prompt, generate one-off
    scripts/
      fetch_results_auto.py     populates the static /results showcase using the real
                                frontage-capture pipeline (not curated by hand); run manually
    static/products/            the 3 reference product photos served by the API
frontend/
  src/
    App.tsx                    routes: / (marketing home), /app (pipeline + demo console),
                                /results (static before/after showcase)
    api.ts, types.ts             typed API client
    components/
      HomePage.tsx, PipelineGallery.tsx, Marquee.tsx   marketing/landing page
      ConsolePage.tsx           tab container for the pipeline runner and the demo playground
      PipelinePage.tsx, RunControls.tsx, SummaryStats.tsx, VenueCard.tsx,
      RejectedList.tsx, AttemptLog.tsx, FrontagePanel.tsx, CompositePanel.tsx,
      BeforeAfter.tsx, StatusBadge.tsx      the automated pipeline run + its results
      DemoPage.tsx               manual single-shot compositing playground UI
      ResultsPage.tsx            static showcase of real, pipeline-produced before/afters
  public/
    products/                   product photos used by the UI
    results/                    committed before/after image pairs (26 Furnival Street,
                                A Toca), produced by scripts/fetch_results_auto.py — not
                                generated at runtime
design.md
```

## Running locally

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # then fill in the two keys below
uvicorn app.main:app --reload --port 8000
```

`.env` needs:

```
MAPILLARY_TOKEN=...   # free, no card — https://www.mapillary.com/dashboard/developers
GEMINI_API_KEY=...    # https://aistudio.google.com/apikey
```

Venue discovery itself (OpenStreetMap Overpass + Nominatim) needs no key at all.

Health check: `GET http://127.0.0.1:8000/api/health` should report both keys configured.
API docs at `http://127.0.0.1:8000/docs`.

**Note on the Gemini key's tier.** Gemini's image-*generation* model
(`gemini-3.1-flash-image`) carries a 0/day quota on newly-created/free-tier projects by
default — this applies regardless of the key otherwise working for vision/text calls
(`gemini-3.1-flash-lite`, used for fit/usability/QA judgements). If your key doesn't have
image-generation quota, compositing still works end to end via the local, non-AI
`classical_compositing` fallback (rembg cutout + door-height scale math — see design.md
§3) rather than failing; results are labelled `method: "classical"` in the API/UI so it's
clear which path produced them. To exercise the primary Gemini compositing path, the
Gemini project backing the key needs billing enabled.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. In dev, Vite proxies `/api`, `/images` and `/static` to the
backend on `:8000` (see `vite.config.ts`) — no `.env` needed locally.

- `/` — marketing/landing page.
- `/app` — the console: **Pipeline** tab runs the full automated pipeline (venue discovery
  → fit scoring → frontage capture → compositing) via **"Run prospecting pipeline."** A run
  typically takes 1–3 minutes for 3 venues, since each venue involves several sequential
  Gemini calls (usability checks per frontage attempt, entrance detection, plus up to 2
  compositing attempts with a QA check each). **Demo** tab is a manual playground: upload
  any frontage photo, pick a product, optionally edit the compositing prompt, and generate
  a single result directly, without running the full pipeline.
- `/results` — a static showcase of real before/after pairs (committed images, not
  generated on page load), produced by `backend/scripts/fetch_results_auto.py` against the
  actual frontage-capture pipeline.

### Running the pipeline / reproducing the venue list in design.md

Once both keys are live, either use the UI button above, or call the API directly. The
API's own default is `target_count: 2, max_candidates: 5` (deliberately conservative — see
the note below on free-tier Gemini quota); pass explicit values to get 3+ venues for the
brief:

```bash
curl -X POST http://127.0.0.1:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"target_count": 3, "max_candidates": 30}'
```

The response includes every selected venue (with its frontage/composite results and which
compositing method — `gemini` or `classical` — produced the final image) and every rejected
candidate with its rejection reasoning — the same data the UI renders. Copy the selected
venues' name/address/postcode and a few notable rejections into `design.md` §1 ("Selected
venues from this run").

To regenerate the static `/results` showcase images from fresh live data:

```bash
cd backend
python scripts/fetch_results_auto.py
```

This discovers independent restaurants via OSM, runs each through the real
`frontage.capture_frontage` pipeline, and saves the first 5 accepted "before" frames into
`frontend/public/results/` — the same code path the automated pipeline uses, not a
hand-picked set of photos.

## Deployment

**Render (both services, via Blueprint).** `render.yaml` at the repo root defines both
services — apply it from the Render dashboard: **New +** → **Blueprint** → select this repo.

- `restu-api` — the FastAPI backend (`runtime: python`, free plan). After the first deploy,
  set `MAPILLARY_TOKEN` and `GEMINI_API_KEY` in its dashboard (left blank in the blueprint
  intentionally — never commit real keys). A free-tier/unbilled Gemini key still works end
  to end via the classical compositing fallback (see "Running locally" above).
- `restu-web` — the frontend static site (`npm run build`, publishes `dist`), pre-wired via
  `VITE_API_BASE` to call `restu-api`.
- If either service name is already taken, Render appends a suffix to its URL — update
  `CORS_ORIGINS` (on `restu-api`) and `VITE_API_BASE` (on `restu-web`) in the dashboard to
  match the actual assigned URLs, then trigger a manual redeploy on both.
- Free tier spins a service down after 15 min idle; the next request cold-starts in
  ~30–50s. Point an uptime monitor (e.g. UptimeRobot, 5-minute interval) at
  `restu-api.onrender.com/api/health` to keep it warm and get alerted on real downtime.
- The classical fallback's `rembg`/`onnxruntime` model is deliberately configured with the
  CPU memory arena disabled (`classical_compositing.py::_get_rembg_session`) to keep a flat
  ~380MB footprint — needed to fit inside a 512MB free-tier container; without it, RSS
  grows by ~650MB per call and never comes back down.
- Generated images (`backend/data/images/`) live on ephemeral disk — fine for demoing, but
  they're wiped on every redeploy/restart. Not a concern for `frontend/public/results/`,
  which is committed to the repo rather than generated at runtime.

**Alternative: Vercel (frontend only) + Render/Fly.io/Railway (backend).** Vercel's
serverless Python runtime isn't a fit for the backend here — a pipeline run is one
long-lived request (multiple sequential Gemini calls, routinely 1–3 minutes) writing to
local disk, which doesn't survive serverless invocations. Deploy the frontend to Vercel
(root `frontend/`, framework preset "Vite", build `npm run build`, output `dist`,
`VITE_API_BASE` set to wherever the backend ends up) and the backend to any long-running
host with the existing `uvicorn app.main:app` entrypoint — no code changes needed either
way.

## Notes on scope

- Three or more venues per run is the brief's target. The API/UI default (`target_count=2,
  max_candidates=5`) is set conservatively low out of the box because each additional
  candidate costs several sequential Gemini calls (fit check, one usability check per
  frontage attempt, entrance detection, up to 2 compositing QA passes) against what's
  typically a rate-limited free-tier key — `target_count` is adjustable in the UI up to 10,
  and was set to 3 for the run documented above.
- Nothing in the selection, framing, or QA path is manually curated — every accept/reject
  decision (candidate fit, frontage usability, composite quality) is made by rule-based
  code or a Gemini vision judgement, with the reasoning kept and shown in the UI, per the
  brief's "your own code needs to decide, unaided" requirement.
- Compositing has two paths, not one: the primary path is Gemini image generation with an
  automated 6-check QA gate; a local, non-AI cutout-and-shadow fallback (`rembg` +
  measured door-height scaling) kicks in automatically — and is clearly labelled — only
  when Gemini can't generate an image at all (e.g. an unbilled key's 0/day image-generation
  quota), so the pipeline always produces an inspectable result rather than failing
  silently. Full reasoning in design.md §3.
