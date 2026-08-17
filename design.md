# Design note — storefront capture & visualisation

This covers the two capabilities at the technical heart of the prospecting engine:
getting a usable, well-framed photo of a real venue's frontage, and compositing the
client's real planters onto it believably. It's written at the depth a second engineer
should be able to build the same system from; file/function references point at the
actual prototype implementation in `backend/app/`.

## 1. Choosing venues

**Source.** OpenStreetMap — Overpass API for the raw venue data, Nominatim for
address/postcode fill-in — `backend/app/services/osm.py`. Both are free and keyless, which
matters at 5,000+ venues/week where a metered API becomes a real cost line. Overpass is
queried around a central-London point (`search_lat`/`search_lng`, 4km radius, configurable
in `app/config.py`) for four `(OSM tag, value)` pairs, each as both a `node` and a `way`
(small venues are nodes; venues occupying a mapped building outline are ways):

| OSM tag | Value | Maps to |
|---|---|---|
| `amenity` | `cafe` | café |
| `amenity` | `restaurant` | restaurant |
| `shop` | `hairdresser` | salon |
| `shop` | `beauty` | salon |

OSM has no "is this a chain" signal built in, so independence is enforced entirely by the
rule-based prefilter below rather than a search-time keyword bias.

**Rule-based prefilter** (cheap, runs before any model call), `services/osm.py` /
`services/fit.py::_rule_reject`:
- **Chain blocklist** — a hard-coded list of ~20 well-known chain names (Starbucks, Costa,
  Pret, Greggs, Nando's, Toni & Guy, ...) matched case-insensitively against the venue
  name (`osm.py::is_chain`). The client wants independents with bare frontages, not
  corporate storefronts that already follow brand guidelines for their entrance.
- **Must have a `name` tag** — anonymous/unnamed nodes (mis-tagged street furniture, etc.)
  are dropped before anything else runs.
- **Venue type restricted** to café / restaurant / salon (`services/fit.py::ALLOWED_TYPES`)
  — the four OSM tag/value pairs above already constrain this, but the check is repeated
  in `fit.py` so it's enforced even if the query list changes later.

**Address completion.** OSM's own `addr:*` tags are frequently missing or partial for small
independents (present for maybe half of candidates in practice). Where `addr:housenumber`/
`addr:street` or `addr:postcode` is missing, `osm.py::_reverse_geocode` calls Nominatim's
reverse-geocoding endpoint for that coordinate and fills the gap from its `address.postcode`
and `display_name`. This runs at Nominatim's mandated rate limit (≤1 request/second, throttled
explicitly in code) and only for candidates that already passed the chain/type filters above,
to keep the added latency proportional to what's actually needed.

**Vision-model fit judgement** (`services/fit.py::score_venue`, prompt
`services/vision.py::FIT_PROMPT`, called via `judge_frontage_fit`). For each surviving
candidate, the best available photo (the OSM `image`/`wikimedia_commons` tag if the venue
has one, otherwise the closest-matching nearby Mapillary frame — see §2) is sent to Gemini
with the venue name/type and this question, answered as strict JSON:

```json
{
  "is_street_facing_entrance": true/false,
  "frontage_is_bare_or_underdressed": true/false,
  "planters_would_visibly_help": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "..."
}
```

A venue is **accepted** only if all three booleans are true and `confidence >= 0.55`
(`ACCEPT_THRESHOLD`). The reasoning string and the boolean signals are kept and shown
per-venue in the UI (and would be logged at scale) — nothing here is manually eyeballed;
every accept/reject has a machine-written reason attached. `services/pipeline.py::run_pipeline`
runs this scoring across all discovered candidates concurrently (bounded to 5 in flight at
once, `FIT_SCORING_CONCURRENCY`) rather than sequentially, since it's the step that scales
worst with candidate count.

**Accept/reject bar, stated explicitly:** a candidate is usable if (a) it's an independent
café/restaurant/salon, (b) it is not permanently closed, (c) a photo of its frontage is
available from at least one source, and (d) the vision model judges the entrance to be
genuinely street-facing, currently under-dressed, and a plausible improvement candidate
with confidence ≥ 0.55. Anything failing (d) is rejected even if (a)–(c) pass — e.g. a café
with an already-planted frontage, or a restaurant whose only available photo is an interior
shot. Rejected venues are kept (not discarded) with their reasoning, both in the API
response (`PipelineRunResult.rejected_venues`) and the UI's "N candidates rejected" panel,
so the decision is auditable.

