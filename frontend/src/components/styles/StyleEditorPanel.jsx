import Button from '../ui/Button'
import StylePreviewCard from './StylePreviewCard'

const FONT_OPTIONS = [
  'Inter', 'Arial', 'Arial Black', 'Arial Rounded MT Bold', 'Avenir Next',
  'Calibri', 'Comic Sans MS', 'Georgia', 'Helvetica Neue', 'Impact',
  'Montserrat', 'Poppins', 'Segoe UI', 'Space Grotesk', 'Tahoma',
  'Times New Roman', 'Trebuchet MS', 'Verdana', 'Menlo',
]
const ANIMATIONS = ['kinetic', 'word-pop', 'pop', 'bounce', 'fade', 'none']
const POSITIONS = ['top', 'middle', 'bottom']

/**
 * StyleEditorPanel
 *
 * Full property editor for a caption style (custom or a duplicated
 * preset). Controls map 1:1 onto CaptionStyle fields on the backend so
 * `onChange` payloads can be sent straight to apply-style / PATCH /styles.
 */
export default function StyleEditorPanel({ style, onChange, onSave, saving }) {
  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    onChange({ ...style, [key]: value })
  }
  const setNum = (key) => (e) => onChange({ ...style, [key]: Number(e.target.value) })

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-8">
      <div className="space-y-3">
        <p className="text-xs font-medium text-[var(--color-text-dim)] uppercase tracking-wide">Live preview</p>
        <StylePreviewCard style={style} selected={false} onClick={() => {}} />
      </div>

      <div className="space-y-6">
        <Field label="Style name">
          <input
            value={style.name}
            onChange={set('name')}
            className="input"
            placeholder="My custom style"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Font family">
            <input
              list="font-options"
              value={style.font_family}
              onChange={set('font_family')}
              className="input"
              placeholder="e.g. Arial Black, Montserrat"
            />
            <datalist id="font-options">
              {FONT_OPTIONS.map((f) => (
                <option key={f} value={f} />
              ))}
            </datalist>
          </Field>
          <Field label={`Font size: ${style.font_size}px`}>
            <input
              type="range"
              min={16}
              max={72}
              value={style.font_size}
              onChange={setNum('font_size')}
              className="w-full accent-[var(--color-accent)]"
            />
          </Field>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <ColorField label="Text color" value={style.text_color} onChange={set('text_color')} />
          <ColorField label="Highlight" value={style.highlight_color} onChange={set('highlight_color')} />
          <ColorField label="Outline" value={style.outline_color} onChange={set('outline_color')} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label={`Outline width: ${style.outline_width}px`}>
            <input
              type="range"
              min={0}
              max={12}
              value={style.outline_width}
              onChange={setNum('outline_width')}
              className="w-full accent-[var(--color-accent)]"
            />
          </Field>
          <Field label={`Shadow: ${style.shadow_strength}`}>
            <input
              type="range"
              min={0}
              max={10}
              value={style.shadow_strength}
              onChange={setNum('shadow_strength')}
              className="w-full accent-[var(--color-accent)]"
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Position">
            <select value={style.position} onChange={set('position')} className="input">
              {POSITIONS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </Field>
          <Field label="Animation">
            <select value={style.animation} onChange={set('animation')} className="input">
              {ANIMATIONS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label={`Background box opacity: ${style.background_opacity}%`}>
            <input
              type="range"
              min={0}
              max={100}
              disabled={!style.background_box}
              value={style.background_opacity}
              onChange={setNum('background_opacity')}
              className="w-full accent-[var(--color-accent)] disabled:opacity-30"
            />
          </Field>
          <Field label={`Words per caption: ${style.words_per_block}`}>
            <input
              type="range"
              min={1}
              max={10}
              value={style.words_per_block}
              onChange={setNum('words_per_block')}
              className="w-full accent-[var(--color-accent)]"
            />
          </Field>
        </div>

        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="checkbox" checked={style.background_box} onChange={set('background_box')} className="accent-[var(--color-accent)]" />
            Background box
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="checkbox" checked={style.uppercase} onChange={set('uppercase')} className="accent-[var(--color-accent)]" />
            Uppercase
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="checkbox" checked={style.bold} onChange={set('bold')} className="accent-[var(--color-accent)]" />
            Bold
          </label>
        </div>

        <div className="pt-2">
          <Button onClick={onSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save style'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-[var(--color-text-dim)] mb-1.5">{label}</span>
      {children}
    </label>
  )
}

function ColorField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-[var(--color-text-dim)] mb-1.5">{label}</span>
      <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] px-2 py-1.5">
        <input type="color" value={value} onChange={onChange} className="w-6 h-6 rounded cursor-pointer bg-transparent" />
        <span className="font-mono text-xs text-[var(--color-text-dim)] uppercase">{value}</span>
      </div>
    </label>
  )
}
