import type { VenuePipelineResult } from "../types"
import { StatusBadge } from "./StatusBadge"
import { FrontagePanel } from "./FrontagePanel"
import { CompositePanel } from "./CompositePanel"

const TYPE_LABEL: Record<string, string> = {
  cafe: "Café",
  restaurant: "Restaurant",
  salon: "Salon",
  other: "Other",
}

export function VenueCard({ result, index }: { result: VenuePipelineResult; index: number }) {
  const { venue, fit, frontage, composite, product } = result

  return (
    <article
      className="overflow-hidden rounded-xl border"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
    >
      <header className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4" style={{ borderColor: "var(--line)" }}>
        <div>
          <div className="flex items-center gap-2 text-xs" style={{ color: "var(--ink-muted)" }}>
            <span className="font-mono-ui">{String(index + 1).padStart(2, "0")}</span>
            <span
              className="rounded-full px-2 py-0.5 font-medium"
              style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
            >
              {TYPE_LABEL[venue.venue_type] ?? venue.venue_type}
            </span>
          </div>
          <h3 className="mt-1 text-base font-semibold">{venue.name}</h3>
          <p className="text-sm" style={{ color: "var(--ink-muted)" }}>
            {venue.address ?? "Address unresolved"}
            {venue.postcode ? ` · ${venue.postcode}` : ""}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge accepted={fit.accepted} acceptedLabel="Selected" rejectedLabel="Not selected" />
          <span className="font-mono-ui text-xs" style={{ color: "var(--ink-muted)" }}>
            fit score {fit.score.toFixed(2)}
          </span>
        </div>
      </header>

      <div className="px-5 py-3 text-sm" style={{ color: "var(--ink-muted)" }}>
        {fit.reasoning}
      </div>

      {frontage && (
        <div className="grid gap-5 border-t px-5 py-5 md:grid-cols-2" style={{ borderColor: "var(--line)" }}>
          <FrontagePanel frontage={frontage} />
          {composite && product ? (
            <CompositePanel composite={composite} frontage={frontage} product={product} />
          ) : (
            <div>
              <h4 className="mb-2 text-sm font-semibold">Composited visual</h4>
              <div
                className="rounded-lg border border-dashed px-3 py-4 text-xs"
                style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
              >
                Skipped — no usable frontage image to composite onto.
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  )
}