**Selected venues from this run** (a live run against the default London search area,
reproducible via `README.md` "Running the pipeline"; OSM/Mapillary coverage and Gemini's
vision judgements aren't perfectly deterministic between runs, so a different run surfaces
different specific venues, but the accept/reject logic itself is fixed):

| Venue | Address | Postcode | Type | Fit score | Frontage | Composite |
|---|---|---|---|---|---|---|
| 26 Furnival Street | 26 Furnival Street, London | EC4A 1JS | Restaurant | 0.90 | Mapillary — accepted, entrance-zoomed | Accepted (classical fallback — Gemini image-generation quota wasn't available on this key's tier at run time; see §3) |
| A Toca | 339–343 Wandsworth Road, London | SW8 2JH | Restaurant | — | Mapillary — accepted, entrance-zoomed | Accepted |
| Cafe Angel | 250 [address partially unresolved], London | WC1X 8JR | Café | 0.90 | No usable frame across Mapillary/OSM/website — skipped | — (compositing correctly skipped; no base image to composite onto) |

26 Furnival Street's fit reasoning: *the building frontage is plain brick and glass with no
existing greenery or decorative elements, making it a strong candidate for planters to
soften the sterile, industrial aesthetic.* Its accepted Mapillary frame was also used to
verify the entrance-zoom step (§2): `detect_entrance` located the doorway at 0.95 confidence,
and the wide street shot was correctly cropped down to a tight, well-framed shot of just the
entrance. A Toca followed the same path and is the second worked example committed under
`frontend/public/results/` (before/after pair), generated via the results-showcase script
described in §2/§4 rather than by hand.

Cafe Angel passed the fit bar (0.90 — "paved, lacks greenery") but produced no usable
frontage frame from any of the three sources, so the pipeline correctly skipped compositing
for it rather than send a bad base image downstream — visible in the UI's frontage attempt
log with the specific per-attempt rejection reasoning.

**Rejected before selection** (6 of 8 candidates screened in this run):

| Venue | Type | Score | Reasoning |
|---|---|---|---|
| Woburn Cafe | Café | 0.40 | Best available photo showed a hotel/residential street scene — no cafe entrance visible |
| The Serpentine Lido Cafe | Café | 0.10 | No OSM photo or nearby Mapillary frame to assess |
| Starbucks | Café | 0.00 | Chain blocklist — rejected before any vision call |
| Bon Gusto | Restaurant | 0.10 | No OSM photo or nearby Mapillary frame to assess |
| Bank Restaurant & Bar | Restaurant | 0.10 | No OSM photo or nearby Mapillary frame to assess |
| Buckingham Coffee Lounge | Café | 0.10 | No OSM photo or nearby Mapillary frame to assess |

The 0.10-score rejections are the dominant real-world failure mode observed, not the vision
judgement itself: several small independents have no OSM `image`/`wikimedia_commons` tag
and no Mapillary coverage within the search tolerance, so `fit.py`'s best-effort image lookup
has nothing to score them against. That's a coverage gap, not a scoring bug — see §4 for what
I'd change (progressively widening the Mapillary search radius, and a further fallback to
Google Places/Street View coverage, which the brief itself allows as a source, before
rejecting purely on "no image available").

## 2. Getting the frontage image

Implementation: `backend/app/services/mapillary.py` (framing) +
`backend/app/services/frontage.py` (orchestration/fallback) +
`backend/app/services/vision.py::judge_frontage_usability` and `detect_entrance`
(accept/reject + entrance zoom).

**Why Mapillary, and how it differs from Street View's panorama model.** Street View gives
you one panorama per capture point that you can virtually rotate to any heading on demand.
Mapillary's free-tier coverage is instead a corpus of individually-captured, mostly
fixed-perspective photographs, each already pointing in whatever direction the
contributor's camera/dashcam happened to face. That changes the framing problem from
"compute the heading, then request that view" to "search nearby images and rank them by how
close their *already-captured* heading is to the direction we need" — a search-and-rank
problem rather than a compute-and-request one. In practice:

1. Query the Mapillary **image search** endpoint (`graph.mapillary.com/images`) with a
   small bounding box around the venue (~60m — `SEARCH_RADIUS_M`), requesting `geometry`
   (the capture location), `compass_angle`/`computed_compass_angle` (the direction the
   camera was facing), and a thumbnail URL for each nearby image.
