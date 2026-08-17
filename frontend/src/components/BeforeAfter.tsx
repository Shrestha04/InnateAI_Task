interface BeforeAfterProps {
  beforeUrl: string
  afterUrl: string
  beforeLabel?: string
  afterLabel?: string
  downloadFileName?: string
}

export function BeforeAfter({
  beforeUrl,
  afterUrl,
  beforeLabel = "Captured frontage",
  afterLabel = "With planters",
  downloadFileName = "planters-visual.jpg",
}: BeforeAfterProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <figure className="m-0">
        <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
          <img src={beforeUrl} alt={beforeLabel} className="aspect-[4/3] w-full object-cover" />
        </div>
        <figcaption className="mt-1.5 text-[11px] font-medium" style={{ color: "var(--ink-muted)" }}>
          {beforeLabel}
        </figcaption>
      </figure>
      <figure className="m-0">
        <div className="relative overflow-hidden rounded-lg border" style={{ borderColor: "var(--line)" }}>
          <img src={afterUrl} alt={afterLabel} className="aspect-[4/3] w-full object-cover" />
          <a
            href={afterUrl}
            download={downloadFileName}
            className="absolute bottom-2 right-2 flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] font-semibold shadow-lg transition-transform hover:scale-105"
            style={{ background: "var(--accent)", color: "#0a0a0b" }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 3v13m0 0-4-4m4 4 4-4M5 21h14" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Download
          </a>
        </div>
        <figcaption className="mt-1.5 text-[11px] font-medium" style={{ color: "var(--ink-muted)" }}>
          {afterLabel}
        </figcaption>
      </figure>
    </div>
  )
}
