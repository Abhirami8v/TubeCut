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

export default function StyleEditorPanel({ style, onChange, onSave, saving }) {
  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    onChange({ ...style, [key]: value })
  }
  const setNum = (key) => (e) => onChange({ ...style, [key]: Number(e.target.value) })

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-10 items-start">
      {/* Live Preview Column */}
      <div className="space-y-4 sticky top-4 bg-[#141318] border border-[#2A2633] p-5 rounded-3xl">
        <span className="text-[10px] font-mono tracking-widest text-[#C45EFF] uppercase font-bold">
          Active Preview
        </span>
        <StylePreviewCard style={style} selected={false} onClick={() => {}} />
        <p className="text-[10px] text-[var(--color-text-dim)] leading-relaxed text-center font-mono">
          Simulating a 9:16 portrait mobile render.
        </p>
      </div>

      {/* Editor Controls Column */}
      <div className="space-y-8 bg-[#141318] border border-[#2A2633] p-8 rounded-3xl">
        
        {/* Style metadata */}
        <div className="space-y-4">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633] pb-2">Identity</h3>
          <Field label="Style Name">
            <input
              value={style.name}
              onChange={set('name')}
              className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white placeholder:text-[var(--color-text-faint)] focus:border-[#C45EFF] focus:outline-none transition-colors"
              placeholder="e.g. Bold Neon, Minimalist"
            />
          </Field>
        </div>

        {/* Typography */}
        <div className="space-y-4">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633] pb-2">Typography</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label="Font Family">
              <input
                list="font-options"
                value={style.font_family}
                onChange={set('font_family')}
                className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white placeholder:text-[var(--color-text-faint)] focus:border-[#C45EFF] focus:outline-none transition-colors"
                placeholder="Select or type font..."
              />
              <datalist id="font-options">
                {FONT_OPTIONS.map((f) => (
                  <option key={f} value={f} />
                ))}
              </datalist>
            </Field>
            
            <Field label={`Font Size: ${style.font_size}px`}>
              <div className="flex items-center gap-3 h-11">
                <input
                  type="range"
                  min={16}
                  max={72}
                  value={style.font_size}
                  onChange={setNum('font_size')}
                  className="flex-1 accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </Field>
          </div>
        </div>

        {/* Color Palette */}
        <div className="space-y-4">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633] pb-2">Color Palette</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <ColorField label="Text Color" value={style.text_color} onChange={set('text_color')} />
            <ColorField label="Highlight Color" value={style.highlight_color} onChange={set('highlight_color')} />
            <ColorField label="Outline Color" value={style.outline_color} onChange={set('outline_color')} />
          </div>
        </div>

        {/* Outline & Shadow Effects */}
        <div className="space-y-4">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633] pb-2">Stroke & Effects</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label={`Outline Width: ${style.outline_width}px`}>
              <div className="flex items-center gap-3 h-11">
                <input
                  type="range"
                  min={0}
                  max={12}
                  value={style.outline_width}
                  onChange={setNum('outline_width')}
                  className="flex-1 accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </Field>
            <Field label={`Text Shadow Strength: ${style.shadow_strength}`}>
              <div className="flex items-center gap-3 h-11">
                <input
                  type="range"
                  min={0}
                  max={10}
                  value={style.shadow_strength}
                  onChange={setNum('shadow_strength')}
                  className="flex-1 accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </Field>
          </div>
        </div>

        {/* Position & Animations */}
        <div className="space-y-4">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633] pb-2">Layout & Motion</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label="Layout Position">
              <select 
                value={style.position} 
                onChange={set('position')} 
                className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white focus:border-[#C45EFF] focus:outline-none transition-colors appearance-none cursor-pointer"
              >
                {POSITIONS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </Field>
            
            <Field label="Active Animation">
              <select 
                value={style.animation} 
                onChange={set('animation')} 
                className="w-full bg-[#0D0C0F] border border-[#2A2633] rounded-xl px-4 py-3 text-sm text-white focus:border-[#C45EFF] focus:outline-none transition-colors appearance-none cursor-pointer"
              >
                {ANIMATIONS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </Field>
          </div>
        </div>

        {/* Pacing & Box Opacity */}
        <div className="space-y-4">
          <h3 className="font-display font-bold text-lg text-white border-b border-[#2A2633] pb-2">Subtitles Settings</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Field label={`Background Box Opacity: ${style.background_opacity}%`}>
              <div className="flex items-center gap-3 h-11">
                <input
                  type="range"
                  min={0}
                  max={100}
                  disabled={!style.background_box}
                  value={style.background_opacity}
                  onChange={setNum('background_opacity')}
                  className="flex-1 accent-[#C45EFF] disabled:opacity-20 cursor-pointer"
                />
              </div>
            </Field>
            <Field label={`Words Per Block: ${style.words_per_block}`}>
              <div className="flex items-center gap-3 h-11">
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={style.words_per_block}
                  onChange={setNum('words_per_block')}
                  className="flex-1 accent-[#C45EFF] cursor-pointer"
                />
              </div>
            </Field>
          </div>
        </div>

        {/* Checkbox Options */}
        <div className="flex flex-wrap items-center gap-6 pt-2">
          <label className="flex items-center gap-2.5 text-sm text-white cursor-pointer select-none font-medium">
            <input 
              type="checkbox" 
              checked={style.background_box} 
              onChange={set('background_box')} 
              className="w-4 h-4 rounded border-[#2A2633] bg-[#0D0C0F] text-[#C45EFF] accent-[#C45EFF] cursor-pointer" 
            />
            Background Box
          </label>
          
          <label className="flex items-center gap-2.5 text-sm text-white cursor-pointer select-none font-medium">
            <input 
              type="checkbox" 
              checked={style.uppercase} 
              onChange={set('uppercase')} 
              className="w-4 h-4 rounded border-[#2A2633] bg-[#0D0C0F] text-[#C45EFF] accent-[#C45EFF] cursor-pointer" 
            />
            Force Uppercase
          </label>
          
          <label className="flex items-center gap-2.5 text-sm text-white cursor-pointer select-none font-medium">
            <input 
              type="checkbox" 
              checked={style.bold} 
              onChange={set('bold')} 
              className="w-4 h-4 rounded border-[#2A2633] bg-[#0D0C0F] text-[#C45EFF] accent-[#C45EFF] cursor-pointer" 
            />
            Bold Weights
          </label>
        </div>

        {/* Actions Button */}
        <div className="pt-4 border-t border-[#2A2633]/50">
          <Button 
            onClick={onSave} 
            disabled={saving}
            className="w-full sm:w-auto rounded-xl bg-gradient-to-tr from-[#C45EFF] to-[#D88EFF] text-white hover:opacity-90 font-bold px-6 py-3 tracking-wide shadow-[0_4px_15px_rgba(196,94,255,0.25)]"
          >
            {saving ? 'Saving Preset...' : 'Save Preset Style'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <label className="block space-y-2">
      <span className="block text-xs font-semibold text-[var(--color-text-dim)] uppercase tracking-wide">{label}</span>
      {children}
    </label>
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