2. For every returned image, compute the **compass bearing** from that image's own capture
   location to the venue's coordinate (`mapillary.py::_bearing_deg`, the same great-circle
   bearing formula Street View's heading derivation would use), then compute the **angular
   difference** between that ideal bearing and the image's actual `compass_angle`
   (`_angular_diff`). This is the panorama-heading-matching idea carried over to a
   fixed-shot corpus: instead of rotating a panorama to the bearing we want, we find the
   photo whose capture heading already comes closest to it.
3. Rank candidates by that angular difference (closest-facing first) and take the top 3
   (`MAX_CANDIDATES`) as framing attempts — mirroring the "retry at nearby headings" idea
   from a panorama-based approach, just realised as "try the next-closest real photo"
   instead of "rotate a few degrees and re-render."
4. Panoramic (`is_pano`) captures are explicitly skipped. Reprojecting an equirectangular
   360° image to a directional crop is the same underlying idea as Street View's heading
   parameter, but implementing that reprojection is a real feature in its own right, not
   something to bolt on for a 3-venue prototype — noted as a limitation, not silently
   ignored. **Field of view** is also an honest approximation here: Mapillary's public
   fields don't expose a precise per-image FOV, so a fixed 75° (`ASSUMED_FOV`) is assumed,
   reasonable for the dashcam/action-cam rigs that make up most of its coverage, but a
   coarser number than Street View's exact `fov` parameter would give.

**When imagery faces the wrong way or doesn't show the entrance.** Every frame — from any
source — is scored by `judge_frontage_usability`, a Gemini vision call answering:

```json
{
  "shows_entrance_clearly": true/false,
  "reasonably_front_on": true/false,
  "unobstructed": true/false,
  "usable": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "..."
}
```

`usable` requires all three booleans true. If none of the (up to 3) ranked Mapillary frames
pass, the pipeline falls back, **in order**:
1. **An OSM-tagged photo** (`osm.py::fetch_osm_photo_bytes`, from the venue's own `image` or
   `wikimedia_commons` tag) — present for a minority of listings, but when it exists it's
   already attached to this specific venue rather than found by proximity search. Run
   through the same usability check.
2. **The venue's own website `og:image`** (`fallback_images.py`) — scraped as a last
   resort, since a business's own homepage hero image is frequently a shot of their own
   doorway/shopfront.

If nothing passes, the venue is marked `frontage.accepted = false` with the reasoning
preserved, and the pipeline skips compositing for it rather than sending a bad base image
downstream. Every attempt across every source is retained in `FrontageResult.attempts` and
shown in the UI's expandable attempt log — the accept/reject decision is fully automated
and auditable, per venue, without anyone eyeballing a map view.

**Accept/reject bar, stated explicitly:** a frontage frame is usable only if the model
confirms it clearly shows the entrance, is reasonably front-on (not a steep side angle),
and is unobstructed (no scaffolding, no vehicle or pedestrian blocking most of the
doorway, not too dark/blurry to read). This is deliberately strict, because this image
becomes the base layer of a photo sent to the venue owner — anything ambiguous here
compounds into a worse composite later.

**Zooming to the entrance.** Once a frame passes the usability gate, a second Gemini vision
call (`vision.py::detect_entrance`, prompt `ENTRANCE_PROMPT`) locates the entrance door's
tight bounding box, in the same 0–1000 normalized-coordinate style as the usability check.
`frontage.py::_zoom_to_entrance` crops the wide street frame around that box — padded for
context (door frame, threshold, a little pavement either side), fitted to a 4:3 frame, and
upscaled with Lanczos resampling if the crop comes out small — and this cropped image
*replaces* `FrontageResult.image_url`/`image_path` for everything downstream, including the
compositing base image. The sales visual ends up centred on the doorway itself, not the
whole facade, at essentially no extra pipeline cost (one more vision call per accepted
frame, not per attempt). If the entrance isn't confidently detected
(`entrance_visible=false` or `confidence < 0.5`), the wide frame is kept rather than risking
a bad crop — the original attempt is always still shown in the UI's attempt log either way.

