import { useState } from "react"

interface ResultRow {
  slug: string
  name: string
  address: string
}

const RESULTS: ResultRow[] = [
  { slug: "26-furnival-street", name: "26 Furnival Street", address: "26 Furnival Street, London EC4A 1JS" },
  { slug: "a-toca", name: "A Toca", address: "339-343 Wandsworth Road, London SW8 2JH" },
]

function ImageSlot({
  src,
  alt,
  filename,
  downloadName,
}: {
  src: string
  alt: string
  filename: string
  downloadName?: string
}) {
  const [missing, setMissing] = useState(false)

  if (missing) {
    return (
      <div
        className="flex aspect-[4/3] w-full flex-col items-center justify-center gap-1 rounded-lg border border-dashed px-3 text-center"
        style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
      >
        <span className="text-xs font-medium">Not yet added</span>
        <span className="font-mono-ui text-[11px]">results/{filename}</span>
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
      <img src={src} alt={alt} className="aspect-[4/3] w-full object-cover" onError={() => setMissing(true)} />
      {downloadName && (
        <a
          href={src}
          download={downloadName}
          className="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] font-semibold shadow-lg transition-transform hover:scale-105"
          style={{ background: "var(--accent)", color: "#0a0a0b" }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 3v13m0 0-4-4m4 4 4-4M5 21h14" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Download
        </a>
      )}
    </div>
  )
}

export function ResultsPage() {
  return (
    <div className="min-h-screen pt-28">
      <div className="mx-auto max-w-6xl px-6 pb-2">
        <span className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--ink-muted)" }}>
          Innate AI · Prospecting engine
        </span>
        <h1 className="font-display mt-1 text-2xl font-semibold">Results showcase</h1>
        <p className="mt-1 max-w-2xl text-sm" style={{ color: "var(--ink-muted)" }}>
          Real independent London restaurants, captured live via the same Mapillary/OSM frontage pipeline the app
          uses.
        </p>
      </div>

      <main className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-6">
        {RESULTS.map((r) => (
          <div key={r.slug} className="rounded-xl border p-5" style={{ borderColor: "var(--line)", background: "var(--surface)" }}>
            <h3 className="text-sm font-semibold">{r.name}</h3>
            <p className="mb-3 text-xs" style={{ color: "var(--ink-muted)" }}>
              {r.address}
            </p>
            <div className="grid grid-cols-2 gap-3">
              <figure className="m-0">
                <ImageSlot
                  src={`/results/${r.slug}-before.jpg`}
                  alt={`${r.name} — captured frontage`}
                  filename={`${r.slug}-before.jpg`}
                />
                <figcaption className="mt-1.5 text-[11px] font-medium" style={{ color: "var(--ink-muted)" }}>
                  Captured frontage
                </figcaption>
              </figure>
              <figure className="m-0">
                <ImageSlot
                  src={`/results/${r.slug}-after.jpg`}
                  alt={`${r.name} — with planters`}
                  filename={`${r.slug}-after.jpg`}
                  downloadName={`${r.slug}-planters.jpg`}
                />
                <figcaption className="mt-1.5 text-[11px] font-medium" style={{ color: "var(--ink-muted)" }}>
                  With planters
                </figcaption>
              </figure>
            </div>
          </div>
        ))}
      </main>
    </div>
  )
}
