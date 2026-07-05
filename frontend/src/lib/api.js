/**
 * api.js
 *
 * Thin fetch wrapper for the TubeCut backend. All requests go through
 * the Vite dev proxy at /api (see vite.config.js), which forwards to
 * FastAPI and strips the /api prefix.
 */

const BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? "https://tubecut.onrender.com" : "/api");

export function downloadUrl(path) {
  if (!path) return null
  return path.startsWith('/api/') ? path : `${BASE}${path}`
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new Error(detail || `Request failed: ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Jobs
  generateClips: (payload) =>
    request('/generate-clips', { method: 'POST', body: JSON.stringify(payload) }),
  getJob: (jobId) => request(`/jobs/${jobId}`),

  // Clips
  getClip: (clipId) => request(`/clips/${clipId}`),
  trimClip: (clipId, payload) =>
    request(`/clips/${clipId}/trim`, { method: 'POST', body: JSON.stringify(payload) }),
  updateCaption: (clipId, payload) =>
    request(`/clips/${clipId}/update-caption`, { method: 'POST', body: JSON.stringify(payload) }),
  createCaption: (clipId, payload) =>
    request(`/clips/${clipId}/create-caption`, { method: 'POST', body: JSON.stringify(payload) }),
  deleteCaption: (clipId, payload) =>
    request(`/clips/${clipId}/delete-caption`, { method: 'POST', body: JSON.stringify(payload) }),
  splitCaption: (clipId, payload) =>
    request(`/clips/${clipId}/split-caption`, { method: 'POST', body: JSON.stringify(payload) }),
  mergeCaption: (clipId, payload) =>
    request(`/clips/${clipId}/merge-caption`, { method: 'POST', body: JSON.stringify(payload) }),
  applyStyle: (clipId, payload) =>
    request(`/clips/${clipId}/apply-style`, { method: 'POST', body: JSON.stringify(payload) }),

  // Styles
  listStyles: () => request('/styles'),
  createStyle: (payload) => request('/styles', { method: 'POST', body: JSON.stringify(payload) }),
  updateStyle: (styleId, payload) =>
    request(`/styles/${styleId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteStyle: (styleId) => request(`/styles/${styleId}`, { method: 'DELETE' }),

  // Library
  listAllClips: () => request('/library/clips'),
}

export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '0:00'
  const total = Math.max(0, Math.round(seconds))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function formatTimecode(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '00:00.00'
  const total = Math.max(0, seconds)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${s.toFixed(2).padStart(5, '0')}`
}
