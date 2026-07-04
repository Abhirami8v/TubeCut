import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Link2, Sparkles, ArrowRight } from 'lucide-react'
import { api } from '../lib/api'
import { useJobPolling } from '../hooks/useJobPolling'
import Button from '../components/ui/Button'
import PipelineProgress from '../components/clips/PipelineProgress'
import ClipCard from '../components/clips/ClipCard'

export default function CreateClipPage() {
  const [url, setUrl] = useState('')
  const [jobId, setJobId] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [autoReframe, setAutoReframe] = useState(true)
  const navigate = useNavigate()

  const { job, error: pollError } = useJobPolling(jobId)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return

    setSubmitting(true)
    setSubmitError(null)
    try {
      const res = await api.generateClips({ url: url.trim(), auto_reframe: autoReframe })
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
    <div className="px-10 py-10 max-w-5xl mx-auto">
      {!jobId && (
        <div className="min-h-[70vh] flex flex-col items-center justify-center text-center gap-8">
          <div className="space-y-3">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-2)] px-3 py-1 text-xs text-[var(--color-text-dim)] font-mono">
              <Sparkles size={12} className="text-[var(--color-accent)]" />
              transcribe · score hooks · auto-reframe · caption
            </span>
            <h1 className="font-display font-semibold text-4xl tracking-tight">
              Turn any video into clips worth posting
            </h1>
            <p className="text-[var(--color-text-dim)] max-w-md mx-auto">
              Paste a link. TubeCut finds the hooks, reframes for vertical, and burns in captions
              automatically.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="w-full max-w-xl">
            <div className="flex items-center gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-2 focus-within:border-[var(--color-accent)] transition-colors">
              <Link2 size={18} className="text-[var(--color-text-faint)] ml-2 shrink-0" />
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste a YouTube or video URL…"
                className="flex-1 bg-transparent outline-none text-sm placeholder:text-[var(--color-text-faint)] py-2"
              />
              <Button type="submit" disabled={submitting || !url.trim()} className="shrink-0">
                {submitting ? 'Starting…' : 'Generate Clips'}
                {!submitting && <ArrowRight size={15} />}
              </Button>
            </div>

            <label className="flex items-center gap-2 mt-4 justify-center text-xs text-[var(--color-text-dim)] cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoReframe}
                onChange={(e) => setAutoReframe(e.target.checked)}
                className="accent-[var(--color-accent)]"
              />
              Auto-reframe to vertical 9:16 with face tracking
            </label>

            {submitError && (
              <p className="mt-3 text-sm text-[var(--color-danger)] text-center">{submitError}</p>
            )}
          </form>
        </div>
      )}

      {isProcessing && job && (
        <div className="min-h-[70vh] flex flex-col items-center justify-center gap-2">
          <p className="text-xs font-mono text-[var(--color-text-faint)] mb-6 truncate max-w-md">
            {job.source_title || 'Processing your video'}
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
              className="mt-6"
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
        <p className="text-sm text-[var(--color-danger)] text-center mt-4">{pollError}</p>
      )}

      {isDone && job && (
        <div className="py-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-display font-semibold text-2xl">{job.clips.length} clips ready</h2>
              <p className="text-sm text-[var(--color-text-dim)] mt-1 truncate max-w-md">
                from "{job.source_title}"
              </p>
            </div>
            <Button
              variant="secondary"
              onClick={() => {
                setJobId(null)
                setUrl('')
              }}
            >
              New video
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
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
