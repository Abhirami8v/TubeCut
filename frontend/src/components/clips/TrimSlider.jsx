import { useCallback, useRef, useState } from 'react'
import { formatTimecode } from '../../lib/api'

/**
 * TrimSlider
 *
 * Visual timeline-style trim control: a track representing the full
 * (un-trimmed) clip duration, with draggable start/end handles. Calls
 * onChange continuously while dragging and onCommit once the drag
 * ends, so the parent can debounce the actual /trim API call.
 */
export default function TrimSlider({ duration, trimStart, trimEnd, onChange, onCommit }) {
  const trackRef = useRef(null)
  const [dragging, setDragging] = useState(null) // 'start' | 'end' | null

  const pxToTime = useCallback(
    (clientX) => {
      const track = trackRef.current
      if (!track) return 0
      const rect = track.getBoundingClientRect()
      const fraction = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
      return fraction * duration
    },
    [duration]
  )

  const handlePointerDown = (handle) => (e) => {
    e.preventDefault()
    setDragging(handle)

    const handleMove = (moveEvent) => {
      const time = pxToTime(moveEvent.clientX)
      if (handle === 'start') {
        onChange({ start: Math.min(time, trimEnd - 0.3), end: trimEnd })
      } else {
        onChange({ start: trimStart, end: Math.max(time, trimStart + 0.3) })
      }
    }
    const handleUp = () => {
      setDragging(null)
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerup', handleUp)
      onCommit()
    }
    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerup', handleUp)
  }

  const startPct = (trimStart / duration) * 100
  const endPct = (trimEnd / duration) * 100

  return (
    <div className="w-full select-none">
      <div className="flex items-center justify-between mb-2 font-mono text-xs text-[var(--color-text-dim)]">
        <span>{formatTimecode(trimStart)}</span>
        <span>{formatTimecode(trimEnd - trimStart)} selected</span>
        <span>{formatTimecode(trimEnd)}</span>
      </div>

      <div ref={trackRef} className="relative h-12 rounded-lg bg-[var(--color-surface-2)] border border-[var(--color-border)] overflow-hidden">
        {/* waveform-style ticks for visual texture */}
        <div className="absolute inset-0 flex items-center px-1 gap-[2px] opacity-30 pointer-events-none">
          {Array.from({ length: 80 }).map((_, i) => (
            <span
              key={i}
              className="flex-1 bg-[var(--color-text-faint)] rounded-full"
              style={{ height: `${20 + Math.abs(Math.sin(i * 0.7)) * 60}%` }}
            />
          ))}
        </div>

        {/* dimmed regions outside selection */}
        <div className="absolute inset-y-0 left-0 bg-black/50" style={{ width: `${startPct}%` }} />
        <div className="absolute inset-y-0 right-0 bg-black/50" style={{ width: `${100 - endPct}%` }} />

        {/* active selection border */}
        <div
          className="absolute inset-y-0 border-y-2 border-[var(--color-accent)]"
          style={{ left: `${startPct}%`, width: `${endPct - startPct}%` }}
        />

        {/* handles */}
        <Handle pct={startPct} dragging={dragging === 'start'} onPointerDown={handlePointerDown('start')} />
        <Handle pct={endPct} dragging={dragging === 'end'} onPointerDown={handlePointerDown('end')} />
      </div>
    </div>
  )
}

function Handle({ pct, dragging, onPointerDown }) {
  return (
    <div
      onPointerDown={onPointerDown}
      className={`absolute top-0 bottom-0 w-3 -ml-1.5 cursor-ew-resize flex items-center justify-center group ${
        dragging ? 'z-20' : 'z-10'
      }`}
      style={{ left: `${pct}%` }}
    >
      <div
        className={`w-1.5 h-full rounded-full bg-[var(--color-accent)] transition-transform ${
          dragging ? 'scale-x-150' : 'group-hover:scale-x-125'
        }`}
      />
    </div>
  )
}
