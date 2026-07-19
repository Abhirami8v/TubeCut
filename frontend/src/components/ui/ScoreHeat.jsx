function heatColor(score) {
  if (score >= 75) return 'var(--color-heat-high)'
  if (score >= 50) return 'var(--color-heat-mid)'
  return 'var(--color-heat-low)'
}

export default function ScoreHeat({ label, score, size = 'md' }) {
  const color = heatColor(score)
  const sizeClasses = size === 'sm' ? 'text-[10px] px-2.5 py-0.5 rounded-full' : 'text-xs px-3 py-1 rounded-full'

  return (
    <div
      className={`inline-flex items-center gap-1.5 border font-mono transition-all duration-300 hover:scale-[1.02] ${sizeClasses}`}
      style={{
        borderColor: `${color}25`,
        background: `${color}0C`,
        color,
        boxShadow: `0 0 12px ${color}05`,
      }}
      title={`${label}: ${score}/100`}
    >
      <span 
        className="w-1.5 h-1.5 rounded-full animate-pulse shrink-0" 
        style={{ 
          background: color, 
          boxShadow: `0 0 8px ${color}` 
        }} 
      />
      {label && <span className="text-[var(--color-text-dim)] font-sans font-medium">{label}:</span>}
      <span className="font-bold">{Math.round(score)}</span>
    </div>
  )
}
