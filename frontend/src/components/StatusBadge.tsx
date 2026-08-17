interface StatusBadgeProps {
  accepted: boolean
  acceptedLabel?: string
  rejectedLabel?: string
}

export function StatusBadge({ accepted, acceptedLabel = "Accepted", rejectedLabel = "Rejected" }: StatusBadgeProps) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{
        background: accepted ? "var(--good-soft)" : "var(--bad-soft)",
        color: accepted ? "var(--good)" : "var(--bad)",
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: accepted ? "var(--good)" : "var(--bad)" }}
      />
      {accepted ? acceptedLabel : rejectedLabel}
    </span>
  )
}
