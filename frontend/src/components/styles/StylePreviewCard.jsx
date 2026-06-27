/**
 * StylePreviewCard
 *
 * Renders a small mock video frame styled with the given CaptionStyle
 * so users can compare presets visually before applying one, without
 * needing a real rendered clip.
 */
export default function StylePreviewCard({ style, selected, onClick, actions }) {
  const textTransform = style.uppercase ? 'uppercase' : 'none'
  const fontWeight = style.bold ? 700 : 400
  const justify = style.position === 'top' ? 'flex-start' : style.position === 'middle' ? 'center' : 'flex-end'

  return (
    <div
      onClick={onClick}
      className={`group relative rounded-xl overflow-hidden border cursor-pointer transition-all duration-150 ${
        selected
          ? 'border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]'
          : 'border-[var(--color-border)] hover:border-[var(--color-text-faint)]'
      }`}
    >
      <div
        className="aspect-[9/16] flex flex-col p-4 relative"
        style={{
          justifyContent: justify,
          background:
            'linear-gradient(160deg, #2a2438 0%, #1a1d24 45%, #14171c 100%)',
        }}
      >
        <span
          className="self-center text-center leading-tight px-2 py-1 rounded"
          style={{
            fontFamily: style.font_family,
            fontSize: Math.min(style.font_size, 30),
            color: style.text_color,
            textTransform,
            fontWeight,
            WebkitTextStroke: style.outline_width ? `${Math.min(style.outline_width, 3) / 2}px ${style.outline_color}` : undefined,
            textShadow: style.shadow_strength
              ? `0 ${style.shadow_strength}px ${style.shadow_strength * 2}px rgba(0,0,0,0.6)`
              : undefined,
            background: style.background_box
              ? `${style.outline_color}${Math.round((style.background_opacity / 100) * 255)
                  .toString(16)
                  .padStart(2, '0')}`
              : 'transparent',
          }}
        >
          {style.animation === 'kinetic' || style.animation === 'word-pop' ? (
            <>
              MAKE <span style={{ color: style.highlight_color, fontSize: '1.16em' }}>IT</span> POP
            </>
          ) : style.name.toUpperCase()}
        </span>
      </div>

      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {actions}
      </div>

      <div className="px-3 py-2.5 bg-[var(--color-surface)] border-t border-[var(--color-border)]">
        <p className="text-xs font-medium truncate">{style.name}</p>
        <p className="text-[10px] text-[var(--color-text-faint)] font-mono mt-0.5">
          {style.font_family} · {style.font_size}px · {style.animation}
        </p>
      </div>
    </div>
  )
}
