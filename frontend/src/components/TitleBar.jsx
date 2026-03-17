export default function TitleBar({ restaurantName }) {
  return (
    <div style={{
      background: 'var(--bg-sidebar)',
      borderBottom: '0.5px solid var(--border-default)',
      padding: '10px 16px',
      textAlign: 'center',
      flexShrink: 0,
      userSelect: 'none',
      zIndex: 10,
    }}>
      <span style={{
        fontFamily: 'var(--font-serif)',
        fontSize: 13,
        fontWeight: 500,
        color: 'var(--text-primary)',
        letterSpacing: '-0.1px',
      }}>
        RFP Pipeline{restaurantName ? ` — ${restaurantName}` : ''}
      </span>
    </div>
  )
}
