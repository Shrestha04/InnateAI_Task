import { useEffect, useRef } from "react"
import { Link } from "react-router-dom"

interface Step {
  label: string
  title: string
  description: string
  gradient: string
  image: string
  tall: boolean
}

const STEPS: Step[] = [
  {
    label: "Discovery",
    title: "Find venues",
    description: "OpenStreetMap + Overpass surface independent cafés, restaurants and salons — chains filtered out.",
    gradient: "linear-gradient(135deg, rgba(43,109,79,0.75), rgba(12,42,28,0.9))",
    image: "/products/planter-black-cylinder.jpg",
    tall: true,
  },
  {
    label: "Vision",
    title: "Screen for fit",
    description: "Gemini judges each frontage as street-facing, bare, and a genuine planter opportunity.",
    gradient: "linear-gradient(135deg, rgba(58,110,165,0.75), rgba(13,36,56,0.9))",
    image: "/products/planter-white-cube.jpg",
    tall: false,
  },
  {
    label: "Capture",
    title: "Get the frontage",
    description: "Mapillary frames ranked by heading match, falling back to OSM photos and the venue's own site.",
    gradient: "linear-gradient(135deg, rgba(194,131,58,0.75), rgba(58,35,8,0.9))",
    image: "/products/planter-corten-modular.jpg",
    tall: true,
  },
  {
    label: "Framing",
    title: "Zoom to the entrance",
    description: "The actual doorway is detected and the frame is cropped tight around it, not the whole facade.",
    gradient: "linear-gradient(135deg, rgba(75,123,191,0.75), rgba(15,31,56,0.9))",
    image: "/products/planter-black-cylinder.jpg",
    tall: false,
  },
  {
    label: "Generation",
    title: "Composite planters",
    description: "The client's real product photo is scaled against the doorway and placed in believably, shadow and all.",
    gradient: "linear-gradient(135deg, rgba(95,174,98,0.75), rgba(18,48,24,0.9))",
    image: "/products/planter-corten-modular.jpg",
    tall: true,
  },
  {
    label: "Quality",
    title: "Six-check QA gate",
    description: "Scale, perspective, grounding, artifacts — every generation is rejected or passed automatically.",
    gradient: "linear-gradient(135deg, rgba(209,161,58,0.75), rgba(58,44,12,0.9))",
    image: "/products/planter-white-cube.jpg",
    tall: false,
  },
  {
    label: "Try it",
    title: "Open the console",
    description: "Run the live pipeline yourself, or drop in your own frontage photo in the compositing playground.",
    gradient: "linear-gradient(135deg, rgba(140,233,154,0.7), rgba(18,48,24,0.92))",
    image: "/products/planter-corten-modular.jpg",
    tall: true,
  },
]

export function PipelineGallery() {
  const sectionRef = useRef<HTMLElement>(null)
  const trackRef = useRef<HTMLDivElement>(null)
  const dotsRef = useRef<Array<HTMLSpanElement | null>>([])
  const tickingRef = useRef(false)

  useEffect(() => {
    function update() {
      tickingRef.current = false
      const section = sectionRef.current
      const track = trackRef.current
      if (!section || !track) return

      const rect = section.getBoundingClientRect()
      const total = section.offsetHeight - window.innerHeight
      const progress = total > 0 ? Math.min(Math.max(-rect.top / total, 0), 1) : 0
      const maxTranslate = Math.max(track.scrollWidth - window.innerWidth, 0)
      track.style.transform = `translateX(-${progress * maxTranslate}px)`

      const activeIndex = Math.round(progress * (dotsRef.current.length - 1))
      dotsRef.current.forEach((dot, i) => {
        if (!dot) return
        const active = i === activeIndex
        dot.style.width = active ? "24px" : "6px"
        dot.style.background = active ? "var(--accent)" : "var(--line-strong)"
      })
    }

    function onScroll() {
      if (!tickingRef.current) {
        tickingRef.current = true
        requestAnimationFrame(update)
      }
    }

    window.addEventListener("scroll", onScroll, { passive: true })
    window.addEventListener("resize", onScroll)
    update()
    return () => {
      window.removeEventListener("scroll", onScroll)
      window.removeEventListener("resize", onScroll)
    }
  }, [])

  return (
    <section ref={sectionRef} className="relative" style={{ height: "300vh" }}>
      <div className="sticky top-0 h-screen overflow-hidden border-t" style={{ borderColor: "var(--line)" }}>
        <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-start justify-between px-6 pt-10 md:px-10 md:pt-14">
          <h2 className="font-display text-[9vw] font-medium uppercase leading-[0.95] md:text-[3.2vw]">How it works</h2>
          <div className="hidden items-center gap-1.5 md:flex">
            {STEPS.map((_, i) => (
              <span
                key={i}
                ref={(el) => {
                  dotsRef.current[i] = el
                }}
                className="h-1.5 rounded-full transition-all duration-300"
                style={{ width: 6, background: "var(--line-strong)" }}
              />
            ))}
          </div>
        </div>

        <div className="flex h-full items-center pl-6 md:pl-10">
          <div
            ref={trackRef}
            className="grid auto-cols-[80vw] grid-flow-col grid-rows-2 gap-4 md:auto-cols-[30vw] md:gap-6"
            style={{ willChange: "transform" }}
          >
            {STEPS.map((step) => (
              <GalleryCard key={step.title} step={step} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function GalleryCard({ step }: { step: Step }) {
  return (
    <Link
      to="/app"
      data-cursor="true"
      className="group relative overflow-hidden rounded-2xl border border-white/15"
      style={{ height: step.tall ? "68vh" : "32vh", gridRow: step.tall ? "span 2 / span 2" : undefined }}
    >
      <div className="absolute inset-0 transition-transform duration-700 ease-out group-hover:scale-110">
        <img src={step.image} alt="" className="h-full w-full object-cover" />
        <div className="absolute inset-0" style={{ background: step.gradient, mixBlendMode: "multiply" }} />
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/15 to-transparent" />
      <div className="absolute inset-0 flex flex-col justify-end p-6">
        <span className="text-xs uppercase tracking-widest text-white/70">{step.label}</span>
        <h3 className="font-display mt-1 text-2xl font-medium leading-tight text-white md:text-3xl">{step.title}</h3>
        <p className="mt-2 max-w-xs text-sm text-white/80">{step.description}</p>
      </div>
    </Link>
  )
}
