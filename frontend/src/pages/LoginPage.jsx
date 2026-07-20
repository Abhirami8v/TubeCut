import { useState } from 'react'
import { Sparkles, Lock, Mail, ArrowRight, UserPlus, LogIn } from 'lucide-react'
import { api } from '../lib/api'
import Button from '../components/ui/Button'

export default function LoginPage({ onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      let res
      if (isRegister) {
        res = await api.register({ email: email.trim(), password })
      } else {
        res = await api.login({ email: email.trim(), password })
      }

      localStorage.setItem('tubecut_token', res.token)
      localStorage.setItem('tubecut_email', res.email)
      localStorage.setItem('tubecut_is_admin', res.is_admin ? 'true' : 'false')
      localStorage.setItem('tubecut_logged_in', 'true')
      onLoginSuccess()
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-screen bg-[#0D0C0F] text-white flex items-center justify-center relative overflow-hidden p-6">
      {/* Glow background orbs */}
      <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-[#C45EFF]/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-[#C45EFF]/5 blur-[130px] pointer-events-none" />

      {/* Login Card */}
      <div className="w-full max-w-md bg-[#141318] border border-[#2A2633] rounded-[32px] p-8 sm:p-10 relative z-10 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)] overflow-hidden group">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-[1px] bg-gradient-to-r from-transparent via-[#C45EFF] to-transparent" />

        {/* Brand header */}
        <div className="flex flex-col items-center text-center gap-3 mb-6">
          <div className="relative w-12 h-12 rounded-2xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] flex items-center justify-center shrink-0 shadow-[0_0_20px_rgba(196,94,255,0.4)]">
            <Sparkles size={24} className="text-white animate-pulse" strokeWidth={2.2} />
          </div>
          <div className="space-y-1">
            <h1 className="font-display font-extrabold text-3xl tracking-tight text-white">
              TubeCut Studio
            </h1>
            <p className="text-xs text-[var(--color-text-dim)] font-medium uppercase tracking-widest font-mono">
              AI Publisher Dashboard
            </p>
          </div>
        </div>

        {/* Tabs switcher */}
        <div className="flex bg-[#0D0C0F] p-1.5 rounded-2xl border border-[#2A2633] mb-6">
          <button
            type="button"
            onClick={() => {
              setIsRegister(false)
              setError(null)
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold tracking-wide transition-all ${
              !isRegister
                ? 'bg-[#1E1C22] text-white font-bold'
                : 'text-[var(--color-text-dim)] hover:text-white'
            }`}
          >
            <LogIn size={13} />
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setIsRegister(true)
              setError(null)
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-semibold tracking-wide transition-all ${
              isRegister
                ? 'bg-[#1E1C22] text-white font-bold'
                : 'text-[var(--color-text-dim)] hover:text-white'
            }`}
          >
            <UserPlus size={13} />
            Register
          </button>
        </div>

        {/* Form panel */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-4">
            {/* Email input field */}
            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">
                Email Address
              </span>
              <div className="flex items-center gap-3 rounded-xl border border-[#2A2633] bg-[#0D0C0F] px-4 py-3 focus-within:border-[#C45EFF] transition-colors">
                <Mail size={16} className="text-[var(--color-text-faint)]" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="creator@tubecut.com"
                  className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-[var(--color-text-faint)]"
                />
              </div>
            </label>

            {/* Password input field */}
            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">
                Studio Password
              </span>
              <div className="flex items-center gap-3 rounded-xl border border-[#2A2633] bg-[#0D0C0F] px-4 py-3 focus-within:border-[#C45EFF] transition-colors">
                <Lock size={16} className="text-[var(--color-text-faint)]" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-[var(--color-text-faint)]"
                />
              </div>
            </label>
          </div>

          {error && (
            <p className="text-xs text-[#FF5A79] text-center font-medium bg-[#FF5A79]/5 border border-[#FF5A79]/10 rounded-xl py-2 px-3">
              {error}
            </p>
          )}

          {/* Submit action button */}
          <Button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] text-white hover:opacity-90 font-bold py-3.5 tracking-wide shadow-[0_4px_20px_rgba(196,94,255,0.25)] flex items-center justify-center gap-2 transition-all mt-4 cursor-pointer"
          >
            {loading
              ? isRegister
                ? 'Creating Account...'
                : 'Entering Studio...'
              : isRegister
              ? 'Create Account'
              : 'Sign In'}
            {!loading && <ArrowRight size={16} strokeWidth={2.5} />}
          </Button>
        </form>

        {/* Footnote */}
        <div className="mt-8 pt-6 border-t border-[#2A2633]/50 text-center">
          <p className="text-[10px] text-[var(--color-text-faint)] leading-relaxed font-mono">
            First user registers as an administrator. Or use seeded admin credentials: <span className="text-white font-bold">admin@tubecut.com</span> with password <span className="text-white font-bold">admin</span>
          </p>
        </div>
      </div>
    </div>
  )
}
