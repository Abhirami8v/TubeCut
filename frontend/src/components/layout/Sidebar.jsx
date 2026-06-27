import { NavLink } from 'react-router-dom'
import { Scissors, Film, Palette, Settings, Sparkles } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Create Clip', icon: Scissors, end: true },
  { to: '/clips', label: 'My Clips', icon: Film },
  { to: '/styles', label: 'Caption Styles', icon: Palette },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <aside className="glass w-64 shrink-0 h-screen sticky top-0 flex flex-col border-r border-[var(--color-border-soft)]">
      <div className="px-6 py-6 flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-[var(--color-accent)] flex items-center justify-center shrink-0">
          <Sparkles size={16} className="text-white" strokeWidth={2.5} />
        </div>
        <span className="font-display font-semibold text-lg tracking-tight">TubeCut</span>
      </div>

      <nav className="flex-1 px-3 flex flex-col gap-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                isActive
                  ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
                  : 'text-[var(--color-text-dim)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-2)]'
              }`
            }
          >
            <Icon size={18} strokeWidth={2} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 mx-3 mb-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)]/60">
        <p className="text-xs text-[var(--color-text-dim)] leading-relaxed">
          Paste a link, get clips with hooks, captions, and auto-reframe — ready to post.
        </p>
      </div>
    </aside>
  )
}
