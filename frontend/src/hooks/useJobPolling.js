import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

/**
 * useJobPolling
 *
 * Polls GET /jobs/{jobId} every `intervalMs` while a jobId is set and
 * the job hasn't reached a terminal state (completed/failed). Exposes
 * the latest job snapshot plus a `reset` to clear it.
 *
 * If the backend returns 404 (e.g. after a Render restart that wiped
 * the SQLite database), polling stops and `notFound` is set to true
 * so the parent component can clear the stale jobId.
 */
export function useJobPolling(jobId, intervalMs = 1500) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    if (!jobId) {
      setJob(null)
      setNotFound(false)
      return
    }

    let cancelled = false

    async function poll() {
      try {
        const data = await api.getJob(jobId)
        if (cancelled) return
        setJob(data)
        setError(null)
        setNotFound(false)

        if (data.status !== 'completed' && data.status !== 'failed') {
          timerRef.current = setTimeout(poll, intervalMs)
        }
      } catch (err) {
        if (cancelled) return

        // If the job no longer exists (404), stop polling entirely
        if (err.message?.includes('404') || err.status === 404) {
          setNotFound(true)
          setError(null)
          return
        }

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

  return { job, error, notFound }
}
