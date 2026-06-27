import { useEffect, useState } from 'react'
import { Plus, Copy, Trash2, X } from 'lucide-react'
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
    <div className="px-10 py-10 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-1">
        <h1 className="font-display font-semibold text-2xl">Caption Styles</h1>
        <Button onClick={startNew} size="sm">
          <Plus size={14} /> New style
        </Button>
      </div>
      <p className="text-sm text-[var(--color-text-dim)] mb-8">
        Built-in presets plus anything you've customized. Applied per-clip from the clip editor.
      </p>

      {error && <p className="text-sm text-[var(--color-danger)] mb-4">{error}</p>}

      {styles && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {styles.map((style) => (
            <StylePreviewCard
              key={style.id}
              style={style}
              onClick={() => startEdit(style)}
              actions={
                <>
                  <IconAction title="Duplicate" onClick={(e) => { e.stopPropagation(); startDuplicate(style) }}>
                    <Copy size={12} />
                  </IconAction>
                  {!style.is_preset && (
                    <IconAction title="Delete" onClick={(e) => { e.stopPropagation(); handleDelete(style) }}>
                      <Trash2 size={12} />
                    </IconAction>
                  )}
                </>
              }
            />
          ))}
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-6">
          <div className="glass w-full max-w-3xl max-h-[88vh] overflow-y-auto rounded-2xl p-6 relative">
            <button
              onClick={() => setEditing(null)}
              className="absolute top-4 right-4 text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
            >
              <X size={18} />
            </button>
            <h2 className="font-display font-semibold text-lg mb-6">
              {isNew ? 'New caption style' : `Edit "${editing.name}"`}
            </h2>
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
      className="w-6 h-6 rounded-md bg-black/70 backdrop-blur text-white flex items-center justify-center hover:bg-black/90"
      {...props}
    >
      {children}
    </button>
  )
}
