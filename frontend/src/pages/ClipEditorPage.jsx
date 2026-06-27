import { useEffect, useRef, useState, useCallback } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Smartphone, Monitor, Loader2 } from 'lucide-react'
import { api, downloadUrl, formatDuration } from '../lib/api'
import ScoreHeat from '../components/ui/ScoreHeat'
import Button from '../components/ui/Button'
import TrimSlider from '../components/clips/TrimSlider'
import CaptionTimeline from '../components/captions/CaptionTimeline'
import StylePickerRow from '../components/styles/StylePickerRow'

const TABS = [
  { key: 'preview', label: 'Preview' },
  { key: 'captions', label: 'Captions' },
  { key: 'trim', label: 'Trim / Crop' },
]

export default function ClipEditorPage() {
  const { clipId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  const [clip, setClip] = useState(null)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState(location.state?.tab || 'preview')
  const [playheadTime, setPlayheadTime] = useState(0)
  const [selectedBlockId, setSelectedBlockId] = useState(null)

  const [trimDraft, setTrimDraft] = useState(null) // { start, end } relative to original clip
  const [trimSaving, setTrimSaving] = useState(false)
  const [styleApplying, setStyleApplying] = useState(false)

  const videoRef = useRef(null)
  const saveCaptionTimer = useRef(null)

  const loadClip = useCallback(() => {
    return api
      .getClip(clipId)
      .then((data) => {
        setClip(data)
        const originalDuration = data.end_time - data.start_time
        setTrimDraft({
          start: data.trim_start_time - data.start_time,
          end: data.trim_end_time - data.start_time,
        })
        return data
      })
      .catch((err) => setError(err.message))
  }, [clipId])

  useEffect(() => {
    loadClip()
  }, [loadClip])

  if (error) {
    return (
      <div className="px-10 py-10">
        <p className="text-sm text-[var(--color-danger)]">{error}</p>
      </div>
    )
  }

  if (!clip || !trimDraft) {
    return (
      <div className="px-10 py-10 max-w-5xl mx-auto">
        <div className="aspect-video rounded-2xl shimmer max-w-2xl mx-auto" />
      </div>
    )
  }

  const originalDuration = clip.end_time - clip.start_time

  async function handleApplyStyle(styleId) {
    setStyleApplying(true)
    try {
      const updated = await api.applyStyle(clipId, { style_id: styleId })
      setClip(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setStyleApplying(false)
    }
  }

  async function commitTrim() {
    setTrimSaving(true)
    try {
      await api.trimClip(clipId, { trim_start_time: trimDraft.start, trim_end_time: trimDraft.end })
      await loadClip()
    } catch (err) {
      setError(err.message)
    } finally {
      setTrimSaving(false)
    }
  }

  function handleCaptionTextChange(blockId, text) {
    setClip((prev) => ({
      ...prev,
      caption_blocks: prev.caption_blocks.map((b) => (b.id === blockId ? { ...b, text } : b)),
    }))
    debounceSaveCaption(blockId, { text })
  }

  function handleCaptionRetime(blockId, patch) {
    setClip((prev) => ({
      ...prev,
      caption_blocks: prev.caption_blocks.map((b) => (b.id === blockId ? { ...b, ...patch } : b)),
    }))
    debounceSaveCaption(blockId, patch)
  }

  function debounceSaveCaption(blockId, patch) {
    if (saveCaptionTimer.current) clearTimeout(saveCaptionTimer.current)
    saveCaptionTimer.current = setTimeout(async () => {
      try {
        const updated = await api.updateCaption(clipId, { block_id: blockId, ...patch })
        setClip(updated)
      } catch (err) {
        setError(err.message)
      }
    }, 500)
  }

  async function handleSplit(blockId, splitAt) {
    try {
      const updated = await api.splitCaption(clipId, { block_id: blockId, split_at_time: splitAt })
      setClip(updated)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleMergeWithNext(blockId) {
    const sorted = [...clip.caption_blocks].sort((a, b) => a.order_index - b.order_index)
    const idx = sorted.findIndex((b) => b.id === blockId)
    const next = sorted[idx + 1]
    if (!next) return
    try {
      const updated = await api.mergeCaption(clipId, { first_block_id: blockId, second_block_id: next.id })
      setClip(updated)
      setSelectedBlockId(blockId)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleAddBlock(start, end) {
    try {
      const updated = await api.createCaption(clipId, {
        start_time: start,
        end_time: end,
        text: 'New caption',
      })
      setClip(updated)
      const sorted = [...updated.caption_blocks].sort((a, b) => a.start_time - b.start_time)
      const created = sorted.find((b) => Math.abs(b.start_time - start) < 0.05) || sorted[sorted.length - 1]
      if (created) setSelectedBlockId(created.id)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDeleteBlock(blockId) {
    try {
      const updated = await api.deleteCaption(clipId, { block_id: blockId })
      setClip(updated)
      setSelectedBlockId(null)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="px-10 py-8 max-w-6xl mx-auto">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-dim)] hover:text-[var(--color-text)] mb-6"
      >
        <ArrowLeft size={15} /> Back
      </button>

      <div className="flex items-start justify-between gap-6 mb-6 flex-wrap">
        <div>
          <h1 className="font-display font-semibold text-2xl mb-2">{clip.title}</h1>
          <div className="flex items-center gap-2 flex-wrap">
            <ScoreHeat label="Hook" score={clip.hook_score} size="sm" />
            <ScoreHeat label="Confidence" score={clip.confidence_score} size="sm" />
            <ScoreHeat label="Viral" score={clip.viral_score} size="sm" />
            <span className="inline-flex items-center gap-1 text-xs text-[var(--color-text-faint)] font-mono">
              {clip.is_vertical ? <Smartphone size={12} /> : <Monitor size={12} />}
              {formatDuration(clip.duration)}
            </span>
          </div>
        </div>

        {clip.download_url && (
          <a
            href={downloadUrl(clip.download_url)}
            download
            className="inline-flex items-center justify-center rounded-lg bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] px-4 py-2 gap-2 text-sm font-medium"
          >
            <Download size={15} /> Download MP4
          </a>
        )}
      </div>

      <div className="flex gap-1 border-b border-[var(--color-border)] mb-6">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              tab === t.key
                ? 'border-[var(--color-accent)] text-[var(--color-text)]'
                : 'border-transparent text-[var(--color-text-dim)] hover:text-[var(--color-text)]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-8">
        <div className="space-y-3">
          <div
            className="rounded-2xl overflow-hidden border border-[var(--color-border)] bg-black mx-auto"
            style={{
              aspectRatio: clip.is_vertical ? '9 / 16' : '16 / 9',
              maxWidth: clip.is_vertical ? 320 : '100%',
            }}
          >
            {clip.preview_url ? (
              <video
                ref={videoRef}
                src={clip.preview_url}
                controls
                className="w-full h-full object-contain"
                onTimeUpdate={(e) => setPlayheadTime(e.target.currentTime)}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-[var(--color-text-faint)]">
                <Loader2 className="animate-spin" />
              </div>
            )}
          </div>
          {clip.render_status !== 'ready' && (
            <p className="text-xs text-center text-[var(--color-text-dim)] font-mono">
              {clip.render_status === 'rendering' ? 'Re-rendering…' : clip.render_status}
            </p>
          )}
        </div>

        <div>
          {tab === 'preview' && (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
              <p className="text-xs font-medium text-[var(--color-text-dim)] uppercase tracking-wide mb-2">
                Transcript
              </p>
              <p className="text-sm leading-relaxed text-[var(--color-text)]">{clip.transcript_text}</p>
              {clip.ai_reason && (
                <>
                  <p className="text-xs font-medium text-[var(--color-text-dim)] uppercase tracking-wide mb-2 mt-5">
                    Why this clip
                  </p>
                  <p className="text-sm leading-relaxed text-[var(--color-text-dim)]">{clip.ai_reason}</p>
                </>
              )}
            </div>
          )}

          {tab === 'captions' && (
            <div className="space-y-6">
              <div>
                <p className="text-xs font-medium text-[var(--color-text-dim)] uppercase tracking-wide mb-2">
                  Caption style
                </p>
                <StylePickerRow
                  appliedStyleId={clip.applied_style_id}
                  onApply={handleApplyStyle}
                  applying={styleApplying}
                />
              </div>

              <div>
                <p className="text-xs font-medium text-[var(--color-text-dim)] uppercase tracking-wide mb-2">
                  Timeline
                </p>
                <CaptionTimeline
                  blocks={[...clip.caption_blocks].sort((a, b) => a.order_index - b.order_index)}
                  duration={clip.duration}
                  selectedId={selectedBlockId}
                  onSelect={setSelectedBlockId}
                  onTextChange={handleCaptionTextChange}
                  onRetime={handleCaptionRetime}
                  onSplit={handleSplit}
                  onMergeWithNext={handleMergeWithNext}
                  onAddBlock={handleAddBlock}
                  onDeleteBlock={handleDeleteBlock}
                  playheadTime={playheadTime}
                  onSeek={(t) => {
                    if (videoRef.current) videoRef.current.currentTime = t
                  }}
                />
              </div>
            </div>
          )}

          {tab === 'trim' && (
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-5">
              <p className="text-xs font-medium text-[var(--color-text-dim)] uppercase tracking-wide">
                Trim window
              </p>
              <TrimSlider
                duration={originalDuration}
                trimStart={trimDraft.start}
                trimEnd={trimDraft.end}
                onChange={setTrimDraft}
                onCommit={commitTrim}
              />
              <p className="text-xs text-[var(--color-text-faint)]">
                Drag the handles to adjust the in/out points. The clip re-renders automatically when you
                release.
              </p>
              {trimSaving && (
                <p className="text-xs text-[var(--color-accent)] inline-flex items-center gap-1.5">
                  <Loader2 size={12} className="animate-spin" /> Re-rendering clip…
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
