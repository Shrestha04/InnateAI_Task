import type { PipelineRunResult } from "../types"

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono-ui text-2xl font-semibold">{value}</span>
      <span className="text-xs" style={{ color: "var(--ink-muted)" }}>
        {label}
      </span>
    </div>
  )
}

export function SummaryStats({ result }: { result: PipelineRunResult }) {
  const selected = result.results.length
  const frontageUsable = result.results.filter((r) => r.frontage?.accepted).length
  const compositeReady = result.results.filter((r) => r.composite?.accepted).length

  return (
    <div
      className="grid grid-cols-2 gap-6 rounded-xl border px-5 py-4 sm:grid-cols-4"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
    >
      <Stat label="Candidates screened" value={result.candidates_considered} />
      <Stat label="Selected as good fits" value={selected} />
      <Stat label="Usable frontage found" value={frontageUsable} />
      <Stat label="Ready-to-send composites" value={compositeReady} />
    </div>
  )
}
