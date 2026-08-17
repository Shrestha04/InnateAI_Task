import { Link } from "react-router-dom"
import { Marquee } from "./Marquee"
import { PipelineGallery } from "./PipelineGallery"

const TICKER = ["Independent cafés", "•", "Restaurants", "•", "Salons", "•", "Bare frontages", "•", "London", "•"]

export function HomePage() {
  return (
    <div>
      <section className="relative flex min-h-screen flex-col justify-between overflow-hidden px-6 pb-10 pt-32 md:px-10 md:pt-40">
        <div className="pointer-events-none absolute inset-0">
          <img
            src="/products/planter-corten-modular.jpg"
            alt=""
            className="h-full w-full object-cover opacity-25"
          />
          <div
            className="absolute inset-0"
            style={{ background: "linear-gradient(180deg, rgba(10,10,12,0.55) 0%, rgba(10,10,12,0.88) 65%, var(--paper) 100%)" }}
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(60% 50% at 50% 0%, rgba(140,233,154,0.14), transparent 70%), radial-gradient(40% 40% at 85% 20%, rgba(140,233,154,0.08), transparent 70%)",
            }}
          />
        </div>
        <div className="relative">
          <span className="font-display text-xs uppercase tracking-[0.4em]" style={{ color: "var(--ink-muted)" }}>
            Innate AI · Prospecting engine
          </span>
          <h1 className="font-display mt-4 max-w-4xl text-[13vw] font-medium uppercase leading-[0.95] md:text-[6.4vw]">
            Every bare doorway is a pitch that hasn't been made yet.
          </h1>
          <p className="mt-6 max-w-lg text-base" style={{ color: "var(--ink-muted)" }}>
            An automated engine that finds independent London venues with under-dressed frontages, captures a real
            photo of their actual entrance, and shows the owner exactly what it could look like — planted.
          </p>
          <div className="mt-8 flex items-center gap-4">
            <Link
              to="/app"
              data-cursor="true"
              className="animate-slow-blink font-display rounded-full px-6 py-3 text-sm font-semibold uppercase tracking-wide transition-transform hover:scale-105 hover:animate-none"
              style={{ background: "var(--accent)", color: "#0a0a0b" }}
            >
              Open the console
            </Link>
            <a
              href="#gallery"
              data-cursor="true"
              className="font-display text-sm font-medium uppercase tracking-wide underline decoration-1 underline-offset-4"
              style={{ color: "var(--ink-muted)" }}
            >
              See how it works
            </a>
          </div>
        </div>

        <div className="relative flex items-end justify-between gap-6">
          <div className="overflow-hidden">
            <Marquee items={TICKER} accentEvery={2} />
          </div>
          <div className="hidden shrink-0 flex-col items-center gap-2 text-xs uppercase tracking-widest md:flex" style={{ color: "var(--ink-muted)" }}>
            <span>Scroll</span>
            <span className="h-8 w-px animate-bounce" style={{ background: "var(--line-strong)" }} />
          </div>
        </div>
      </section>

      <div id="gallery">
        <PipelineGallery />
      </div>

      <section className="border-t px-6 py-24 text-center md:px-10" style={{ borderColor: "var(--line)" }}>
        <Link to="/app" data-cursor="true" className="group inline-block">
          <h2 className="font-display uppercase leading-[0.9] text-[9vw] font-medium transition-colors duration-500 group-hover:text-[var(--accent)] md:text-[7.5vw]">
            Let's get you planted
          </h2>
        </Link>
        <div className="mt-10 overflow-hidden border-y py-6" style={{ borderColor: "var(--line)" }}>
          <Marquee items={["Storefront Prospecting", "•", "Innate AI", "•"]} />
        </div>
        <p className="mx-auto mt-8 max-w-lg text-xs" style={{ color: "var(--ink-muted)" }}>
          Prototype for internal review. Frontage imagery is sourced live per run; see design.md for the
          imagery-rights position before any outreach use.
        </p>
      </section>
    </div>
  )
}