**Results showcase.** `backend/scripts/fetch_results_auto.py` is a small, separate script
(not part of the app's runtime request path) that exercises this exact same
`frontage.capture_frontage` code against freshly-discovered independent restaurants and
saves the first N accepted "before" frames into `frontend/public/results/` for the static
`/results` demo page — it reuses the pipeline's real logic rather than curating photos by
hand, and is how the 26 Furnival Street / A Toca before-images in that page were produced.

### Imagery-rights position

This is the part I'd want a real legal/commercial sign-off on before scaling past a
prototype, but my working position — and switching the imagery source from Google to
OpenStreetMap/Mapillary (see §2) genuinely improves this story, not just the cost:

- **The licensing here is explicitly built for reuse.** OpenStreetMap's data is ODbL
  (Open Database License) — free to use, adapt, and use commercially, with attribution to
  "© OpenStreetMap contributors." Mapillary's contributed imagery is CC-BY-SA — again
  explicitly permitting commercial use and derivative works (which is exactly what
  compositing is), provided attribution is given. That's a fundamentally different starting
  point from Street View's terms, which restrict use to display within a Google Maps
  context and don't license standalone redistribution at all — this isn't a workaround for
  a restrictive ToS, it's imagery actually licensed for what this product does.
- **The genuine open question is CC-BY-SA's share-alike clause** — strictly read, a
  published *adaptation* of CC-BY-SA imagery should carry the same license and attribution
  forward. My working position: a single composited image emailed to one venue owner as
  personalised, non-published outreach is a private communication, not a "publication" of
  an adapted dataset in the sense the share-alike clause is aimed at (it's aimed at e.g.
  reusing Mapillary imagery to build and publish a competing map product). I'd still credit
  the sources ("Imagery: Mapillary contributors. Map data: OpenStreetMap contributors") in
  outreach material as a low-cost way to remove the ambiguity entirely, and would not rely
  on this reading for anything that gets *published* rather than sent 1:1 (a public case
  study, a landing page using the same composite) without checking that use against
  Mapillary's actual commercial terms first.
- **At the stated scale (5,000+ venues/week),** I'd confirm directly with Mapillary that
  this volume of programmatic image fetching sits within their free/fair-use tier rather
  than assuming it does — heavy automated reuse is exactly the kind of usage a "free for
  reasonable use" imagery API tends to define a commercial tier around, and I'd rather ask
  than find out from a rate-limit wall mid-pipeline.
- **Property/privacy, separate from the licensing question:** photographing a shopfront
  from a public street is not a privacy violation in the UK — there's no reasonable
  expectation of privacy for a building's public-facing exterior. The more interesting
  question is consent for the *commercial* act of generating and sending an altered image
  of someone's property to them unsolicited. My position: this is defensible as a
  legitimate-interest, one-to-one sales approach (UK GDPR Art. 6(1)(f), for any
  incidentally-visible individuals in the source photo) provided the image is (a) clearly
  labelled as an illustrative AI-generated concept, not a real installation, and (b) the
  outreach includes a straightforward way to ask for it not to happen again. I would not
  be comfortable with this same imagery being used in public advertising (a billboard, a
  public case-study page) without the owner's explicit sign-off — the bar for "we sent
  you one mockup to start a conversation" is materially lower than "we published your
  building."
- **I am not a lawyer**, and would not ship the 5,000/week version without a real legal
  review covering both the Google Maps Platform commercial terms and UK GDPR — the above
  is my defensible working position for a prototype/early pilot, not a substitute for that
  review.

## 3. Compositing the planters

Implementation: `backend/app/products.py` (catalogue) +
`backend/app/services/compositing.py` (Gemini generation + QA loop, primary path) +
`backend/app/services/classical_compositing.py` (deterministic, non-AI fallback path, used
automatically when the primary path can't run at all — see below).

**Primary path — Gemini image generation.** `gemini_image_model` (`gemini-3.1-flash-image`,
configured in `app/config.py`) accepts multiple reference images plus a text instruction and
returns an edited image — the natural fit for "take this real product photo and place it
into this real scene," as opposed to text-to-image generation which would reinterpret the
product from a caption.

**A real constraint this prototype ran into, and why the fallback path exists.** Gemini's
image-*generation* models currently carry a 0/day quota on every project by default,
including this one's — regardless of which text/vision model tier the project otherwise has
access to. Generating a composite at all requires a billed Gemini project; there is no
free-tier path around it. Rather than let the whole compositing step silently fail (or block
the submission on getting a billed key provisioned in time), `compositing.py::composite_for_venue`
only falls back to the classical path **when Gemini could not generate an image at all across
every attempt** — a capability gap, not a quality judgement. A generation Gemini *did* produce
but the QA gate rejected stays rejected; it does not silently swap to the classical method.
This is exactly the kind of infrastructure/quota reality a second engineer building this for
real would hit, so it's handled as a designed fallback rather than patched around.

**Estimating real-world scale from a reference object (both paths).** The frontage photo
always contains one dependable real-world reference: **the entrance door itself.** UK
commercial doors are near-universally 1.98–2.10m tall (`UK_DOOR_HEIGHT_M`) — a far tighter
and more reliable range than estimating scale from, say, a person who might be anywhere in
frame or absent entirely. Each product in the catalogue carries a measured
`reference_height_m` (taken from the client's own product photography/spec — e.g. the black
cylinder planter's container is ~0.55m, its planting reaches ~1.1m overall; see
`products.py`).

- **Gemini path:** the compositing prompt (`compositing.py::COMPOSITE_PROMPT`) states both
  figures explicitly and instructs the model to size the planter against the doorway using
  that real ratio — a **prompt-based scale anchor**, appropriate for a prototype, but the
  honest limitation is that it relies on the model's own visual estimate of the doorway's
  pixel height rather than a measured one.
- **Classical path:** this is where the door-height reference is actually measured rather
  than estimated. A cheap, text-only Gemini vision call (`classical_compositing.py::_detect_door`,
  `DOOR_PROMPT`) returns the door's top/bottom pixel position (0–1000 normalized) and a
  ground placement point beside it. From the door's measured pixel height and the same
  2.04m assumption, the code computes an exact **metres-per-pixel** figure for that specific
  photo, and scales the product's known `visual_height_m` into an exact target pixel height
  — a precise, deterministic version of the same idea the Gemini path leaves to the model's
  judgement.

The more rigorous version I'd build next for the *Gemini* path specifically: reuse the same
door-detection call the classical path and the entrance-zoom step (§2) already make, compute
the precise pixel target from it, and pass that **exact number** into the compositing prompt
(or pre-scale a cutout before compositing) instead of leaving the ratio to the
image-generation model's own visual estimate. Three separate parts of this codebase currently
detect "the door" independently (entrance-zoom, classical placement, Gemini's own visual
guess) rather than sharing one detection — see §4.

**Keeping products visually faithful.**
- **Gemini path**, three levers, all in `compositing.py`:
  1. The actual product photo is passed as a **reference image**, not described in text —
     the model is editing/compositing against real pixels, not re-imagining "a black
     planter" from a caption.
  2. The prompt explicitly instructs: *keep the planter's container material, colour, shape
     and the plants/foliage identical to the reference image; reuse the exact product shown,
     don't invent a different one.*
  3. The **QA gate** (below) checks `product_matches_reference` on every generation and
     rejects drift instead of accepting a plausible-looking but different planter.
- **Classical path**, faithfulness is structural rather than prompted: `rembg`
  (`isnet-general-use` model, run fully locally — no API call) segments the actual product
  photo into a cutout, which is pasted directly onto the frontage. There is no
  reinterpretation step to drift in the first place; the trade-off is realism, not fidelity
  (see limitations below).

**Rejection criteria — Gemini path** (`services/vision.py::judge_composite_quality`,
`QA_PROMPT`) — the automated gate a generation must pass before it's ever shown as a result.
Given the original frontage photo and the composited output side by side, Gemini answers six
independent booleans plus an overall verdict:

| Check | Rejects when |
|---|---|
| `building_unaltered` | facade, signage, windows, door or brickwork were changed/warped |
| `product_matches_reference` | the planter doesn't match the reference product's container/plants |
| `scale_plausible` | the planter is obviously too large or too small for the doorway |
| `perspective_plausible` | the planter's perspective doesn't match the camera angle of the scene |
| `has_grounding_and_shadow` | it floats, clips through geometry, or has no contact shadow |
| `no_visual_artifacts` | warped edges, duplicated geometry, or other rendering artifacts |

`accepted` is true only if **all six** are true — a single failed check is enough to reject
the whole generation. This is deliberately strict: a generation bad enough to embarrass the
sales rep sending it should never reach a venue owner, and each of these six is a distinct,
common failure mode of image-compositing models.

**Rejection criteria — classical path.** There is no image-quality QA gate here (there's no
generation to judge — the pasted cutout is what it is), only a capability gate: if the door
detector reports `door_visible: false`, the attempt is rejected outright rather than pasting
a planter at a guessed position with no scale reference. Its output is explicitly labelled
in the UI (`method: "classical"`, a "Classical fallback used" badge) rather than presented as
indistinguishable from a Gemini generation — a venue owner-facing sales visual should never
be ambiguous about which method produced it, and see the honest limitation called out below.

**Honest limitation of the classical path.** It is a real, inspectable result — the actual
product cutout, scaled from the same doorway-height reference math, placed at a
vision-detected ground point with a synthetic drop shadow — but it is a cutout-and-shadow
paste, not photorealistic generation: no perspective warp to match the camera angle, no
physically simulated relighting to match the scene's lighting direction/colour temperature.
It exists so the pipeline always produces *something* inspectable when the primary path is
unavailable, with that limitation surfaced rather than hidden, not as a claimed substitute
for the Gemini path's realism.

**Retry policy.** Up to `MAX_ATTEMPTS = 2` Gemini generations per venue/product. If the
first generation is rejected, a second is attempted; if that also fails **and at least one
of the two attempts produced an image at all**, the venue is marked `composite.accepted =
false` with the last rejection reasoning surfaced. If Gemini produced no image on either
attempt (the quota case), the classical fallback runs once. Either way, the venue is never
retried indefinitely and never silently returns a bad image. All attempts — including
rejected Gemini ones with their per-check breakdown, and the classical attempt when it runs
— are kept in `CompositeResult.attempts` and shown in the UI, so a rejected venue's failure
mode is visible, not hidden.

**Product selection per venue.** For the prototype, `products.py::pick_product_for_venue`
picks deterministically by venue type (salons → white cube planters, restaurants → corten
modular, cafés → black cylinder) so every venue gets a plausible-looking product without a
human choosing per venue. A production version would score fit against the facade's
colour/material and available pavement width instead of a fixed type mapping.

**Manual demo/prompt playground.** `backend/app/routers/demo.py` +
`compositing.py::generate_demo_composite` expose a separate, non-pipeline endpoint: upload
any frontage photo, pick a product, optionally edit the compositing prompt, and see a single
generation's result and QA breakdown directly — useful for iterating on the prompt itself
(`COMPOSITE_PROMPT` is exposed via `build_composite_prompt` as an editable starting point)
without running the full discovery→fit→frontage pipeline each time. It falls back to the
same classical method under the same quota condition, but a QA rejection here is shown for
information rather than gating anything — the playground's purpose is inspecting what a
given prompt produces, not enforcing the pipeline's accept bar.

## 4. What I'd change with more time

- Share one doorway detection across framing, classical scaling, and Gemini's compositing
  prompt, instead of three separate places (`detect_entrance` in §2, `_detect_door` in the
  classical path, and Gemini's own visual guess in the primary path) each re-deriving their
  own notion of "the door." The classical path already proves the measured-pixel approach
  works; wiring that same detection's pixel box into the Gemini prompt's scale math (as an
  exact number, not a stated ratio) is the natural next step and removes the single biggest
  source of scale drift in the primary path.
- Widen the Mapillary search past a fixed 60m/70° tolerance when coverage near a venue is
  thin — e.g. progressively growing the bounding box — instead of falling straight to the
  OSM-photo/website fallback the first time nothing in range matches well. In practice this
  is the dominant real-world rejection cause at the fit-scoring stage (§1's "no image
  available" rejections, e.g. Bon Gusto / Bank Restaurant & Bar / Buckingham Coffee Lounge
  in this run's rejected list) — a genuine coverage gap, not a scoring problem. A further
  fallback to the Google Places Photos API (the brief's other suggested source) before
  giving up entirely would close most of that gap, at the cost of a metered/keyed API in a
  pipeline otherwise built to be keyless at the discovery stage.
- Reproject panoramic (`is_pano`) Mapillary captures to a directional crop instead of
  skipping them outright — real feature, noted as a limitation in §2, not silently ignored.
- Add a perspective-warp + relighting step to the classical fallback (project the cutout
  onto an estimated ground plane, sample the frontage's local lighting for the shadow/tint)
  so it degrades more gracefully when it's the only path available, rather than being
  visibly a flat paste.
- Persisted run history (currently an in-memory `RunStore` per process, `app/storage.py` —
  fine for a prototype, not for 5,000/week) and a moderation queue UI for the rare
  reject-after-2-attempts case rather than just surfacing the failure.
- A real billed Gemini project for the pipeline's actual submitted run, so the primary
  Gemini compositing path — not the classical fallback — is what's demonstrated end to end;
  the classical path's existence and the reasoning above is itself part of what I'd defend
  on a call, but it's a fallback, not the intended primary experience.
