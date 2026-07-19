import { NavLink } from 'react-router-dom'
import { Scissors, Film, Palette, Settings, Sparkles, LogOut } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Create Clip', icon: Scissors, end: true },
  { to: '/clips', label: 'My Clips', icon: Film },
  { to: '/styles', label: 'Caption Styles', icon: Palette },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  const handleLogout = () => {
    localStorage.removeItem('tubecut_logged_in')
    window.location.reload()
  }

  return (
    <aside className="w-64 shrink-0 h-screen sticky top-0 flex flex-col bg-[#0D0C0F] border-r border-[#1E1B24] z-10">
      {/* Brand Header */}
      <div className="px-6 py-8 flex items-center gap-3">
        <div className="relative w-9 h-9 rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(196,94,255,0.4)]">
          <Sparkles size={18} className="text-white" strokeWidth={2.2} />
        </div>
        <div className="flex flex-col">
          <span className="font-display font-bold text-xl tracking-tight bg-gradient-to-r from-white via-[#F4F3F6] to-[#C45EFF] bg-clip-text text-transparent">
            TubeCut
          </span>
          <span className="text-[10px] font-mono text-[var(--color-text-faint)] tracking-widest uppercase">
            AI Publisher
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 flex flex-col gap-1.5 pt-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `group relative flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
                isActive
                  ? 'bg-[#1E1C22] text-[#C45EFF] shadow-[inset_0_0_1px_1px_rgba(196,94,255,0.15)]'
                  : 'text-[var(--color-text-dim)] hover:text-white hover:bg-[#151418]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  size={18}
                  strokeWidth={2.2}
                  className={`transition-colors duration-300 ${
                    isActive ? 'text-[#C45EFF]' : 'text-[var(--color-text-faint)] group-hover:text-[var(--color-text-dim)]'
                  }`}
                />
                <span>{label}</span>
                {/* Active Indicator Bar */}
                {isActive && (
                  <span className="absolute left-0 top-1/4 bottom-1/4 w-1 rounded-r bg-[#C45EFF] shadow-[0_0_8px_#C45EFF]" />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer / Logout action */}
      <div className="p-4 border-t border-[#1E1B24] flex flex-col gap-3">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-4 py-3 rounded-xl text-sm font-medium text-[#FF5A79] hover:text-[#FF7A99] hover:bg-[#FF5A79]/5 border border-transparent hover:border-[#FF5A79]/10 transition-all duration-300 cursor-pointer"
        >
          <LogOut size={18} strokeWidth={2.2} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
