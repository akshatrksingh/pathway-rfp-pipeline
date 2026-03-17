import { useState, useRef } from 'react'

const labelStyle = {
  display: 'block',
  fontSize: 12,
  color: 'var(--text-muted)',
  marginBottom: 5,
}

const inputStyle = {
  width: '100%',
  padding: '9px 12px',
  border: '0.5px solid var(--border-default)',
  borderRadius: 'var(--radius-md)',
  fontSize: 14,
  color: 'var(--text-primary)',
  background: 'var(--bg-input)',
  boxSizing: 'border-box',
  outline: 'none',
  transition: 'border-color 0.1s',
}

function FocusInput({ style, ...props }) {
  const [focused, setFocused] = useState(false)
  return (
    <input
      {...props}
      style={{
        ...inputStyle,
        ...style,
        borderColor: focused ? '#888780' : 'var(--border-default)',
      }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  )
}

export default function MenuUpload({
  restForm, setRestForm, selectedRestaurant, isParsing, parseError, onParse,
}) {
  const [pdfFile, setPdfFile] = useState(null)
  const [menuUrl, setMenuUrl] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  function handleFile(file) {
    if (file?.type === 'application/pdf') {
      setPdfFile(file)
      setMenuUrl('')
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!pdfFile && !menuUrl.trim()) return
    onParse({ file: pdfFile || null, url: menuUrl.trim() || null })
  }

  const hasSource = pdfFile || menuUrl.trim()
  const hasRestaurant = selectedRestaurant || restForm.name.trim()
  const isReady = hasSource && hasRestaurant && !isParsing

  return (
    <div style={{ maxWidth: 580 }}>
      <h1 style={{
        fontFamily: 'var(--font-serif)',
        fontSize: 22,
        fontWeight: 500,
        color: 'var(--text-primary)',
        marginBottom: 6,
        letterSpacing: '-0.3px',
      }}>
        {selectedRestaurant
          ? `New menu for ${selectedRestaurant.name}`
          : 'Set up a new restaurant'}
      </h1>
      <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 28 }}>
        Upload a PDF menu or paste a URL — we'll extract dishes and ingredients automatically.
      </p>

      <form onSubmit={handleSubmit}>
        {/* Restaurant details — only for new restaurants */}
        {!selectedRestaurant && (
          <div style={{ marginBottom: 28 }}>
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>Restaurant name</label>
              <FocusInput
                placeholder="e.g. Luca's Trattoria"
                value={restForm.name}
                onChange={e => setRestForm(p => ({ ...p, name: e.target.value }))}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 150px 72px', gap: 10 }}>
              <div>
                <label style={labelStyle}>Street address</label>
                <FocusInput
                  placeholder="123 Main St"
                  value={restForm.address}
                  onChange={e => setRestForm(p => ({ ...p, address: e.target.value }))}
                />
              </div>
              <div>
                <label style={labelStyle}>City</label>
                <FocusInput
                  placeholder="Brooklyn"
                  value={restForm.city}
                  onChange={e => setRestForm(p => ({ ...p, city: e.target.value }))}
                />
              </div>
              <div>
                <label style={labelStyle}>State</label>
                <FocusInput
                  placeholder="NY"
                  value={restForm.state}
                  onChange={e => setRestForm(p => ({ ...p, state: e.target.value }))}
                  style={{ textTransform: 'uppercase' }}
                />
              </div>
            </div>
          </div>
        )}

        {/* PDF drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => !pdfFile && fileInputRef.current?.click()}
          style={{
            border: `1.5px dashed ${isDragging ? 'var(--green-strong)' : pdfFile ? 'var(--green-medium)' : 'var(--border-default)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: '28px 24px',
            textAlign: 'center',
            background: isDragging ? 'var(--green-light)' : pdfFile ? '#F5FCF9' : 'var(--bg-card)',
            cursor: pdfFile ? 'default' : 'pointer',
            transition: 'all 0.15s',
            marginBottom: 14,
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={e => handleFile(e.target.files[0])}
          />

          {pdfFile ? (
            <div>
              {/* PDF icon */}
              <div style={{ marginBottom: 8 }}>
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" style={{ margin: '0 auto', display: 'block' }}>
                  <rect x="6" y="2" width="20" height="28" rx="2" fill="#E1F5EE" stroke="var(--green-medium)" strokeWidth="1"/>
                  <path d="M10 10h12M10 15h12M10 20h8" stroke="var(--green-strong)" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
              <div style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 500 }}>{pdfFile.name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                {(pdfFile.size / 1024).toFixed(0)} KB
              </div>
              <button
                type="button"
                onClick={e => { e.stopPropagation(); setPdfFile(null) }}
                style={{
                  marginTop: 8,
                  fontSize: 12,
                  color: 'var(--text-muted)',
                  background: 'none',
                  border: 'none',
                  textDecoration: 'underline',
                  padding: 0,
                }}
              >
                Remove
              </button>
            </div>
          ) : (
            <div>
              {/* Upload icon */}
              <div style={{ marginBottom: 10 }}>
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" style={{ margin: '0 auto', display: 'block' }}>
                  <path d="M14 18V8M14 8L10 12M14 8L18 12" stroke="var(--text-hint)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M6 20h16" stroke="var(--text-hint)" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </div>
              <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                Drop PDF here or{' '}
                <span style={{ color: 'var(--green-strong)', textDecoration: 'underline' }}>
                  click to browse
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-hint)', marginTop: 4 }}>PDF only</div>
            </div>
          )}
        </div>

        {/* OR divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
          <div style={{ flex: 1, height: '0.5px', background: 'var(--border-default)' }} />
          <span style={{ fontSize: 12, color: 'var(--text-hint)' }}>or paste a URL</span>
          <div style={{ flex: 1, height: '0.5px', background: 'var(--border-default)' }} />
        </div>

        {/* URL input */}
        <div style={{ marginBottom: 28 }}>
          <FocusInput
            placeholder="https://restaurant.com/menu"
            value={menuUrl}
            disabled={!!pdfFile}
            onChange={e => setMenuUrl(e.target.value)}
            style={{ opacity: pdfFile ? 0.4 : 1 }}
          />
        </div>

        {/* Error */}
        {parseError && (
          <div style={{
            background: 'var(--red-light)',
            border: '0.5px solid var(--red-strong)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            fontSize: 13,
            color: 'var(--red-text)',
            marginBottom: 16,
          }}>
            {parseError}
          </div>
        )}

        <button
          type="submit"
          disabled={!isReady}
          style={{
            background: isReady ? 'var(--green-strong)' : 'var(--text-hint)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: 'var(--radius-pill)',
            padding: '10px 28px',
            fontSize: 14,
            fontWeight: 500,
            cursor: isReady ? 'pointer' : 'not-allowed',
            transition: 'background 0.15s',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          {isParsing && (
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ animation: 'spin 1s linear infinite' }}>
              <circle cx="7" cy="7" r="5.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5"/>
              <path d="M7 1.5A5.5 5.5 0 0 1 12.5 7" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          )}
          {isParsing ? 'Parsing menu…' : 'Parse menu'}
        </button>
      </form>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
