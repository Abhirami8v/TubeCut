import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import Button from '../components/ui/Button'
import { Loader2, Settings, Sparkles, Palette, Save } from 'lucide-react'

const FONT_OPTIONS = [
  'Bowlby One SC', 'KOMIKAX', 'Unbounded', 'Yuyu', 'Inter Local',
  'Inter', 'Arial', 'Arial Black', 'Arial Rounded MT Bold', 'Avenir Next',
  'Calibri', 'Comic Sans MS', 'Georgia', 'Helvetica Neue', 'Impact',
  'Montserrat', 'Poppins', 'Segoe UI', 'Space Grotesk', 'Tahoma',
  'Times New Roman', 'Trebuchet MS', 'Verdana', 'Menlo',
]
const ANIMATIONS = ['kinetic', 'word-pop', 'pop', 'bounce', 'fade', 'none']
const POSITIONS = ['top', 'middle', 'bottom']

export default function SettingsPage() {
  const [settings, setSettings] = useState(null)
  const [styles, setStyles] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  async function loadData() {
    try {
      setLoading(true)
      const me = await api.getMe()
      setSettings(me.settings)
      const styleList = await api.listStyles()
      setStyles(styleList)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleChange = (key, val) => {
    setSettings((prev) => ({ ...prev, [key]: val }))
    setSuccess(false)
  }

  const handleNumChange = (key, val) => {
    setSettings((prev) => ({ ...prev, [key]: Number(val) }))
    setSuccess(false)
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      const updated = await api.saveSettings(settings)
      setSettings(updated)
      setSuccess(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="px-6 md:px-12 py-12 max-w-6xl mx-auto flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="animate-spin text-[#C45EFF]" size={28} />
          <span className="text-sm text-[var(--color-text-dim)] font-mono">Loading system preferences...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="px-6 md:px-12 py-12 max-w-4xl mx-auto min-h-screen relative">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#C45EFF]/2 blur-[140px] pointer-events-none" />

      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10 pb-6 border-b border-[#2A2633] relative z-10">
        <div>
          <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold flex items-center gap-1">
            <Settings size={12} /> Studio Configurations
          </span>
          <h1 className="font-display font-extrabold text-3xl md:text-4xl text-white tracking-tight mt-1">
            Settings
          </h1>
          <p className="text-sm text-[var(--color-text-dim)] mt-2">
            Configure system defaults and visual presets applied to your newly generated short-form clips.
          </p>
        </div>
      </div>

      {error && (
        <p className="text-sm text-[#FF5A79] bg-[#FF5A79]/5 border border-[#FF5A79]/10 rounded-xl py-3 px-4 mb-6 relative z-10">{error}</p>
      )}
      {success && (
        <p className="text-sm text-[#35D0BA] bg-[#35D0BA]/5 border border-[#35D0BA]/10 rounded-xl py-3 px-4 mb-6 relative z-10">
          Preferences saved successfully.
        </p>
      )}

      <form onSubmit={handleSave} className="space-y-8 relative z-10">
        
        {/* Section 1: Pipeline Defaults */}
        <div className="bg-[#141318] border border-[#2A2633] rounded-3xl p-6 sm:p-8 space-y-6">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633]/60 pb-3 flex items-center gap-2">
            <Sparkles size={16} className="text-[#C45EFF]" /> Clip Generator Defaults
          </h3>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">
                Default Clip Count: {settings.default_clip_count}
              </span>
              <span className="block text-xs text-[var(--color-text-faint)] leading-normal">
                Initial number of clips generated from Long videos.
              </span>
              <input
                type="range"
                min={1}
                max={10}
                value={settings.default_clip_count}
                onChange={(e) => handleNumChange('default_clip_count', e.target.value)}
                className="w-full accent-[#C45EFF] cursor-pointer mt-1"
              />
            </label>

            <label className="flex items-center justify-between gap-4 p-4 rounded-2xl border border-[#2A2633]/55 bg-[#0D0C0F]/50 cursor-pointer hover:border-[#2A2633] transition-colors">
              <div>
                <span className="block text-sm font-semibold text-white">Auto-reframe to vertical</span>
                <span className="block text-xs text-[var(--color-text-dim)] mt-1 leading-normal">
                  Crop horizontally-shot footage to vertical 9:16 using face tracking by default.
                </span>
              </div>
              <input
                type="checkbox"
                checked={settings.auto_reframe_default}
                onChange={(e) => handleChange('auto_reframe_default', e.target.checked)}
                className="w-4 h-4 accent-[#C45EFF] cursor-pointer"
              />
            </label>
          </div>
        </div>

        {/* Section 2: Default Caption Visual Settings */}
        <div className="bg-[#141318] border border-[#2A2633] rounded-3xl p-6 sm:p-8 space-y-6">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633]/60 pb-3 flex items-center gap-2">
            <Palette size={16} className="text-[#C45EFF]" /> Default Subtitle Typography
          </h3>

          {/* Typography layout inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Font Family</span>
              <select
                value={settings.caption_font_family}
                onChange={(e) => handleChange('caption_font_family', e.target.value)}
                className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white focus:border-[#C45EFF] focus:outline-none transition-colors cursor-pointer appearance-none"
              >
                {FONT_OPTIONS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </label>

            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Font Weight</span>
              <select
                value={settings.caption_font_weight}
                onChange={(e) => handleChange('caption_font_weight', e.target.value)}
                className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white focus:border-[#C45EFF] focus:outline-none transition-colors cursor-pointer appearance-none"
              >
                <option value="normal">Normal</option>
                <option value="bold">Bold</option>
              </select>
            </label>

            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Font Size: {settings.caption_font_size}px</span>
              <div className="flex items-center h-12">
                <input
                  type="range"
                  min={12}
                  max={96}
                  value={settings.caption_font_size}
                  onChange={(e) => handleNumChange('caption_font_size', e.target.value)}
                  className="w-full accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </label>
          </div>

          {/* Color Palette Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
            <ColorField
              label="Text Color"
              value={settings.caption_text_color}
              onChange={(e) => handleChange('caption_text_color', e.target.value)}
            />
            <ColorField
              label="Highlight Color"
              value={settings.caption_highlight_color}
              onChange={(e) => handleChange('caption_highlight_color', e.target.value)}
            />
            <ColorField
              label="Outline Color"
              value={settings.caption_outline_color}
              onChange={(e) => handleChange('caption_outline_color', e.target.value)}
            />
            <ColorField
              label="Background Color"
              value={settings.caption_background_color}
              onChange={(e) => handleChange('caption_background_color', e.target.value)}
            />
          </div>

          {/* Stroke and Shadow Settings */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Outline Width: {settings.caption_outline_width}px</span>
              <div className="flex items-center h-12">
                <input
                  type="range"
                  min={0}
                  max={12}
                  value={settings.caption_outline_width}
                  onChange={(e) => handleNumChange('caption_outline_width', e.target.value)}
                  className="w-full accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </label>

            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Text Shadow Strength: {settings.caption_shadow_strength}</span>
              <div className="flex items-center h-12">
                <input
                  type="range"
                  min={0}
                  max={10}
                  value={settings.caption_shadow_strength}
                  onChange={(e) => handleNumChange('caption_shadow_strength', e.target.value)}
                  className="w-full accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </label>
          </div>

          {/* Position, Animations, Safe margins */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-2">
            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Layout Position</span>
              <select
                value={settings.caption_position}
                onChange={(e) => handleChange('caption_position', e.target.value)}
                className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white focus:border-[#C45EFF] focus:outline-none transition-colors cursor-pointer appearance-none"
              >
                {POSITIONS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>

            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Active Animation</span>
              <select
                value={settings.caption_animation}
                onChange={(e) => handleChange('caption_animation', e.target.value)}
                className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white focus:border-[#C45EFF] focus:outline-none transition-colors cursor-pointer appearance-none"
              >
                {ANIMATIONS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </label>

            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">Safe Margins: {settings.caption_safe_margins}px</span>
              <div className="flex items-center h-12">
                <input
                  type="range"
                  min={0}
                  max={200}
                  value={settings.caption_safe_margins}
                  onChange={(e) => handleNumChange('caption_safe_margins', e.target.value)}
                  className="w-full accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </label>
          </div>

          {/* Background Box Opacity & Words Per Block */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">
                Background Box Opacity: {settings.caption_background_opacity}%
              </span>
              <div className="flex items-center h-12">
                <input
                  type="range"
                  min={0}
                  max={100}
                  disabled={!settings.caption_background_box}
                  value={settings.caption_background_opacity}
                  onChange={(e) => handleNumChange('caption_background_opacity', e.target.value)}
                  className="w-full accent-[#C45EFF] disabled:opacity-20 cursor-pointer"
                />
              </div>
            </label>

            <label className="block space-y-2">
              <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">
                Words Per Caption Block: {settings.caption_words_per_block}
              </span>
              <div className="flex items-center h-12">
                <input
                  type="range"
                  min={1}
                  max={12}
                  value={settings.caption_words_per_block}
                  onChange={(e) => handleNumChange('caption_words_per_block', e.target.value)}
                  className="w-full accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </label>
          </div>

          {/* Toggles */}
          <div className="flex flex-wrap items-center gap-6 pt-4">
            <label className="flex items-center gap-2.5 text-sm text-white cursor-pointer select-none font-medium">
              <input
                type="checkbox"
                checked={settings.caption_background_box}
                onChange={(e) => handleChange('caption_background_box', e.target.checked)}
                className="w-4 h-4 rounded border-[#2A2633] bg-[#0D0C0F] text-[#C45EFF] accent-[#C45EFF] cursor-pointer"
              />
              Background Box
            </label>

            <label className="flex items-center gap-2.5 text-sm text-white cursor-pointer select-none font-medium">
              <input
                type="checkbox"
                checked={settings.caption_uppercase}
                onChange={(e) => handleChange('caption_uppercase', e.target.checked)}
                className="w-4 h-4 rounded border-[#2A2633] bg-[#0D0C0F] text-[#C45EFF] accent-[#C45EFF] cursor-pointer"
              />
              Force Uppercase
            </label>
          </div>

        </div>

        {/* Save button */}
        <div className="pt-2">
          <Button
            type="submit"
            disabled={saving}
            className="w-full sm:w-auto rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] text-white hover:opacity-90 font-bold px-8 py-4 tracking-wide shadow-[0_4px_20px_rgba(196,94,255,0.25)] flex items-center justify-center gap-2 cursor-pointer"
          >
            {saving ? (
              <>
                <Loader2 size={16} className="animate-spin" /> Saving Configurations...
              </>
            ) : (
              <>
                <Save size={16} /> Save Settings
              </>
            )}
          </Button>
        </div>

      </form>
    </div>
  )
}

function ColorField({ label, value, onChange }) {
  return (
    <label className="block space-y-2">
      <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">{label}</span>
      <div className="flex items-center gap-3 rounded-xl border border-[#2A2633] bg-[#0D0C0F] px-3.5 py-2.5 focus-within:border-[#C45EFF] transition-colors">
        <input
          type="color"
          value={value}
          onChange={onChange}
          className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0 shrink-0 p-0"
        />
        <span className="font-mono text-xs text-white uppercase font-bold tracking-wider">{value}</span>
      </div>
    </label>
  )
}
