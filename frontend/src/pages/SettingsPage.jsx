import { useState } from 'react'

export default function SettingsPage() {
  const [defaultClipCount, setDefaultClipCount] = useState(3)
  const [autoReframeDefault, setAutoReframeDefault] = useState(true)

  return (
    <div className="px-10 py-10 max-w-2xl mx-auto">
      <h1 className="font-display font-semibold text-2xl mb-1">Settings</h1>
      <p className="text-sm text-[var(--color-text-dim)] mb-8">
        Defaults applied the next time you generate clips.
      </p>

      <div className="space-y-6">
        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <label className="block">
            <span className="block text-sm font-medium mb-1">Default clip count: {defaultClipCount}</span>
            <span className="block text-xs text-[var(--color-text-dim)] mb-3">
              How many clips to generate per video by default.
            </span>
            <input
              type="range"
              min={1}
              max={10}
              value={defaultClipCount}
              onChange={(e) => setDefaultClipCount(Number(e.target.value))}
              className="w-full accent-[var(--color-accent)]"
            />
          </label>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <label className="flex items-center justify-between cursor-pointer">
            <span>
              <span className="block text-sm font-medium">Auto-reframe to vertical</span>
              <span className="block text-xs text-[var(--color-text-dim)] mt-0.5">
                Use face/person tracking to convert clips to 9:16 by default.
              </span>
            </span>
            <input
              type="checkbox"
              checked={autoReframeDefault}
              onChange={(e) => setAutoReframeDefault(e.target.checked)}
              className="accent-[var(--color-accent)] w-4 h-4"
            />
          </label>
        </div>

        <p className="text-xs text-[var(--color-text-faint)]">
          These preferences are stored locally in this browser session for now.
        </p>
      </div>
    </div>
  )
}
