import { StatusBadge } from "./StatusBadge"

interface Attempt {
  accepted: boolean
  reasoning: string
}

interface AttemptLogProps<T extends Attempt> {
  attempts: T[]
  renderLabel: (attempt: T, index: number) => string
}

export function AttemptLog<T extends Attempt>({ attempts, renderLabel }: AttemptLogProps<T>) {
  if (attempts.length === 0) return null

  return (
    <details className="group mt-3">
      <summary
        className="cursor-pointer select-none text-xs font-medium"
        style={{ color: "var(--ink-muted)" }}
      >
        {attempts.length} automated attempt{attempts.length === 1 ? "" : "s"} logged — expand
      </summary>
      <ol className="mt-2 flex flex-col gap-2">
        {attempts.map((attempt, index) => (
          <li
            key={index}
            className="rounded-md border px-3 py-2 text-xs"
            style={{ borderColor: "var(--line)", background: "var(--paper)" }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono-ui" style={{ color: "var(--ink-muted)" }}>
                {renderLabel(attempt, index)}
              </span>
              <StatusBadge accepted={attempt.accepted} acceptedLabel="Passed" rejectedLabel="Rejected" />
            </div>
            <p className="mt-1" style={{ color: "var(--ink-muted)" }}>
              {attempt.reasoning}
            </p>
          </li>
        ))}
      </ol>
    </details>
  )
}
