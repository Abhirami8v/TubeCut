import { useEffect, useState } from 'react'
import { Film, FilmIcon, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import ClipCard from '../components/clips/ClipCard'

export default function MyClipsPage() {
  const [clips, setClips] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api
      .listAllClips()
      .then(setClips)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="px-6 md:px-12 py-12 max-w-6xl mx-auto min-h-screen relative">
      {/* Page Header */}
      <div className="mb-10 pb-6 border-b border-[#2A2633] flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
            Studio Library
          </span>
          <h1 className="font-display font-extrabold text-3xl md:text-4xl text-white tracking-tight mt-1">
            My Clips
          </h1>
          <p className="text-sm text-[var(--color-text-dim)] mt-2">
            Every highlighted clip you've generated, across all source videos.
          </p>
        </div>
        {clips && clips.length > 0 && (
          <span className="text-xs font-mono text-[var(--color-text-faint)] bg-[#1E1C22] px-3.5 py-1.5 rounded-full border border-[#2A2633]">
            Total Clips: {clips.length}
          </span>
        )}
      </div>

      {error && (
        <p className="text-sm text-[#FF5A79] bg-[#FF5A79]/5 border border-[#FF5A79]/10 rounded-xl py-3 px-4 mb-6">{error}</p>
      )}

      {/* Loading Skeletons */}
      {clips === null && !error && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 items-start">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-3xl border border-[#2A2633] bg-[#141318] overflow-hidden">
              <div className="aspect-video bg-[#1E1C22]/60 animate-pulse relative">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#C45EFF]/5 to-transparent animate-[shimmer_2s_infinite]" />
              </div>
              <div className="p-5 space-y-3 bg-[#141318]">
                <div className="h-4 w-3/4 rounded-lg bg-[#1E1C22] animate-pulse" />
                <div className="h-3 w-1/2 rounded bg-[#1E1C22] animate-pulse" />
                <div className="flex items-center gap-2 pt-2">
                  <div className="h-8 flex-1 rounded-xl bg-[#1E1C22] animate-pulse" />
                  <div className="h-8 w-8 rounded-xl bg-[#1E1C22] animate-pulse" />
                  <div className="h-8 w-8 rounded-xl bg-[#1E1C22] animate-pulse" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {clips && clips.length === 0 && (
        <div className="flex flex-col items-center justify-center text-center py-28 gap-4 border border-dashed border-[#2A2633] rounded-3xl bg-[#141318]/20">
          <div className="w-14 h-14 rounded-full bg-[#1E1C22] flex items-center justify-center text-[var(--color-text-faint)] border border-[#2A2633]">
            <Film size={24} className="text-[#C45EFF]" />
          </div>
          <div className="space-y-1">
            <h3 className="font-display font-bold text-lg text-white">No clips generated yet</h3>
            <p className="text-sm text-[var(--color-text-dim)] max-w-sm mx-auto">
              Ready to create content? Go to the clip creator page to upload and reframe your first video.
            </p>
          </div>
        </div>
      )}

      {/* Grid containing portrait 9:16 and landscape 16:9 clips, aligned at top via items-start */}
      {clips && clips.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 items-start">
          {clips.map((clip) => (
            <ClipCard key={clip.clip_id} clip={clip} />
          ))}
        </div>
      )}
    </div>
  )
}
