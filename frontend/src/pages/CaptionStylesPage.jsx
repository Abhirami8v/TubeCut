import { useEffect, useState } from 'react'
import { Plus, Copy, Trash2, X, Palette } from 'lucide-react'
import { api } from '../lib/api'
import StylePreviewCard from '../components/styles/StylePreviewCard'
import StyleEditorPanel from '../components/styles/StyleEditorPanel'
import Button from '../components/ui/Button'

const BLANK_STYLE = {
  name: 'New Style',
  font_family: 'Inter',
  font_size: 34,
  text_color: '#FFFFFF',
  highlight_color: '#FFD400',
  outline_color: '#000000',
  outline_width: 3,
  shadow_strength: 1,
  background_box: false,
  background_opacity: 50,
  uppercase: true,
  bold: true,
  position: 'bottom',
  animation: 'pop',
  words_per_block: 3,
}

export default function CaptionStylesPage() {
  const [styles, setStyles] = useState(null)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null) // null | style object being edited/created
  const [isNew, setIsNew] = useState(false)
  const [saving, setSaving] = useState(false)

  function refresh() {
    return api
      .listStyles()
      .then(setStyles)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    refresh()
  }, [])

  function startNew() {
    setEditing({ ...BLANK_STYLE })
    setIsNew(true)
  }

  function startDuplicate(style) {
    const { id, is_preset, ...rest } = style
    setEditing({ ...rest, name: `${style.name} (copy)` })
    setIsNew(true)
  }

  function startEdit(style) {
    setEditing({ ...style })
    setIsNew(false)
  }

  async function handleDelete(style) {
    if (style.is_preset) return
    if (!confirm(`Delete "${style.name}"? This can't be undone.`)) return
    await api.deleteStyle(style.id)
    refresh()
  }

  async function handleSave() {
    setSaving(true)
    try {
      if (isNew) {
        const { id, is_preset, ...payload } = editing
        await api.createStyle(payload)
      } else {
        const { id, is_preset, ...payload } = editing
        await api.updateStyle(editing.id, payload)
      }
      setEditing(null)
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="px-6 md:px-12 py-12 max-w-6xl mx-auto min-h-screen relative">
      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10 pb-6 border-b border-[#2A2633]">
        <div>
          <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
            Typography Assets
          </span>
          <h1 className="font-display font-extrabold text-3xl md:text-4xl text-white tracking-tight mt-1">
            Caption Styles
          </h1>
          <p className="text-sm text-[var(--color-text-dim)] mt-2">
            Customize typography presets to burn text overlays onto your short-form videos.
          </p>
        </div>
        
        <Button 
          onClick={startNew} 
          size="sm"
          className="rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] text-white hover:opacity-90 font-semibold px-5 py-2.5 shadow-[0_4px_12px_rgba(196,94,255,0.2)] flex items-center justify-center gap-2"
        >
          <Plus size={15} strokeWidth={2.5} /> Create style
        </Button>
      </div>

      {error && (
        <p className="text-sm text-[#FF5A79] bg-[#FF5A79]/5 border border-[#FF5A79]/10 rounded-xl py-3 px-4 mb-6">{error}</p>
      )}

      {/* Styles Grid */}
      {styles && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
          {styles.map((style) => (
            <StylePreviewCard
              key={style.id}
              style={style}
              onClick={() => startEdit(style)}
              actions={
                <div className="flex items-center gap-1.5">
                  <IconAction title="Duplicate Style" onClick={(e) => { e.stopPropagation(); startDuplicate(style) }}>
                    <Copy size={11} />
                  </IconAction>
                  {!style.is_preset && (
                    <IconAction title="Delete Style" onClick={(e) => { e.stopPropagation(); handleDelete(style) }}>
                      <Trash2 size={11} className="hover:text-[#FF5A79]" />
                    </IconAction>
                  )}
                </div>
              }
            />
          ))}
        </div>
      )}

      {/* Editor Modal Overlay (Widen from max-w-3xl to max-w-5xl) */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 sm:p-6 overflow-y-auto">
          <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-3xl p-8 relative bg-[#0D0C0F] border border-[#2A2633] shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
            <button
              onClick={() => setEditing(null)}
              className="absolute top-5 right-5 w-8 h-8 rounded-full border border-[#2A2633] bg-[#141318] text-[var(--color-text-dim)] hover:text-white flex items-center justify-center hover:border-white/20 transition-all"
            >
              <X size={15} />
            </button>
            
            <div className="mb-8">
              <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
                Style Designer
              </span>
              <h2 className="font-display font-extrabold text-2xl text-white tracking-tight mt-1">
                {isNew ? 'Create Caption Preset' : `Customize "${editing.name}"`}
              </h2>
            </div>
            
            <StyleEditorPanel
              style={editing}
              onChange={setEditing}
              onSave={handleSave}
              saving={saving}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function IconAction({ children, ...props }) {
  return (
    <button
      className="w-6 h-6 rounded-lg bg-black/80 backdrop-blur text-white flex items-center justify-center hover:bg-black border border-white/10 hover:border-white/30 transition-all cursor-pointer"
      {...props}
    >
      {children}
    </button>
  )
}
