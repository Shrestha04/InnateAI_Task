import { useEffect, useRef } from "react"

export function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null)
  const ringRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const mq = window.matchMedia("(hover: hover) and (pointer: fine)")
    if (!mq.matches) return

    document.body.classList.add("has-custom-cursor")
    const pos = { x: window.innerWidth / 2, y: window.innerHeight / 2 }
    let hovering = false

    function render() {
      const { x, y } = pos
      if (dotRef.current) dotRef.current.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`
      if (ringRef.current) {
        const scale = hovering ? 1.7 : 1
        ringRef.current.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%) scale(${scale})`
      }
    }

    function handleMove(e: MouseEvent) {
      pos.x = e.clientX
      pos.y = e.clientY
      render()
    }

    function handleOver(e: MouseEvent) {
      hovering = Boolean((e.target as HTMLElement).closest?.("a, button, [data-cursor]"))
      render()
    }

    window.addEventListener("mousemove", handleMove)
    window.addEventListener("mouseover", handleOver)
    return () => {
      document.body.classList.remove("has-custom-cursor")
      window.removeEventListener("mousemove", handleMove)
      window.removeEventListener("mouseover", handleOver)
    }
  }, [])

  return (
    <div className="pointer-events-none fixed inset-0 z-[999] hidden md:block" aria-hidden="true">
      <div ref={dotRef} className="fixed left-0 top-0 h-1.5 w-1.5 rounded-full" style={{ background: "var(--ink)" }} />
      <div
        ref={ringRef}
        className="fixed left-0 top-0 h-8 w-8 rounded-full border transition-transform duration-150 ease-out"
        style={{ borderColor: "var(--ink)" }}
      />
    </div>
  )
}
