import { useRef, useState } from 'react'
import { Scissors, Combine, Plus, Trash2 } from 'lucide-react'
import { formatTimecode } from '../../lib/api'

/**
 * CaptionTimeline
 *
 * The signature editing surface: caption blocks laid out on a
 * horizontal time ruler, each independently draggable on its edges to
 * retime, clickable to edit text inline, with split/merge/delete
 * actions and a way to add a brand new block from scratch (needed when
 * auto-transcription produced nothing, or to fill a gap).
 * This is intentionally NOT a modal — it's the main content of the
 * "Captions" tab in the clip editor.
 */
export default function CaptionTimeline({
  blocks,
  duration,
  selectedId,
  onSelect,
  onTextChange,
  onRetime,
  onSplit,
  onMergeWithNext,
  onAddBlock,
  onDeleteBlock,
  playheadTime,
  onSeek,
}) {
  const trackRef = useRef(null)
  const [dragging, setDragging] = useState(null) // { blockId, edge }

  const pxToTime = (clientX) => {
    const track = trackRef.current
    if (!track) return 0
    const rect = track.getBoundingClientRect()
    const fraction = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
    return fraction * duration
  }

  const startDrag = (block, edge) => (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging({ blockId: block.id, edge })

    const handleMove = (moveEvent) => {
      const time = pxToTime(moveEvent.clientX)
      if (edge === 'start') {
        onRetime(block.id, { start_time: Math.min(time, block.end_time - 0.1) })
      } else {
        onRetime(block.id, { end_time: Math.max(time, block.start_time + 0.1) })
      }
    }
    const handleUp = () => {
      setDragging(null)
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerup', handleUp)
    }
    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerup', handleUp)
  }

  const playheadPct = duration ? (playheadTime / duration) * 100 : 0

  function handleAddAtPlayhead() {
    const start = Math.max(0, Math.min(playheadTime, duration - 0.5))
    const end = Math.min(duration, start + 1.5)
    onAddBlock(start, end)
  }

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1.5 px-1">
        <span className="text-[10px] font-mono text-[var(--color-text-faint)]">00:00.00</span>
        <button
          onClick={handleAddAtPlayhead}
          className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] px-2 py-1 rounded-md hover:bg-[var(--color-accent)]/10"
        >
          <Plus size={13} /> Add caption at playhead
        </button>
        <span className="text-[10px] font-mono text-[var(--color-text-faint)]">{formatTimecode(duration)}</span>
      </div>

      <div
        ref={trackRef}
        className="relative h-24 rounded-lg bg-[var(--color-surface-2)] border border-[var(--color-border)] cursor-pointer"
        onClick={(e) => {
          if (dragging) return
          onSeek(pxToTime(e.clientX))
        }}
      >
        {/* ruler ticks */}
        <div className="absolute inset-0 flex pointer-events-none">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="flex-1 border-r border-[var(--color-border-soft)] last:border-r-0" />
          ))}
        </div>

        {/* playhead */}
        <div
          className="absolute top-0 bottom-0 w-px bg-[var(--color-accent)] z-30 pointer-events-none"
          style={{ left: `${playheadPct}%` }}
        >
          <div className="w-2.5 h-2.5 rounded-full bg-[var(--color-accent)] -ml-[5px] -mt-1" />
        </div>

        {/* empty state, shown directly on the track so it's impossible to miss */}
        {blocks.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-xs text-[var(--color-text-faint)]">
              No captions yet — click "Add caption at playhead" above, or click anywhere on this track.
            </span>
          </div>
        )}

        {/* blocks */}
        {blocks.map((block) => {
          const leftPct = (block.start_time / duration) * 100
          const widthPct = ((block.end_time - block.start_time) / duration) * 100
          const isSelected = block.id === selectedId

          return (
            <div
              key={block.id}
              onClick={(e) => {
                e.stopPropagation()
                onSelect(block.id)
              }}
              className={`absolute top-3 bottom-3 rounded-md px-2 flex items-center overflow-hidden transition-colors cursor-pointer border ${
                isSelected
                  ? 'bg-[var(--color-accent)]/25 border-[var(--color-accent)]'
                  : 'bg-[var(--color-surface-3)] border-[var(--color-border)] hover:border-[var(--color-text-faint)]'
              }`}
              style={{ left: `${leftPct}%`, width: `${Math.max(widthPct, 1.5)}%` }}
            >
              <span className="text-[11px] truncate font-medium pointer-events-none">{block.text}</span>

              <div
                onPointerDown={startDrag(block, 'start')}
                className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-[var(--color-accent)]/60"
              />
              <div
                onPointerDown={startDrag(block, 'end')}
                className="absolute right-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-[var(--color-accent)]/60"
              />
            </div>
          )
        })}

        {/* empty track click target — lets you click directly on the ruler to add a block there */}
        {blocks.length === 0 && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              const start = Math.max(0, pxToTime(e.clientX) - 0.5)
              const end = Math.min(duration, start + 1.5)
              onAddBlock(start, end)
            }}
            className="absolute inset-0 w-full h-full cursor-pointer bg-transparent"
            aria-label="Add caption block here"
          />
        )}
      </div>

      {selectedId && (
        <CaptionBlockEditor
          block={blocks.find((b) => b.id === selectedId)}
          onTextChange={onTextChange}
          onSplit={onSplit}
          onMergeWithNext={onMergeWithNext}
          onDelete={onDeleteBlock}
          hasNext={blocks.findIndex((b) => b.id === selectedId) < blocks.length - 1}
        />
      )}
    </div>
  )
}

function CaptionBlockEditor({ block, onTextChange, onSplit, onMergeWithNext, onDelete, hasNext }) {
  if (!block) return null
  const mid = (block.start_time + block.end_time) / 2

  return (
    <div className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs text-[var(--color-text-dim)]">
          {formatTimecode(block.start_time)} → {formatTimecode(block.end_time)}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => onSplit(block.id, mid)}
            className="inline-flex items-center gap-1 text-xs text-[var(--color-text-dim)] hover:text-[var(--color-text)] px-2 py-1 rounded-md hover:bg-[var(--color-surface-2)]"
          >
            <Scissors size={12} /> Split at midpoint
          </button>
          {hasNext && (
            <button
              onClick={() => onMergeWithNext(block.id)}
              className="inline-flex items-center gap-1 text-xs text-[var(--color-text-dim)] hover:text-[var(--color-text)] px-2 py-1 rounded-md hover:bg-[var(--color-surface-2)]"
            >
              <Combine size={12} /> Merge with next
            </button>
          )}
          <button
            onClick={() => onDelete(block.id)}
            className="inline-flex items-center gap-1 text-xs text-[var(--color-danger)] hover:text-red-400 px-2 py-1 rounded-md hover:bg-[var(--color-danger)]/10"
          >
            <Trash2 size={12} /> Delete
          </button>
        </div>
      </div>
      <textarea
        value={block.text}
        onChange={(e) => onTextChange(block.id, e.target.value)}
        rows={2}
        autoFocus
        className="input resize-none font-medium"
      />
    </div>
  )
}
