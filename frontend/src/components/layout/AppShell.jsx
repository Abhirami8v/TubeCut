import Sidebar from './Sidebar'

export default function AppShell({ children }) {
  return (
    <div className="flex min-h-screen bg-[#0D0C0F] text-[var(--color-text)] relative overflow-hidden">
      {/* Decorative ambient gradients */}
      <div className="absolute top-0 right-1/4 w-[500px] h-[500px] rounded-full bg-[#C45EFF]/5 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-10 left-1/3 w-[350px] h-[350px] rounded-full bg-[#C45EFF]/3 blur-[80px] pointer-events-none" />
      
      <Sidebar />
      <main className="flex-1 min-w-0 relative z-10">{children}</main>
    </div>
  )
}
