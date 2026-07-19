/**
 * StylePreviewCard
 *
 * Renders a mock video frame styled with the CaptionStyle
 * so users can compare presets visually.
 */
export default function StylePreviewCard({ style, selected, onClick, actions }) {
  const textTransform = style.uppercase ? 'uppercase' : 'none'
  const fontWeight = style.bold ? 700 : 400
  const justify = style.position === 'top' ? 'flex-start' : style.position === 'middle' ? 'center' : 'flex-end'

  return (
    <div
      onClick={onClick}
      className={`group relative rounded-2xl overflow-hidden border cursor-pointer transition-all duration-300 ${
        selected
          ? 'border-[#C45EFF] shadow-[0_0_20px_rgba(196,94,255,0.25)] ring-1 ring-[#C45EFF]/40'
          : 'border-[#2A2633] hover:border-[#C45EFF]/30 hover:shadow-[0_8px_24px_rgba(0,0,0,0.5)]'
      }`}
    >
      {/* 9:16 Mock Phone Screen */}
      <div
        className="aspect-[9/16] flex flex-col p-4 relative overflow-hidden bg-gradient-to-b from-[#1F1C24] via-[#141318] to-[#0D0C0F]"
        style={{ justifyContent: justify }}
      >
        {/* Mock phone notch/speaker bezel */}
        <div className="absolute top-2.5 left-1/2 -translate-x-1/2 w-12 h-1 rounded-full bg-[#2A2633] opacity-60 pointer-events-none" />
        
        {/* Dynamic Preview Text */}
        <span
          className="self-center text-center leading-tight px-3 py-1.5 rounded-xl select-none"
          style={{
            fontFamily: style.font_family,
            fontSize: Math.min(style.font_size, 26),
            color: style.text_color,
            textTransform,
            fontWeight,
            WebkitTextStroke: style.outline_width ? `${Math.min(style.outline_width, 3) / 1.8}px ${style.outline_color}` : undefined,
            textShadow: style.shadow_strength
              ? `0 ${style.shadow_strength * 1.5}px ${style.shadow_strength * 3}px rgba(0,0,0,0.8)`
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

      {/* Floating Actions */}
      <div className="absolute top-3 right-3 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-20">
        {actions}
      </div>

      {/* Footer Details */}
      <div className="p-4 bg-[#141318] border-t border-[#2A2633]">
        <p className="text-xs font-bold text-white truncate">{style.name}</p>
        <p className="text-[10px] text-[var(--color-text-dim)] font-mono mt-1">
          {style.font_family} · {style.font_size}px · {style.animation}
        </p>
      </div>
    </div>
  )
}
