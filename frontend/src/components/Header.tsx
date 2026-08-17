import { NavLink } from "react-router-dom"

const LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/app", label: "Console", end: false },
  { to: "/results", label: "Results", end: false },
]

export function Header() {
  return (
    <header
      className="fixed inset-x-0 top-0 z-[500] flex items-center justify-between px-6 py-6 md:px-10 md:py-8"
      style={{ mixBlendMode: "difference", color: "#fff" }}
    >
      <NavLink to="/" data-cursor="true" className="font-display text-lg font-semibold tracking-tight">
        Storefront&nbsp;Prospecting
      </NavLink>
      <nav className="flex items-center gap-6">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            data-cursor="true"
            className={({ isActive }) =>
              `font-display text-sm font-medium uppercase tracking-wide transition-opacity ${
                isActive ? "opacity-100" : "opacity-60 hover:opacity-100"
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}
