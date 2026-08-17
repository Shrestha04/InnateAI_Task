import { useEffect, useState } from "react"

const DURATION_MS = 900

export function Preloader() {
  const [count, setCount] = useState(0)
  const [visible, setVisible] = useState(true)
  const [mounted, setMounted] = useState(true)

  useEffect(() => {
    const start = performance.now()
    let raf: number

    function tick(now: number) {
      const progress = Math.min((now - start) / DURATION_MS, 1)
      setCount(Math.floor(progress * 100))
      if (progress < 1) {
        raf = requestAnimationFrame(tick)
      } else {
        setVisible(false)
        setTimeout(() => setMounted(false), 500)
      }
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  if (!mounted) return null

  return (
    <div
      className="fixed inset-0 z-[998] flex flex-col items-center justify-center gap-6 transition-opacity duration-500"
      style={{ background: "var(--paper)", opacity: visible ? 1 : 0 }}
      aria-hidden="true"
    >
      <span className="font-display text-sm uppercase tracking-[0.4em]" style={{ color: "var(--ink-muted)" }}>
        Storefront Prospecting
      </span>
      <span className="font-display text-[13vw] leading-none tabular-nums md:text-[8vw]">
        {String(count).padStart(2, "0")}
      </span>
    </div>
  )
}
