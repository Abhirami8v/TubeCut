import { useEffect, useState } from 'react'
import { Film } from 'lucide-react'
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
    <div className="px-10 py-10 max-w-7xl mx-auto">
      <h1 className="font-display font-semibold text-2xl mb-1">My Clips</h1>
      <p className="text-sm text-[var(--color-text-dim)] mb-8">
        Every clip you've generated, across every video.
      </p>

      {error && <p className="text-sm text-[var(--color-danger)]">{error}</p>}

      {clips === null && !error && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-[var(--color-border)] overflow-hidden">
              <div className="aspect-video shimmer" />
              <div className="p-4 space-y-2">
                <div className="h-3 w-3/4 rounded shimmer" />
                <div className="h-3 w-1/2 rounded shimmer" />
              </div>
            </div>
          ))}
        </div>
      )}

      {clips && clips.length === 0 && (
        <div className="flex flex-col items-center justify-center text-center py-24 gap-3">
          <div className="w-12 h-12 rounded-full bg-[var(--color-surface-2)] flex items-center justify-center text-[var(--color-text-faint)]">
            <Film size={20} />
          </div>
          <p className="text-sm text-[var(--color-text-dim)]">
            No clips yet. Head to Create Clip to generate your first batch.
          </p>
        </div>
      )}

      {clips && clips.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {clips.map((clip) => (
            <ClipCard key={clip.clip_id} clip={clip} />
          ))}
        </div>
      )}
    </div>
  )
}
