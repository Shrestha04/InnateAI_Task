import type { CompositeResult, FrontageResult, Product } from "../types"
import { toAssetUrl } from "../api"
import { StatusBadge } from "./StatusBadge"
import { BeforeAfter } from "./BeforeAfter"
import { AttemptLog } from "./AttemptLog"

const CHECK_LABEL: Record<string, string> = {
  building_unaltered: "Building unaltered",
  product_matches_reference: "Matches reference product",
  scale_plausible: "Scale plausible",
  perspective_plausible: "Perspective plausible",
  has_grounding_and_shadow: "Grounded with shadow",
  no_visual_artifacts: "No artifacts",
}

export function CompositePanel({
  composite,
  frontage,
  product,
}: {
  composite: CompositeResult
  frontage: FrontageResult
  product: Product
}) {
  const bestAttempt = composite.attempts.find((a) => a.accepted) ?? composite.attempts.at(-1)

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold">Composited visual</h4>
        <div className="flex items-center gap-2">
          {composite.accepted && (
            <span
              className="rounded-full px-2 py-0.5 text-[11px] font-medium"
              style={{
                background: composite.method === "classical" ? "var(--warn-soft)" : "var(--accent-soft)",
                color: composite.method === "classical" ? "var(--warn)" : "var(--accent)",
              }}
            >
              {composite.method === "classical" ? "Classical fallback" : "Gemini generation"}
            </span>
          )}
          <StatusBadge accepted={composite.accepted} acceptedLabel="Ready to send" rejectedLabel="Rejected by QA gate" />
        </div>
      </div>

      {composite.accepted && composite.method === "classical" && (
        <div
          className="mb-2 rounded-md border px-3 py-2 text-xs"
          style={{ borderColor: "var(--warn-soft)", background: "var(--warn-soft)", color: "var(--warn)" }}
        >
          Gemini's image-generation model wasn't available on this key (free-tier quota), so this used the
          free local cutout-and-shadow fallback instead — a real product cutout at the correct scale, but not
          photorealistic AI compositing. See design.md for details.
        </div>
      )}

      {composite.accepted && composite.final_image_url && frontage.image_url ? (
        <BeforeAfter
          beforeUrl={toAssetUrl(frontage.image_url)}
          afterUrl={toAssetUrl(composite.final_image_url)}
          downloadFileName={`${frontage.venue_id.replace(/[/\\]/g, "_")}-${product.id}-planters.jpg`}
        />
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {frontage.image_url && (
            <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
              <img src={toAssetUrl(frontage.image_url)} alt="Frontage" className="aspect-[4/3] w-full object-cover" />
            </div>
          )}
          {bestAttempt?.image_url && (
            <div className="overflow-hidden rounded-lg border opacity-70" style={{ borderColor: "var(--bad)" }}>
              <img src={toAssetUrl(bestAttempt.image_url)} alt="Rejected composite" className="aspect-[4/3] w-full object-cover" />
            </div>
          )}
        </div>
      )}

      <div className="mt-2 text-xs" style={{ color: "var(--ink-muted)" }}>
        <span className="font-medium" style={{ color: "var(--ink)" }}>
          Product: {product.name}
        </span>
        <p className="mt-0.5">{composite.scale_note}</p>
        <p className="mt-1">{composite.reasoning}</p>
      </div>

      {bestAttempt && Object.keys(bestAttempt.checks).length > 0 && (
        <div className="mt-3 grid grid-cols-2 gap-1.5 sm:grid-cols-3">
          {Object.entries(bestAttempt.checks).map(([key, passed]) => (
            <div
              key={key}
              className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px]"
              style={{
                borderColor: passed ? "var(--good-soft)" : "var(--bad-soft)",
                background: passed ? "var(--good-soft)" : "var(--bad-soft)",
                color: passed ? "var(--good)" : "var(--bad)",
              }}
            >
              <span
                className="h-1.5 w-1.5 shrink-0 rounded-full"
                style={{ background: passed ? "var(--good)" : "var(--bad)" }}
              />
              {CHECK_LABEL[key] ?? key}
            </div>
          ))}
        </div>
      )}

      <AttemptLog
        attempts={composite.attempts.map((a) => ({ accepted: a.accepted, reasoning: a.reasoning }))}
        renderLabel={(_a, i) => `Generation attempt ${composite.attempts[i].attempt_number}`}
      />
    </div>
  )
}
