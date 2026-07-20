import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link2, Sparkles, ArrowRight, Video, Languages, Smile } from 'lucide-react'
import { api } from '../lib/api'
import { useJobPolling } from '../hooks/useJobPolling'
import Button from '../components/ui/Button'
import PipelineProgress from '../components/clips/PipelineProgress'
import ClipCard from '../components/clips/ClipCard'

export default function CreateClipPage() {
  const [url, setUrl] = useState('')
  const [jobId, setJobId] = useState(() => localStorage.getItem('active_job_id'))
  const [submitError, setSubmitError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [autoReframe, setAutoReframe] = useState(true)
  const [defaultClipCount, setDefaultClipCount] = useState(3)
  const navigate = useNavigate()

  const { job, error: pollError, notFound } = useJobPolling(jobId)

  useEffect(() => {
    api.getMe()
      .then((me) => {
        setAutoReframe(me.settings.auto_reframe_default)
        setDefaultClipCount(me.settings.default_clip_count)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (notFound) {
      setJobId(null)
    }
  }, [notFound])

  useEffect(() => {
    if (jobId) {
      localStorage.setItem('active_job_id', jobId)
    } else {
      localStorage.removeItem('active_job_id')
    }
  }, [jobId])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return

    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await api.generateClips({
        url: url.trim(),
        auto_reframe: autoReframe,
        target_clip_count: defaultClipCount
      })
      setJobId(res.job_id)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const isProcessing = job && job.status !== 'completed'
  const isDone = job && job.status === 'completed'

  return (
    <div className="px-6 md:px-12 py-12 max-w-6xl mx-auto min-h-screen flex flex-col justify-start relative">
      {/* Background soft glowing blur */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#C45EFF]/3 blur-[140px] pointer-events-none" />

      {!jobId && (
        <div className="flex-1 flex flex-col justify-center items-center py-12 md:py-20 gap-12 relative z-10">
          
          {/* Tag & Hero */}
          <div className="space-y-4 text-center max-w-3xl">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#2A2633] bg-[#1E1C22] px-3.5 py-1.5 text-xs text-[var(--color-text-dim)] font-mono font-medium shadow-[0_4px_12px_rgba(0,0,0,0.3)]">
              <Sparkles size={12} className="text-[#C45EFF]" />
              transcribe · score hooks · auto-reframe · caption
            </span>
            
            <h1 className="font-display font-extrabold text-4xl sm:text-5xl md:text-6xl tracking-tight text-white leading-[1.1] pt-2">
              Turn long videos into <br className="hidden sm:inline" />
              <span className="bg-gradient-to-r from-[#C45EFF] to-[#D88EFF] bg-clip-text text-transparent shadow-sm">
                viral shorts
              </span>{' '}
              instantly
            </h1>
            
            <p className="text-[var(--color-text-dim)] text-base sm:text-lg max-w-xl mx-auto leading-relaxed pt-2">
              Paste a link. TubeCut automatically extracts key hooks, tracks faces for vertical 9:16 reframe, and burns in custom subtitles.
            </p>
          </div>

          {/* URL Input Form */}
          <form onSubmit={handleSubmit} className="w-full max-w-2xl px-2">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 rounded-2xl border border-[#2A2633] bg-[#141318]/90 p-2.5 focus-within:border-[#C45EFF]/60 focus-within:shadow-[0_0_25px_rgba(196,94,255,0.15)] transition-all duration-300">
              <div className="flex items-center gap-3 flex-1 px-2.5 py-2">
                <Link2 size={20} className="text-[var(--color-text-faint)] shrink-0" />
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Paste YouTube or video URL..."
                  className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-[var(--color-text-faint)]"
                />
              </div>
              <Button 
                type="submit" 
                disabled={submitting || !url.trim()} 
                className="shrink-0 rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] text-white hover:opacity-90 transition-all font-semibold tracking-wide py-3 px-6 shadow-[0_4px_20px_rgba(196,94,255,0.25)] flex items-center justify-center gap-2"
              >
                {submitting ? 'Starting...' : 'Generate Clips'}
                {!submitting && <ArrowRight size={16} strokeWidth={2.5} />}
              </Button>
            </div>

            <label className="flex items-center gap-2.5 mt-5 justify-center text-xs text-[var(--color-text-dim)] cursor-pointer select-none font-medium hover:text-white transition-colors">
              <input
                type="checkbox"
                checked={autoReframe}
                onChange={(e) => setAutoReframe(e.target.checked)}
                className="rounded border-[#2A2633] bg-[#1E1C22] text-[#C45EFF] focus:ring-0 focus:ring-offset-0 w-4 h-4 accent-[#C45EFF]"
              />
              Auto-reframe to vertical 9:16 layout using intelligent face tracking
            </label>

            {submitError && (
              <p className="mt-4 text-sm text-[#FF5A79] text-center font-medium bg-[#FF5A79]/5 border border-[#FF5A79]/10 rounded-xl py-2 px-4">{submitError}</p>
            )}
          </form>

          {/* Feature Highlights Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl mt-8">
            <div className="border border-[#2A2633] bg-[#141318]/40 rounded-2xl p-6 hover:border-[#C45EFF]/20 transition-colors">
              <div className="w-10 h-10 rounded-xl bg-[#C45EFF]/10 flex items-center justify-center text-[#C45EFF] mb-4">
                <Smile size={20} strokeWidth={2.2} />
              </div>
              <h4 className="font-display font-bold text-base text-white mb-2">AI Hook Extraction</h4>
              <p className="text-xs text-[var(--color-text-dim)] leading-relaxed">
                Analyzes transcripts to detect highly viral, self-contained highlight moments automatically.
              </p>
            </div>
            
            <div className="border border-[#2A2633] bg-[#141318]/40 rounded-2xl p-6 hover:border-[#C45EFF]/20 transition-colors">
              <div className="w-10 h-10 rounded-xl bg-sky-500/10 flex items-center justify-center text-sky-400 mb-4">
                <Video size={20} strokeWidth={2.2} />
              </div>
              <h4 className="font-display font-bold text-base text-white mb-2">Smart Auto-Reframe</h4>
              <p className="text-xs text-[var(--color-text-dim)] leading-relaxed">
                Crops horizontal footage to vertical 9:16 aspect ratio with dynamic target centering.
              </p>
            </div>

            <div className="border border-[#2A2633] bg-[#141318]/40 rounded-2xl p-6 hover:border-[#C45EFF]/20 transition-colors">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-4">
                <Languages size={20} strokeWidth={2.2} />
              </div>
              <h4 className="font-display font-bold text-base text-white mb-2">Dynamic Captions</h4>
              <p className="text-xs text-[var(--color-text-dim)] leading-relaxed">
                Applies eye-catching word-by-word animation presets, outlines, and highlights.
              </p>
            </div>
          </div>
        </div>
      )}

      {isProcessing && job && (
        <div className="flex-1 flex flex-col items-center justify-center py-12 gap-2 relative z-10">
          <p className="text-xs font-mono text-[var(--color-text-dim)] mb-4 truncate max-w-md bg-[#1E1C22] px-4 py-1.5 rounded-full border border-[#2A2633]">
            Target Video: {job.source_title || 'Loading info...'}
          </p>
          <PipelineProgress
            steps={job.steps}
            progressPercent={job.progress_percent}
            currentLabel={job.current_step_label}
            errorMessage={job.status === 'failed' ? job.error_message : null}
          />
          {job.status === 'failed' && (
            <Button
              variant="secondary"
              className="mt-8 rounded-xl bg-[#1E1C22] border-[#2A2633] text-white hover:bg-[#2A2730] px-6 py-2.5"
              onClick={() => {
                setJobId(null)
                setUrl('')
              }}
            >
              Try Another Video
            </Button>
          )}
        </div>
      )}

      {pollError && (
        <p className="text-sm text-[#FF5A79] text-center mt-6 relative z-10">{pollError}</p>
      )}

      {isDone && job && (
        <div className="py-8 relative z-10">
          {/* Done Header Banner */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8 pb-6 border-b border-[#2A2633]">
            <div>
              <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
                Generation Completed
              </span>
              <h2 className="font-display font-extrabold text-3xl text-white tracking-tight mt-1">
                {job.clips.length} Clips Ready
              </h2>
              <p className="text-sm text-[var(--color-text-dim)] mt-1.5 truncate max-w-xl">
                Source: <span className="text-[#F4F3F6] font-medium">{job.source_title}</span>
              </p>
            </div>
            <Button
              variant="secondary"
              className="rounded-xl bg-[#1E1C22] border-[#2A2633] text-white hover:bg-[#2A2730] hover:text-[#C45EFF] px-5 py-2.5 self-stretch md:self-auto text-center"
              onClick={() => {
                setJobId(null)
                setUrl('')
              }}
            >
              Clip another video
            </Button>
          </div>

          {/* Results Grid using items-start to support mixing portrait/landscape aspect ratios smoothly */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 items-start">
            {job.clips
              .slice()
              .sort((a, b) => b.viral_score - a.viral_score)
              .map((clip) => (
                <ClipCard key={clip.clip_id} clip={clip} />
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
