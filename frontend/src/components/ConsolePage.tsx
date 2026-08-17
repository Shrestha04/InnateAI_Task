import { useState } from "react"
import { PipelinePage } from "./PipelinePage"
import { DemoPage } from "./DemoPage"

type Tab = "pipeline" | "demo"

export function ConsolePage() {
  const [tab, setTab] = useState<Tab>("pipeline")

  return (
    <div className="min-h-screen pt-28">
      <div className="mx-auto max-w-6xl px-6 pb-2">
        <span className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--ink-muted)" }}>
          Innate AI · Prospecting engine
        </span>
        <h1 className="font-display mt-1 text-2xl font-semibold">Storefront capture &amp; visualisation</h1>
        <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
          Finds independent London venues with bare frontages, captures a real entrance photo, and composites the
          client's planters onto it — end to end, unattended.
        </p>
      </div>
      <main className="mx-auto flex max-w-6xl flex-col gap-5 px-6 py-6">
        <div className="flex gap-1 border-b" style={{ borderColor: "var(--line)" }}>
          {(["pipeline", "demo"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="-mb-px border-b-2 px-3 py-2 text-sm font-medium"
              style={{
                borderColor: tab === t ? "var(--accent)" : "transparent",
                color: tab === t ? "var(--accent)" : "var(--ink-muted)",
              }}
            >
              {t === "pipeline" ? "Prospecting pipeline" : "Compositing demo"}
            </button>
          ))}
        </div>

        {tab === "pipeline" ? <PipelinePage /> : <DemoPage />}
      </main>
      <footer className="mx-auto max-w-6xl px-6 py-8 text-xs" style={{ color: "var(--ink-muted)" }}>
        Prototype for internal review. Frontage imagery is sourced live per run; see design.md for the imagery-rights
        position before any outreach use.
      </footer>
    </div>
  )
}
