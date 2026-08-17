import type { ScoredVenue } from "../types"

export function RejectedList({ rejected }: { rejected: ScoredVenue[] }) {
  if (rejected.length === 0) return null

  return (
    <details className="rounded-xl border" style={{ borderColor: "var(--line)", background: "var(--surface)" }}>
      <summary className="cursor-pointer select-none px-5 py-4 text-sm font-semibold">
        {rejected.length} candidate{rejected.length === 1 ? "" : "s"} rejected before selection — expand
      </summary>
      <ul className="flex flex-col gap-0 border-t" style={{ borderColor: "var(--line)" }}>
        {rejected.map((r) => (
          <li
            key={r.venue.venue_id}
            className="flex flex-wrap items-start justify-between gap-2 border-b px-5 py-3 last:border-b-0"
            style={{ borderColor: "var(--line)" }}
          >
            <div>
              <p className="text-sm font-medium">{r.venue.name}</p>
              <p className="text-xs" style={{ color: "var(--ink-muted)" }}>
                {r.venue.address ?? "Address unresolved"}
                {r.venue.postcode ? ` · ${r.venue.postcode}` : ""}
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--ink-muted)" }}>
                {r.fit.reasoning}
              </p>
            </div>
            <span className="font-mono-ui shrink-0 text-xs" style={{ color: "var(--ink-muted)" }}>
              score {r.fit.score.toFixed(2)}
            </span>
          </li>
        ))}
      </ul>
    </details>
  )
}
