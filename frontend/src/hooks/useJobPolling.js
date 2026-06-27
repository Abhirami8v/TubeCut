import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

/**
 * useJobPolling
 *
 * Polls GET /jobs/{jobId} every `intervalMs` while a jobId is set and
 * the job hasn't reached a terminal state (completed/failed). Exposes
 * the latest job snapshot plus a `reset` to clear it.
 */
export function useJobPolling(jobId, intervalMs = 1500) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)
  const timerRef = useRef(null)

  useEffect(() => {
    if (!jobId) {
      setJob(null)
      return
    }

    let cancelled = false

    async function poll() {
      try {
        const data = await api.getJob(jobId)
        if (cancelled) return
        setJob(data)
        setError(null)

        if (data.status !== 'completed' && data.status !== 'failed') {
          timerRef.current = setTimeout(poll, intervalMs)
        }
      } catch (err) {
        if (cancelled) return
        setError(err.message)
        timerRef.current = setTimeout(poll, intervalMs * 2)
      }
    }

    poll()

    return () => {
      cancelled = true
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [jobId, intervalMs])

  return { job, error }
}
