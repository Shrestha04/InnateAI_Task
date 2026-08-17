import type { FrontageResult } from "../types"
import { toAssetUrl } from "../api"
import { StatusBadge } from "./StatusBadge"
import { AttemptLog } from "./AttemptLog"

const SOURCE_LABEL: Record<string, string> = {
  mapillary: "Mapillary street imagery",
  osm_photo: "OpenStreetMap photo",
  website_og: "Venue website",
}

export function FrontagePanel({ frontage }: { frontage: FrontageResult }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-semibold">Frontage capture</h4>
        <StatusBadge accepted={frontage.accepted} acceptedLabel="Usable" rejectedLabel="No usable frame" />
      </div>

      {frontage.accepted && frontage.image_url ? (
        <>
          <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
            <img src={toAssetUrl(frontage.image_url)} alt="Venue frontage" className="aspect-[4/3] w-full object-cover" />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs" style={{ color: "var(--ink-muted)" }}>
            <span className="font-medium" style={{ color: "var(--ink)" }}>
              Source: {SOURCE_LABEL[frontage.final_source ?? ""] ?? frontage.final_source}
            </span>
            {frontage.heading_deg !== null && (
              <span className="font-mono-ui">heading {frontage.heading_deg.toFixed(0)}°</span>
            )}
            {frontage.fov_deg !== null && <span className="font-mono-ui">fov {frontage.fov_deg.toFixed(0)}°</span>}
            {frontage.entrance_zoomed && (
              <span
                className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
              >
                Zoomed to entrance
              </span>
            )}
          </div>
          <p className="mt-1 text-xs" style={{ color: "var(--ink-muted)" }}>
            {frontage.reasoning}
          </p>
        </>
      ) : (
        <div
          className="rounded-lg border border-dashed px-3 py-4 text-xs"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
        >
          {frontage.reasoning}
        </div>
      )}

      <AttemptLog
        attempts={frontage.attempts}
        renderLabel={(a) =>
          `${SOURCE_LABEL[a.source] ?? a.source}${a.heading_deg !== null && a.heading_deg !== undefined ? ` · heading ${a.heading_deg.toFixed(0)}°` : ""}`
        }
      />
    </div>
  )
}
