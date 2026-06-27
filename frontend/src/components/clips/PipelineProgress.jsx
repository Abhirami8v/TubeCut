import { Check, Loader2, X } from 'lucide-react'

/**
 * PipelineProgress
 *
 * Step-by-step visualization of the backend job pipeline (download ->
 * extract audio -> transcribe -> analyze -> segment -> render). Steps
 * come straight from GET /jobs/{id}'s `steps` array so the UI never
 * drifts from the backend's actual state machine.
 */
export default function PipelineProgress({ steps, progressPercent, currentLabel, errorMessage }) {
  return (
    <div className="w-full max-w-xl">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-[var(--color-text)]">{currentLabel}</span>
        <span className="font-mono text-sm text-[var(--color-text-dim)]">{Math.round(progressPercent)}%</span>
      </div>

      <div className="h-1.5 w-full rounded-full bg-[var(--color-surface-2)] overflow-hidden mb-6">
        <div
          className="h-full rounded-full bg-[var(--color-accent)] transition-all duration-500 ease-out"
          style={{ width: `${Math.max(2, progressPercent)}%` }}
        />
      </div>

      <ol className="space-y-1">
        {steps
          .filter((s) => s.key !== 'completed')
          .map((step) => (
            <li key={step.key} className="flex items-center gap-3 py-1.5">
              <StepIcon state={step.state} />
              <span
                className={`text-sm ${
                  step.state === 'pending'
                    ? 'text-[var(--color-text-faint)]'
                    : step.state === 'active'
                    ? 'text-[var(--color-text)] font-medium'
                    : step.state === 'failed'
                    ? 'text-[var(--color-danger)]'
                    : 'text-[var(--color-text-dim)]'
                }`}
              >
                {step.label}
              </span>
            </li>
          ))}
      </ol>

      {errorMessage && (
        <div className="mt-4 rounded-lg border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-4 py-3 text-sm text-[var(--color-danger)]">
          {errorMessage}
        </div>
      )}
    </div>
  )
}

function StepIcon({ state }) {
  if (state === 'done') {
    return (
      <span className="w-5 h-5 rounded-full bg-[var(--color-success)]/15 text-[var(--color-success)] flex items-center justify-center shrink-0">
        <Check size={12} strokeWidth={3} />
      </span>
    )
  }
  if (state === 'active') {
    return (
      <span className="w-5 h-5 rounded-full bg-[var(--color-accent)]/15 text-[var(--color-accent)] flex items-center justify-center shrink-0">
        <Loader2 size={12} strokeWidth={3} className="animate-spin" />
      </span>
    )
  }
  if (state === 'failed') {
    return (
      <span className="w-5 h-5 rounded-full bg-[var(--color-danger)]/15 text-[var(--color-danger)] flex items-center justify-center shrink-0">
        <X size={12} strokeWidth={3} />
      </span>
    )
  }
  return <span className="w-5 h-5 rounded-full border border-[var(--color-border)] shrink-0" />
}
