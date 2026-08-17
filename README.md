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
  generation, `httpx` for OpenStreetMap / Mapillary.
- **Frontend:** React + TypeScript (Vite), Tailwind CSS.
- **APIs:** OpenStreetMap (Overpass + Nominatim, no key) for venue discovery, Mapillary
  (free tier) for street-level frontage imagery, Gemini API (`gemini-2.5-flash` for vision
  judgements, `gemini-2.5-flash-image` for compositing).
- No database — the prototype keeps run results in memory and generated images on disk
  (`backend/data/images/`), which is enough for a handful of venues per run. See
  design.md §4 for what changes at production scale.

## Project layout

```
backend/
  app/
    main.py              FastAPI app, CORS, static mounts
    config.py             env-driven settings (API keys, search area)
    schemas.py             all Pydantic response models
    products.py            client's 3-product catalogue (real reference photos)
    services/
      osm.py                OpenStreetMap (Overpass) discovery + Nominatim address fill-in
      fit.py                rule + vision "is this a good candidate" scoring
      mapillary.py           nearby-image search, bearing/heading-match ranking
      frontage.py           orchestrates mapillary -> osm photo -> website fallback
      fallback_images.py    venue website og:image scraper
      vision.py             all Gemini vision-judgement prompts/calls
      compositing.py        Gemini image generation + QA rejection gate
      image_store.py        saves generated/fetched images to disk
    routers/
      pipeline.py           POST /api/pipeline/run, GET /api/pipeline/run/{id}
      products.py           GET /api/products
frontend/
  src/
    App.tsx                 top-level page: run controls, results
    api.ts, types.ts         typed API client
    components/              VenueCard, FrontagePanel, CompositePanel, before/after slider, ...
assets/products/               raw product photos extracted from the client brief (gitignored;
                                the versions actually used by the app live in
                                backend/app/static/products and frontend/public/products)
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

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. In dev, Vite proxies `/api`, `/images` and `/static` to the
backend on `:8000` (see `vite.config.ts`) — no `.env` needed locally. Click **"Run
prospecting pipeline"** to trigger a full run (venue discovery → fit scoring → frontage
capture → compositing). A run typically takes 1–3 minutes for 3 venues, since each venue
involves several sequential Gemini calls (usability checks per frontage attempt, plus up
to 2 compositing attempts with a QA check each).

### Running the pipeline / reproducing the venue list in design.md

Once both keys are live, either use the UI button above, or call the API directly:

```bash
curl -X POST http://127.0.0.1:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"target_count": 3, "max_candidates": 30}'
```

The response includes every selected venue (with its frontage/composite results) and every
rejected candidate with its rejection reasoning — the same data the UI renders. Copy the
selected venues' name/address/postcode and a few notable rejections into `design.md`
§1 ("Selected venues from this run").

## Deployment

**Render (both services, via Blueprint).** `render.yaml` at the repo root defines both
services — apply it from the Render dashboard: **New +** → **Blueprint** → select this repo.

- `restu-api` — the FastAPI backend (`runtime: python`, free plan). After the first deploy,
  set `MAPILLARY_TOKEN` and `GEMINI_API_KEY` in its dashboard (left blank in the blueprint
  intentionally — never commit real keys).
- `restu-web` — the frontend static site (`npm run build`, publishes `dist`), pre-wired via
  `VITE_API_BASE` to call `restu-api`.
- If either service name is already taken, Render appends a suffix to its URL — update
  `CORS_ORIGINS` (on `restu-api`) and `VITE_API_BASE` (on `restu-web`) in the dashboard to
  match the actual assigned URLs, then trigger a manual redeploy on both.
- Free tier spins a service down after 15 min idle; the next request cold-starts in
  ~30-50s. Point an uptime monitor (e.g. UptimeRobot, 5-minute interval) at
  `restu-api.onrender.com/api/health` to keep it warm and get alerted on real downtime.
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

- Three or more venues per run is the brief's target; `target_count` defaults to 3 and is
  adjustable in the UI up to 10.
- Nothing in the selection, framing, or QA path is manually curated — every accept/reject
  decision (candidate fit, frontage usability, composite quality) is made by rule-based
  code or a Gemini vision judgement, with the reasoning kept and shown in the UI, per the
  brief's "your own code needs to decide, unaided" requirement.
# restu
