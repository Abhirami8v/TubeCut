import { useNavigate } from 'react-router-dom'
import { Play, Palette, Scissors, Download, Smartphone, Monitor } from 'lucide-react'
import ScoreHeat from '../ui/ScoreHeat'
import Button from '../ui/Button'
import { downloadUrl, formatDuration } from '../../lib/api'

export default function ClipCard({ clip }) {
  const navigate = useNavigate()

  const goToEditor = (tab) => navigate(`/clips/${clip.clip_id}`, { state: { tab } })

  return (
    <div className="group rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden hover:border-[var(--color-border)]/80 hover:-translate-y-0.5 transition-all duration-200">
      <div
        className="relative bg-[var(--color-surface-2)] cursor-pointer overflow-hidden"
        style={{ aspectRatio: clip.is_vertical ? '9 / 16' : '16 / 9' }}
        onClick={() => goToEditor('preview')}
      >
        {clip.thumbnail_url ? (
          <img
            src={clip.thumbnail_url}
            alt={clip.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[var(--color-text-faint)]">
            <Play size={28} />
          </div>
        )}

        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
          <span className="opacity-0 group-hover:opacity-100 transition-opacity w-12 h-12 rounded-full bg-white/90 flex items-center justify-center">
            <Play size={18} className="text-black ml-0.5" fill="black" />
          </span>
        </div>

        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded-md bg-black/60 backdrop-blur px-1.5 py-0.5 text-[10px] font-mono text-white">
            {clip.is_vertical ? <Smartphone size={10} /> : <Monitor size={10} />}
            {formatDuration(clip.duration)}
          </span>
        </div>

        <div className="absolute top-2 right-2">
          <RenderStatusDot status={clip.render_status} />
        </div>
      </div>

      <div className="p-4 flex flex-col gap-3">
        <h3 className="font-display font-semibold text-sm leading-snug line-clamp-2">{clip.title}</h3>

        <p className="text-xs text-[var(--color-text-dim)] line-clamp-2 leading-relaxed">
          {clip.transcript_text}
        </p>

        <div className="flex items-center gap-2 flex-wrap">
          <ScoreHeat label="Hook" score={clip.hook_score} size="sm" />
          <ScoreHeat label="Viral" score={clip.viral_score} size="sm" />
        </div>

        <div className="flex items-center gap-2 pt-1">
          <Button variant="secondary" size="sm" className="flex-1" onClick={() => goToEditor('preview')}>
            <Play size={13} /> Play
          </Button>
          <Button variant="secondary" size="sm" onClick={() => goToEditor('captions')} title="Caption style">
            <Palette size={13} />
          </Button>
          <Button variant="secondary" size="sm" onClick={() => goToEditor('trim')} title="Crop / Trim">
            <Scissors size={13} />
          </Button>
          {clip.download_url && (
            <a
              href={downloadUrl(clip.download_url)}
              download
              title="Download MP4"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center justify-center rounded-lg bg-[var(--color-surface-2)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-[var(--color-surface-3)] text-xs px-2.5 py-1.5"
            >
              <Download size={13} />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

function RenderStatusDot({ status }) {
  if (status === 'ready') return null
  const labels = { pending: 'Queued', rendering: 'Rendering…', failed: 'Failed' }
  const colors = {
    pending: 'bg-[var(--color-text-faint)]',
    rendering: 'bg-[var(--color-accent)] animate-pulse',
    failed: 'bg-[var(--color-danger)]',
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-black/60 backdrop-blur px-2 py-1 text-[10px] text-white">
      <span className={`w-1.5 h-1.5 rounded-full ${colors[status] || colors.pending}`} />
      {labels[status] || status}
    </span>
  )
}
