interface MarqueeProps {
  items: string[]
  className?: string
  accentEvery?: number
}

export function Marquee({ items, className = "", accentEvery = 0 }: MarqueeProps) {
  const content = [...items, ...items]
  return (
    <div className={`overflow-hidden ${className}`} aria-hidden="true">
      <div className="marquee-track">
        {content.map((item, i) => (
          <span
            key={i}
            className="font-display shrink-0 whitespace-nowrap px-6 text-2xl uppercase leading-none md:text-3xl"
            style={{ color: accentEvery > 0 && i % accentEvery === 0 ? "var(--accent)" : "var(--ink)" }}
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}
