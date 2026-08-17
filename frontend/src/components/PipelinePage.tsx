import { useState } from "react"
import { runPipeline } from "../api"
import type { PipelineRunResult } from "../types"
import { RunControls } from "./RunControls"
import { SummaryStats } from "./SummaryStats"
import { VenueCard } from "./VenueCard"
import { RejectedList } from "./RejectedList"

export function PipelinePage() {
  const [result, setResult] = useState<PipelineRunResult | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleRun(targetCount: number, maxCandidates: number) {
    setIsRunning(true)
    setError(null)
    try {
      const response = await runPipeline(targetCount, maxCandidates)
      setResult(response.result)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline run failed.")
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <RunControls onRun={handleRun} isRunning={isRunning} />

      {error && (
        <div
          className="rounded-xl border px-5 py-4 text-sm"
          style={{ borderColor: "var(--bad-soft)", background: "var(--bad-soft)", color: "var(--bad)" }}
        >
          {error}
        </div>
      )}

      {!result && !isRunning && !error && (
        <div
          className="rounded-xl border border-dashed px-5 py-10 text-center text-sm"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
        >
          Run the pipeline to discover candidate venues, capture their frontage, and generate composited visuals.
        </div>
      )}

      {isRunning && !result && (
        <div
          className="rounded-xl border px-5 py-10 text-center text-sm"
          style={{ borderColor: "var(--line)", background: "var(--surface)", color: "var(--ink-muted)" }}
        >
          Screening venues around London and generating visuals — sit tight.
        </div>
      )}

      {result && (
        <>
          <SummaryStats result={result} />
          <div className="flex flex-col gap-5">
            {result.results.map((r, i) => (
              <VenueCard key={r.venue.venue_id} result={r} index={i} />
            ))}
          </div>
          <RejectedList rejected={result.rejected_venues} />
        </>
      )}
    </div>
  )
}
