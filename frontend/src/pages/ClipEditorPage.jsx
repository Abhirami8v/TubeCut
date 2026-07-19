import { useEffect, useRef, useState, useCallback } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Download, Smartphone, Monitor, Loader2, Play, Palette, Scissors } from 'lucide-react'
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

  const [trimDraft, setTrimDraft] = useState(null)
  const [trimSaving, setTrimSaving] = useState(false)
  const [styleApplying, setStyleApplying] = useState(false)

  const videoRef = useRef(null)
  const saveCaptionTimer = useRef(null)

  const loadClip = useCallback(() => {
    return api
      .getClip(clipId)
      .then((data) => {
        setClip(data)
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
      <div className="px-6 md:px-12 py-12 max-w-6xl mx-auto">
        <p className="text-sm text-[#FF5A79] bg-[#FF5A79]/5 border border-[#FF5A79]/10 rounded-xl py-3 px-4">{error}</p>
      </div>
    )
  }

  if (!clip || !trimDraft) {
    return (
      <div className="px-6 md:px-12 py-12 max-w-6xl mx-auto flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="animate-spin text-[#C45EFF]" size={28} />
          <span className="text-sm text-[var(--color-text-dim)] font-mono">Loading Studio Workspace...</span>
        </div>
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
    <div className="px-6 md:px-12 py-10 max-w-6xl mx-auto min-h-screen relative">
      {/* Back navigation */}
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-2 text-sm text-[var(--color-text-dim)] hover:text-white mb-8 group transition-colors"
      >
        <ArrowLeft size={16} className="group-hover:-translate-x-0.5 transition-transform" />
        Back to Library
      </button>

      {/* Editor Header Details */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 mb-8 pb-6 border-b border-[#2A2633]">
        <div className="space-y-2.5">
          <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
            Clip Editor
          </span>
          <h1 className="font-display font-extrabold text-3xl text-white tracking-tight leading-tight">
            {clip.title}
          </h1>
          <div className="flex items-center gap-3 flex-wrap">
            <ScoreHeat label="Hook" score={clip.hook_score} size="sm" />
            <ScoreHeat label="Viral" score={clip.viral_score} size="sm" />
            <span className="inline-flex items-center gap-1.5 text-xs text-[var(--color-text-faint)] font-mono font-medium bg-[#141318] px-2.5 py-1 rounded-md border border-[#2A2633]">
              {clip.is_vertical ? <Smartphone size={12} className="text-[#C45EFF]" /> : <Monitor size={12} className="text-sky-400" />}
              {formatDuration(clip.duration)}
            </span>
          </div>
        </div>

        {clip.download_url && (
          <a
            href={downloadUrl(clip.download_url)}
            download
            className="inline-flex items-center justify-center rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] text-white hover:opacity-90 font-bold px-6 py-3 tracking-wide shadow-[0_4px_15px_rgba(196,94,255,0.25)] gap-2 text-sm"
          >
            <Download size={16} strokeWidth={2.5} /> Download MP4
          </a>
        )}
      </div>

      {/* Workspace Tabs */}
      <div className="flex gap-2 border-b border-[#2A2633] mb-8">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-all -mb-px ${
              tab === t.key
                ? 'border-[#C45EFF] text-white font-bold'
                : 'border-transparent text-[var(--color-text-dim)] hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Workspace Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-10 items-start">
        
        {/* Left Side: Video Preview device container */}
        <div className="space-y-4">
          <div
            className="rounded-[32px] overflow-hidden border border-[#2A2633] bg-black mx-auto relative p-3 shadow-2xl"
            style={{
              aspectRatio: clip.is_vertical ? '9 / 16' : '16 / 9',
              maxWidth: clip.is_vertical ? 320 : '100%',
            }}
          >
            {/* Phone speaker mock bezel */}
            {clip.is_vertical && (
              <div className="absolute top-6 left-1/2 -translate-x-1/2 w-14 h-1.5 rounded-full bg-[#2A2633] opacity-60 z-20" />
            )}

            <div className="w-full h-full rounded-[24px] overflow-hidden bg-black relative">
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
                  <Loader2 className="animate-spin text-[#C45EFF]" size={28} />
                </div>
              )}
            </div>
          </div>
          
          {clip.render_status !== 'ready' && (
            <p className="text-[10px] text-center text-[#C45EFF] font-mono font-medium bg-[#C45EFF]/10 border border-[#C45EFF]/20 py-1.5 rounded-xl animate-pulse">
              Re-rendering subtitles overlay on video...
            </p>
          )}
        </div>

        {/* Right Side: Tab Panel Content */}
        <div>
          {tab === 'preview' && (
            <div className="rounded-3xl border border-[#2A2633] bg-[#141318] p-6 space-y-6">
              <div>
                <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
                  Speech Transcription
                </span>
                <p className="text-sm leading-relaxed text-white mt-2 font-medium bg-[#0D0C0F] border border-[#2A2633] p-5 rounded-2xl">
                  {clip.transcript_text}
                </p>
              </div>
              
              {clip.ai_reason && (
                <div>
                  <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
                    AI Highlight Reasoning
                  </span>
                  <p className="text-sm leading-relaxed text-[var(--color-text-dim)] mt-2 bg-[#0D0C0F] border border-[#2A2633] p-5 rounded-2xl">
                    {clip.ai_reason}
                  </p>
                </div>
              )}
            </div>
          )}

          {tab === 'captions' && (
            <div className="space-y-8 bg-[#141318] border border-[#2A2633] p-6 rounded-3xl">
              <div>
                <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold block mb-4">
                  Select Caption Preset
                </span>
                <StylePickerRow
                  appliedStyleId={clip.applied_style_id}
                  onApply={handleApplyStyle}
                  applying={styleApplying}
                />
              </div>

              <div>
                <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold block mb-4">
                  Adjust Captions Timeline
                </span>
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
            <div className="rounded-3xl border border-[#2A2633] bg-[#141318] p-6 space-y-6">
              <div>
                <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
                  Crop & Trim Timeline
                </span>
                <div className="mt-4 bg-[#0D0C0F] border border-[#2A2633] p-6 rounded-2xl">
                  <TrimSlider
                    duration={originalDuration}
                    trimStart={trimDraft.start}
                    trimEnd={trimDraft.end}
                    onChange={setTrimDraft}
                    onCommit={commitTrim}
                  />
                </div>
              </div>
              
              <p className="text-xs text-[var(--color-text-dim)] leading-relaxed">
                Drag the horizontal bounds to shift the start and end of the clip sequence. Releases will automatically cue the cloud video processor to generate a cropped snippet.
              </p>
              
              {trimSaving && (
                <div className="inline-flex items-center gap-2 text-xs text-[#C45EFF] bg-[#C45EFF]/10 border border-[#C45EFF]/20 py-2 px-4 rounded-xl animate-pulse font-medium">
                  <Loader2 size={13} className="animate-spin" /> Submitting encoding instructions to server...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
