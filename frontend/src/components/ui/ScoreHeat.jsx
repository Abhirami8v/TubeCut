/**
 * ScoreHeat
 *
 * Renders a 0-100 score as a small heat-colored chip. Color is derived
 * from the score itself (cool gray -> amber -> red), so the chip's
 * color always encodes real information rather than decoration.
 */
function heatColor(score) {
  if (score >= 75) return 'var(--color-heat-high)'
  if (score >= 50) return 'var(--color-heat-mid)'
  return 'var(--color-heat-low)'
}

export default function ScoreHeat({ label, score, size = 'md' }) {
  const color = heatColor(score)
  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-1'

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-md border font-mono ${sizeClasses}`}
      style={{
        borderColor: `${color}40`,
        background: `${color}14`,
        color,
      }}
      title={`${label}: ${score}/100`}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {label && <span className="text-[var(--color-text-dim)] font-sans">{label}</span>}
      <span className="font-semibold">{Math.round(score)}</span>
    </div>
  )
}
