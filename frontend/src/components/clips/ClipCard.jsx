import { useNavigate } from 'react-router-dom'
import { Play, Palette, Scissors, Download, Smartphone, Monitor, AlertCircle, Loader2 } from 'lucide-react'
import ScoreHeat from '../ui/ScoreHeat'
import Button from '../ui/Button'
import { downloadUrl, formatDuration } from '../../lib/api'

export default function ClipCard({ clip }) {
  const navigate = useNavigate()

  const goToEditor = (tab) => navigate(`/clips/${clip.clip_id}`, { state: { tab } })

  return (
    <div className="group rounded-3xl border border-[#2A2633] bg-[#141318] overflow-hidden hover:border-[#C45EFF]/40 hover:shadow-[0_10px_30px_-15px_rgba(196,94,255,0.25)] transition-all duration-300 flex flex-col h-full">
      {/* Aspect Ratio Video Thumbnail Section */}
      <div
        className="relative bg-[#0D0C0F] cursor-pointer overflow-hidden shrink-0 border-b border-[#2A2633]"
        style={{ aspectRatio: clip.is_vertical ? '9 / 16' : '16 / 9' }}
        onClick={() => goToEditor('preview')}
      >
        {clip.thumbnail_url ? (
          <img
            src={clip.thumbnail_url}
            alt={clip.title}
            className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-500 ease-out"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[var(--color-text-faint)] bg-gradient-to-br from-[#1E1C22] to-[#0D0C0F]">
            <Play size={32} strokeWidth={1.5} className="text-[#C45EFF]/40 animate-pulse" />
          </div>
        )}

        {/* Hover overlay with blurred play button */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center backdrop-blur-[2px]">
          <span className="w-14 h-14 rounded-full bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center shadow-2xl scale-95 group-hover:scale-100 transition-transform duration-300">
            <Play size={20} className="text-white ml-1" fill="white" />
          </span>
        </div>

        {/* Floating Badges */}
        <div className="absolute top-3 left-3 flex items-center gap-1.5 z-10">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#0D0C0F]/80 backdrop-blur border border-[#2A2633]/60 px-2.5 py-1 text-[10px] font-mono text-white font-semibold">
            {clip.is_vertical ? <Smartphone size={11} className="text-[#C45EFF]" /> : <Monitor size={11} className="text-sky-400" />}
            {formatDuration(clip.duration)}
          </span>
        </div>

        <div className="absolute top-3 right-3 z-10">
          <RenderStatusBadge status={clip.render_status} />
        </div>
      </div>

      {/* Info Card Content */}
      <div className="p-5 flex flex-col flex-1 justify-between gap-4">
        <div className="space-y-2">
          <h3 
            onClick={() => goToEditor('preview')} 
            className="font-display font-bold text-base text-white hover:text-[#C45EFF] leading-snug cursor-pointer transition-colors line-clamp-2"
          >
            {clip.title}
          </h3>

          <p className="text-xs text-[var(--color-text-dim)] line-clamp-3 leading-relaxed">
            {clip.transcript_text}
          </p>
        </div>

        {/* Metric Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          <ScoreHeat label="Hook" score={clip.hook_score} size="sm" />
          <ScoreHeat label="Viral" score={clip.viral_score} size="sm" />
        </div>

        {/* Action Panel */}
        <div className="flex items-center gap-2 pt-2 border-t border-[#2A2633]/50">
          <Button 
            variant="secondary" 
            size="sm" 
            className="flex-1 rounded-xl bg-[#1E1C22] border-[#2A2633] text-white hover:bg-[#2A2730] hover:text-[#C45EFF] transition-all" 
            onClick={() => goToEditor('preview')}
          >
            <Play size={12} fill="currentColor" /> Play
          </Button>
          
          <Button 
            variant="secondary" 
            size="sm" 
            className="rounded-xl bg-[#1E1C22] border-[#2A2633] text-white hover:bg-[#2A2730] hover:text-[#C45EFF] p-2"
            onClick={() => goToEditor('captions')} 
            title="Style captions"
          >
            <Palette size={13} />
          </Button>
          
          <Button 
            variant="secondary" 
            size="sm" 
            className="rounded-xl bg-[#1E1C22] border-[#2A2633] text-white hover:bg-[#2A2730] hover:text-[#C45EFF] p-2"
            onClick={() => goToEditor('trim')} 
            title="Trim / Crop"
          >
            <Scissors size={13} />
          </Button>

          {clip.download_url && (
            <a
              href={downloadUrl(clip.download_url)}
              download
              title="Download MP4"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center justify-center rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] text-white hover:opacity-90 shadow-[0_0_12px_rgba(196,94,255,0.2)] text-xs p-2.5 transition-all"
            >
              <Download size={13} strokeWidth={2.5} />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

function RenderStatusBadge({ status }) {
  if (status === 'ready') return null
  const labels = { pending: 'Queued', rendering: 'Rendering', failed: 'Failed' }
  const colors = {
    pending: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-500',
    rendering: 'border-[#C45EFF]/40 bg-[#C45EFF]/15 text-[#C45EFF]',
    failed: 'border-[#FF5A79]/30 bg-[#FF5A79]/10 text-[#FF5A79]',
  }
  const icons = {
    pending: <Loader2 size={10} className="animate-spin shrink-0" />,
    rendering: <Loader2 size={10} className="animate-spin shrink-0" />,
    failed: <AlertCircle size={10} className="shrink-0" />,
  }
  
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold bg-[#0D0C0F]/90 backdrop-blur font-mono ${colors[status] || colors.pending}`}>
      {icons[status]}
      {labels[status] || status}
    </span>
  )
}
