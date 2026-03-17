export default function ConfirmModal({ title, message, confirmLabel = 'Confirm', danger = false, onConfirm, onCancel }) {
  return (
    <div
      onClick={onCancel}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        backdropFilter: 'blur(4px)',
        background: 'rgba(44, 44, 42, 0.18)',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--bg-card)',
          border: '0.5px solid var(--border-default)',
          borderRadius: 16,
          padding: '28px 32px',
          maxWidth: 380,
          width: '90%',
          boxShadow: '0 12px 48px rgba(0,0,0,0.14)',
        }}
      >
        <h2 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: 18, fontWeight: 500,
          color: 'var(--text-primary)',
          marginBottom: 10,
        }}>
          {title}
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 26, lineHeight: 1.55 }}>
          {message}
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button
            onClick={onCancel}
            style={{
              background: 'transparent',
              border: '0.5px solid var(--border-default)',
              borderRadius: 'var(--radius-pill)',
              padding: '8px 18px',
              fontSize: 13, fontWeight: 500,
              color: 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            style={{
              background: danger ? 'var(--red-strong, #C0392B)' : 'var(--green-strong)',
              border: 'none',
              borderRadius: 'var(--radius-pill)',
              padding: '8px 20px',
              fontSize: 13, fontWeight: 500,
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
