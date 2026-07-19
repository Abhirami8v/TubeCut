import { Check, Loader2, X, AlertTriangle } from 'lucide-react'

export default function PipelineProgress({ steps, progressPercent, currentLabel, errorMessage }) {
  return (
    <div className="w-full max-w-xl bg-[#141318] border border-[#2A2633] rounded-3xl p-8 relative overflow-hidden shadow-[0_15px_40px_-15px_rgba(0,0,0,0.6)]">
      {/* Decorative top glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-[1px] bg-gradient-to-r from-transparent via-[#C45EFF] to-transparent" />
      
      {/* Header Info */}
      <div className="flex flex-col items-center text-center gap-2 mb-8">
        <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
          AI Pipeline Active
        </span>
        <h3 className="font-display font-bold text-2xl text-white tracking-tight">
          {currentLabel || 'Analyzing Footage...'}
        </h3>
        
        {/* Large Centered Progress Ring/Number */}
        <div className="relative flex items-center justify-center w-28 h-28 rounded-full border border-[#2A2633] bg-[#1E1C22]/30 mt-4">
          <div className="absolute inset-2 rounded-full border border-dashed border-[#C45EFF]/20 animate-[spin_20s_linear_infinite]" />
          <div className="absolute inset-0 rounded-full border-2 border-[#C45EFF] border-t-transparent animate-[spin_3s_linear_infinite] opacity-40" />
          <span className="font-display font-extrabold text-3xl text-white tracking-tight">
            {Math.round(progressPercent)}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2 mb-8">
        <div className="h-2 w-full rounded-full bg-[#1E1C22] overflow-hidden relative border border-[#2A2633]/50">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#C45EFF] to-[#D88EFF] shadow-[0_0_12px_#C45EFF] transition-all duration-700 ease-out relative"
            style={{ width: `${Math.max(4, progressPercent)}%` }}
          >
            {/* Shimmer effect */}
            <div className="absolute inset-0 bg-white/20 animate-[pulse_1.5s_infinite] rounded-full" />
          </div>
        </div>
      </div>

      {/* Steps List */}
      <div className="space-y-3 bg-[#0D0C0F]/60 rounded-2xl p-5 border border-[#1E1B24]">
        {steps
          .filter((s) => s.key !== 'completed')
          .map((step) => {
            const isActive = step.state === 'active'
            const isDone = step.state === 'done'
            const isFailed = step.state === 'failed'
            
            return (
              <div 
                key={step.key} 
                className={`flex items-center justify-between gap-3 py-2 px-3 rounded-lg transition-all duration-300 ${
                  isActive ? 'bg-[#1E1C22]/50 border border-[#C45EFF]/10' : 'border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <StepIcon state={step.state} />
                  <span
                    className={`text-sm tracking-wide transition-colors duration-300 ${
                      isActive
                        ? 'text-white font-semibold'
                        : isDone
                        ? 'text-[var(--color-text-dim)]'
                        : isFailed
                        ? 'text-[#FF5A79]'
                        : 'text-[var(--color-text-faint)]'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {isActive && (
                  <span className="text-[10px] font-mono bg-[#C45EFF]/10 text-[#C45EFF] px-2 py-0.5 rounded border border-[#C45EFF]/20 animate-pulse uppercase">
                    Running
                  </span>
                )}
              </div>
            )
          })}
      </div>

      {/* Error Message Panel */}
      {errorMessage && (
        <div className="mt-6 rounded-2xl border border-[#FF5A79]/30 bg-[#FF5A79]/5 px-5 py-4 text-sm text-[#FF5A79] space-y-2 relative overflow-hidden animate-[headShake_0.5s_ease-in-out]">
          <div className="flex items-center gap-2 font-semibold">
            <AlertTriangle size={16} />
            <span>Process Encountered an Issue</span>
          </div>
          <p className="leading-relaxed opacity-90 text-xs font-mono">{friendlyError(errorMessage)}</p>
          {errorMessage.includes('YT_DLP_COOKIES_CONTENT') && (
            <p className="text-[10px] opacity-80 leading-relaxed font-sans pt-1">
              Add <code className="font-mono bg-[#FF5A79]/10 px-1 py-0.5 rounded text-white">YT_DLP_COOKIES_CONTENT</code> under env variables, then restart.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function friendlyError(message) {
  if (!message) return message
  if (message.includes('not a bot') || message.includes('YT_DLP_COOKIES_CONTENT')) {
    return 'YouTube blocked the request. Please provide cookies in the backend settings configuration.'
  }
  if (message.includes('GEMINI_API_KEY')) {
    return 'Gemini API key is invalid or unset. Please verify your GEMINI_API_KEY settings.'
  }
  if (message.includes('ffmpeg')) {
    return 'FFmpeg error encountered. Please check server log for media encoding issues.'
  }
  const firstLine = message.split('\n')[0]
  return firstLine.length > 220 ? `${firstLine.slice(0, 220)}…` : firstLine
}

function StepIcon({ state }) {
  if (state === 'done') {
    return (
      <span className="w-5 h-5 rounded-full bg-[#35D0BA]/10 text-[#35D0BA] flex items-center justify-center shrink-0 border border-[#35D0BA]/20">
        <Check size={11} strokeWidth={3} />
      </span>
    )
  }
  if (state === 'active') {
    return (
      <span className="w-5 h-5 rounded-full bg-[#C45EFF]/10 text-[#C45EFF] flex items-center justify-center shrink-0 border border-[#C45EFF]/20 animate-pulse">
        <Loader2 size={11} strokeWidth={3} className="animate-spin" />
      </span>
    )
  }
  if (state === 'failed') {
    return (
      <span className="w-5 h-5 rounded-full bg-[#FF5A79]/10 text-[#FF5A79] flex items-center justify-center shrink-0 border border-[#FF5A79]/20">
        <X size={11} strokeWidth={3} />
      </span>
    )
  }
  return <span className="w-5 h-5 rounded-full border border-[#2A2633] shrink-0 bg-[#0D0C0F]" />
}
