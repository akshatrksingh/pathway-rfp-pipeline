import { useState, useRef } from 'react'

const ACCEPTED_TYPES = new Set(['application/pdf', 'image/png', 'image/jpeg', 'image/jpg', 'image/webp'])
const ACCEPTED_EXTS  = new Set(['.pdf', '.png', '.jpg', '.jpeg', '.webp'])
const MAX_BYTES      = 30 * 1024 * 1024  // 30 MB

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
      style={{ ...inputStyle, ...style, borderColor: focused ? '#888780' : 'var(--border-default)' }}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
    />
  )
}

function FileIcon({ isPdf }) {
  if (isPdf) {
    return (
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" style={{ margin: '0 auto', display: 'block' }}>
        <rect x="6" y="2" width="20" height="28" rx="2" fill="#E1F5EE" stroke="var(--green-medium)" strokeWidth="1"/>
        <path d="M10 10h12M10 15h12M10 20h8" stroke="var(--green-strong)" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    )
  }
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" style={{ margin: '0 auto', display: 'block' }}>
      <rect x="4" y="4" width="24" height="24" rx="3" fill="#E1F5EE" stroke="var(--green-medium)" strokeWidth="1"/>
      <circle cx="11" cy="12" r="2.5" fill="var(--green-medium)"/>
      <path d="M4 22l7-7 5 5 4-4 8 8" stroke="var(--green-strong)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function validateFile(file) {
  const ext = '.' + (file.name || '').split('.').pop().toLowerCase()
  const type = (file.type || '').toLowerCase()

  if (!ACCEPTED_TYPES.has(type) && !ACCEPTED_EXTS.has(ext)) {
    return 'Please upload a PDF or image file (PNG, JPG, JPEG).'
  }
  if (file.size > MAX_BYTES) {
    return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Please upload a file under 30 MB.`
  }
  return null
}

export default function MenuUpload({
  restForm, setRestForm, selectedRestaurant, isParsing, parseError, onParse,
}) {
  const [file, setFile]             = useState(null)
  const [fileError, setFileError]   = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef(null)

  function handleFile(f) {
    if (!f) return
    const err = validateFile(f)
    if (err) {
      setFileError(err)
      setFile(null)
      return
    }
    setFileError(null)
    setFile(f)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!file) return
    onParse({ file })
  }

  const isPdf    = file?.type === 'application/pdf' || file?.name?.endsWith('.pdf')
  const needsState = !selectedRestaurant && !restForm.state.trim()
  const isReady  = file && (selectedRestaurant || (restForm.name.trim() && restForm.state.trim())) && !isParsing
  const anyError = fileError || parseError

  return (
    <div style={{ position: 'relative', minHeight: 480 }}>

      {/* ── Left: form content ── */}
      <div style={{ position: 'relative', maxWidth: 520 }}>
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
          Upload a PDF or image of your menu — we'll extract dishes and ingredients automatically.
        </p>

        <form onSubmit={handleSubmit}>
          {/* Restaurant fields — new only */}
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
                  <label style={{ ...labelStyle, color: needsState && file ? 'var(--amber-text)' : 'var(--text-muted)' }}>
                    State{needsState && file ? ' *' : ''}
                  </label>
                  <FocusInput
                    placeholder="NY"
                    value={restForm.state}
                    onChange={e => setRestForm(p => ({ ...p, state: e.target.value.toUpperCase() }))}
                    style={{
                      textTransform: 'uppercase',
                      ...(needsState && file ? { borderColor: 'var(--amber-strong)' } : {}),
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => !file && inputRef.current?.click()}
            style={{
              border: `1.5px dashed ${
                anyError   ? 'var(--red-strong)'   :
                isDragging ? 'var(--green-strong)' :
                file       ? 'var(--green-medium)' :
                             'var(--border-default)'
              }`,
              borderRadius: 'var(--radius-lg)',
              padding: '28px 24px',
              textAlign: 'center',
              background: anyError ? 'var(--red-light)' : isDragging ? 'var(--green-light)' : file ? '#F5FCF9' : 'var(--bg-card)',
              cursor: file ? 'default' : 'pointer',
              transition: 'all 0.15s',
              marginBottom: anyError ? 10 : 28,
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              style={{ display: 'none' }}
              onChange={e => handleFile(e.target.files[0])}
            />

            {file ? (
              <div>
                <div style={{ marginBottom: 8 }}><FileIcon isPdf={isPdf} /></div>
                <div style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 500 }}>{file.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {(file.size / 1024 / 1024).toFixed(1)} MB · {isPdf ? 'PDF' : 'Image'}
                </div>
                <button
                  type="button"
                  onClick={e => { e.stopPropagation(); setFile(null); setFileError(null) }}
                  style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', textDecoration: 'underline', padding: 0, cursor: 'pointer' }}
                >
                  Remove
                </button>
              </div>
            ) : (
              <div>
                <div style={{ marginBottom: 10 }}>
                  <svg width="28" height="28" viewBox="0 0 28 28" fill="none" style={{ margin: '0 auto', display: 'block' }}>
                    <path d="M14 18V8M14 8L10 12M14 8L18 12" stroke="var(--text-hint)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M6 20h16" stroke="var(--text-hint)" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </div>
                <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
                  Drop file here or{' '}
                  <span style={{ color: 'var(--green-strong)', textDecoration: 'underline' }}>browse</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-hint)', marginTop: 5 }}>
                  PDF · PNG · JPG · JPEG &nbsp;·&nbsp; Max 30 MB
                </div>
              </div>
            )}
          </div>

          {/* Error */}
          {anyError && (
            <div style={{
              background: 'var(--red-light)',
              border: '0.5px solid var(--red-strong)',
              borderRadius: 'var(--radius-md)',
              padding: '10px 14px',
              fontSize: 13,
              color: 'var(--red-text)',
              marginBottom: 20,
            }}>
              {anyError}
            </div>
          )}

          {needsState && file && (
            <p style={{ fontSize: 12, color: 'var(--amber-text)', marginBottom: 12 }}>
              Enter a state to enable distributor search and email personalization.
            </p>
          )}
          <button
            type="submit"
            disabled={!isReady}
            style={{
              background: isReady ? 'var(--green-strong)' : 'var(--text-hint)',
              color: '#fff',
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
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
