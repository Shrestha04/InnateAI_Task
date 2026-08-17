import { useState } from "react"

interface RunControlsProps {
  onRun: (targetCount: number, maxCandidates: number) => void
  isRunning: boolean
}

export function RunControls({ onRun, isRunning }: RunControlsProps) {
  const [targetCount, setTargetCount] = useState(2)
  const [maxCandidates, setMaxCandidates] = useState(5)

  return (
    <div
      className="flex flex-wrap items-end gap-4 rounded-xl border px-5 py-4"
      style={{ borderColor: "var(--line)", background: "var(--surface)" }}
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
          Venues to select
        </span>
        <input
          type="number"
          min={1}
          max={10}
          value={targetCount}
          onChange={(e) => setTargetCount(Number(e.target.value))}
          disabled={isRunning}
          className="w-24 rounded-md border px-2.5 py-1.5 font-mono-ui text-sm"
          style={{ borderColor: "var(--line-strong)" }}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-xs font-medium" style={{ color: "var(--ink-muted)" }}>
          Candidates to screen
        </span>
        <input
          type="number"
          min={5}
          max={60}
          value={maxCandidates}
          onChange={(e) => setMaxCandidates(Number(e.target.value))}
          disabled={isRunning}
          className="w-24 rounded-md border px-2.5 py-1.5 font-mono-ui text-sm"
          style={{ borderColor: "var(--line-strong)" }}
        />
      </label>
      <button
        onClick={() => onRun(targetCount, maxCandidates)}
        disabled={isRunning}
        className="rounded-md px-4 py-2 text-sm font-semibold transition-opacity disabled:opacity-60"
        style={{ background: "var(--accent)", color: "#0a0a0b" }}
      >
        {isRunning ? "Running pipeline…" : "Run prospecting pipeline"}
      </button>
      {isRunning ? (
        <span className="text-xs" style={{ color: "var(--ink-muted)" }}>
          Discovering venues, capturing frontages, and generating composites — this can take a couple of minutes.
        </span>
      ) : (
        <span className="text-xs" style={{ color: "var(--ink-muted)" }}>
          Each candidate costs several Gemini calls (fit check, frontage checks, composite QA) — keep these low on a
          free-tier Gemini key, which caps out at a small number of requests per day.
        </span>
      )}
    </div>
  )
}
