import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

/**
 * StylePickerRow
 *
 * Horizontal scroll of style swatches for quickly applying a preset
 * (or custom style) to the current clip from inside the clip editor.
 */
export default function StylePickerRow({ appliedStyleId, onApply, applying }) {
  const [styles, setStyles] = useState(null)

  useEffect(() => {
    api.listStyles().then(setStyles).catch(() => setStyles([]))
  }, [])

  if (!styles) {
    return <div className="h-16 rounded-lg shimmer" />
  }

  return (
    <div className="flex gap-2.5 overflow-x-auto pb-2">
      {styles.map((style) => {
        const isActive = style.id === appliedStyleId
        return (
          <button
            key={style.id}
            disabled={applying}
            onClick={() => onApply(style.id)}
            className={`shrink-0 flex flex-col items-center gap-1.5 px-3 py-2.5 rounded-lg border transition-colors disabled:opacity-50 ${
              isActive
                ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10'
                : 'border-[var(--color-border)] bg-[var(--color-surface-2)] hover:border-[var(--color-text-faint)]'
            }`}
          >
            <span
              className="text-[10px] font-bold px-1.5 py-0.5 rounded"
              style={{
                color: style.text_color,
                background: '#000',
                textTransform: style.uppercase ? 'uppercase' : 'none',
              }}
            >
              Aa
            </span>
            <span className="text-[11px] whitespace-nowrap font-medium">{style.name}</span>
          </button>
        )
      })}
    </div>
  )
}
