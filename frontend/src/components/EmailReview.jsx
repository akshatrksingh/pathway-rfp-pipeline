import { useState } from 'react'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function slugify(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

function recipientFor(name) {
  return `akshatrksingh+${slugify(name)}@gmail.com`
}

function getIngredientsForDistributor(distributorResult, distributorId) {
  if (!distributorResult?.coverage) return []
  const names = new Set()
  for (const cov of distributorResult.coverage) {
    if (cov.distributor_ids.includes(distributorId)) {
      cov.ingredient_names.forEach(n => names.add(n))
    }
  }
  return [...names]
}

// ---------------------------------------------------------------------------
// Send summary (shown after emails are sent)
// ---------------------------------------------------------------------------

function SendSummary({ sendResults, emails }) {
  const sentCount = sendResults?.sent_count ?? 0
  const results = sendResults?.results ?? []

  // Map email_id → email for looking up distributor name
  const emailById = Object.fromEntries(emails.map(e => [e.id, e]))

  return (
    <div style={{ maxWidth: 640 }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: 'var(--green-light)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <svg width="16" height="14" viewBox="0 0 16 14" fill="none">
              <path d="M1.5 7l4 4 9-9" stroke="var(--green-strong)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 500, color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
              Emails sent
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 2 }}>
              {sentCount} RFP email{sentCount !== 1 ? 's' : ''} dispatched to distributors.
            </p>
          </div>
        </div>
      </div>

      {/* Results list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {results.map(r => {
          const email = emailById[r.email_id]
          const distName = email?.distributor?.name ?? `Distributor #${r.email_id}`

          return (
            <div key={r.email_id} style={{
              background: 'var(--bg-card)',
              border: '0.5px solid var(--border-default)',
              borderRadius: 'var(--radius-lg)',
              padding: '14px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: 14,
            }}>
              {/* Check icon */}
              <div style={{
                width: 28, height: 28, borderRadius: '50%',
                background: 'var(--green-light)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                  <path d="M1 5l3.5 3.5L11 1" stroke="var(--green-strong)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--font-serif)', fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                  {distName}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-hint)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.recipient}
                </div>
              </div>

              <span style={{
                fontSize: 11, padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                background: 'var(--green-light)', color: 'var(--green-strong)',
                flexShrink: 0,
              }}>
                Sent
              </span>
            </div>
          )
        })}
      </div>

      {/* Footer note */}
      <p style={{ fontSize: 12, color: 'var(--text-hint)', marginTop: 20 }}>
        Quotes will arrive by reply email. Check back to compare pricing.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Individual email card
// ---------------------------------------------------------------------------

function EmailCard({ email, ingredients, onToggle, onChange, onRevise }) {
  const dist = email.distributor || {}
  const isExpanded = email.isExpanded

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: email.included
        ? '0.5px solid var(--border-default)'
        : '0.5px solid var(--border-light)',
      borderRadius: 'var(--radius-lg)',
      marginBottom: 10,
      overflow: 'hidden',
      opacity: email.included ? 1 : 0.45,
      transition: 'opacity 0.2s, border-color 0.2s',
    }}>
      {/* Card header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 20px', gap: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
          {/* Include toggle */}
          <button
            onClick={() => onChange('included', !email.included)}
            title={email.included ? 'Skip this email' : 'Include this email'}
            style={{
              width: 20, height: 20, borderRadius: 4,
              border: email.included ? 'none' : '1.5px solid var(--border-default)',
              background: email.included ? 'var(--green-strong)' : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', flexShrink: 0, padding: 0,
              transition: 'background 0.15s',
            }}
          >
            {email.included && (
              <svg width="11" height="9" viewBox="0 0 11 9" fill="none">
                <path d="M1 4.5l3 3 6-7" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </button>

          <div style={{ minWidth: 0 }}>
            <span style={{
              fontFamily: 'var(--font-serif)', fontSize: 15, fontWeight: 500,
              color: 'var(--text-primary)', display: 'block',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {dist.name || 'Unknown distributor'}
            </span>
            {dist.specialty && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{dist.specialty}</span>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          {/* Ingredient chips (compact, max 3) */}
          <div style={{ display: 'flex', gap: 5, flexWrap: 'nowrap', overflow: 'hidden' }}>
            {ingredients.slice(0, 3).map((name, i) => (
              <span key={i} style={{
                fontSize: 11, padding: '2px 8px',
                background: 'var(--bg-tag)', borderRadius: 'var(--radius-sm)',
                color: 'var(--text-secondary)', whiteSpace: 'nowrap',
              }}>
                {name}
              </span>
            ))}
            {ingredients.length > 3 && (
              <span style={{ fontSize: 11, color: 'var(--text-hint)', whiteSpace: 'nowrap' }}>
                +{ingredients.length - 3}
              </span>
            )}
          </div>

          {/* Expand chevron */}
          <button
            onClick={() => onChange('isExpanded', !isExpanded)}
            style={{ background: 'none', border: 'none', color: 'var(--text-hint)', cursor: 'pointer', padding: 4, display: 'flex' }}
          >
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path
                d={isExpanded ? 'M2.5 8.5l4-4 4 4' : 'M2.5 4.5l4 4 4-4'}
                stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Expanded body */}
      {isExpanded && (
        <div style={{ borderTop: '0.5px solid var(--border-light)', padding: '16px 20px' }}>
          {/* All ingredient chips */}
          {ingredients.length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
              {ingredients.map((name, i) => (
                <span key={i} style={{
                  fontSize: 12, padding: '3px 10px',
                  background: 'var(--bg-tag)', borderRadius: 'var(--radius-sm)',
                  color: 'var(--text-secondary)',
                }}>
                  {name}
                </span>
              ))}
            </div>
          )}

          {/* Subject */}
          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: 5 }}>
              Subject
            </label>
            <input
              value={email.editSubject}
              onChange={e => onChange('editSubject', e.target.value)}
              style={{
                width: '100%', padding: '7px 10px',
                border: '0.5px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
                fontSize: 13, color: 'var(--text-primary)',
                background: 'var(--bg-input)', outline: 'none',
              }}
              onFocus={e => { e.target.style.borderColor = 'var(--border-default)' }}
              onBlur={e => { e.target.style.borderColor = 'var(--border-light)' }}
            />
          </div>

          {/* Body */}
          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: 5 }}>
              Body
            </label>
            <textarea
              value={email.editBody}
              onChange={e => onChange('editBody', e.target.value)}
              rows={10}
              style={{
                width: '100%', padding: '10px 12px',
                border: '0.5px solid var(--border-light)',
                borderRadius: 'var(--radius-md)',
                fontSize: 13, lineHeight: 1.6,
                color: 'var(--text-primary)',
                background: 'var(--bg-input)',
                resize: 'vertical', outline: 'none',
                fontFamily: 'var(--font-sans)',
              }}
              onFocus={e => { e.target.style.borderColor = 'var(--border-default)' }}
              onBlur={e => { e.target.style.borderColor = 'var(--border-light)' }}
            />
          </div>

          {/* Prompt-to-edit */}
          <div style={{
            display: 'flex', gap: 8,
            background: 'var(--bg-tag)',
            borderRadius: 'var(--radius-md)',
            padding: '8px 10px',
            alignItems: 'flex-end',
          }}>
            <input
              value={email.editInstruction}
              onChange={e => onChange('editInstruction', e.target.value)}
              disabled={email.isRevising}
              placeholder="Ask AI to adjust… e.g. 'make it more formal' or 'add cold-chain requirements'"
              onKeyDown={e => {
                if (e.key === 'Enter' && email.editInstruction.trim() && !email.isRevising) {
                  onRevise(email.id, email.editInstruction)
                }
              }}
              style={{
                flex: 1, background: 'transparent', border: 'none',
                fontSize: 13, color: 'var(--text-primary)', outline: 'none',
                padding: '2px 0',
              }}
            />
            <button
              onClick={() => email.editInstruction.trim() && !email.isRevising && onRevise(email.id, email.editInstruction)}
              disabled={!email.editInstruction.trim() || email.isRevising}
              style={{
                background: email.editInstruction.trim() && !email.isRevising ? 'var(--green-strong)' : 'var(--border-default)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: email.editInstruction.trim() && !email.isRevising ? 'pointer' : 'not-allowed',
                flexShrink: 0,
                transition: 'background 0.15s',
              }}
              title="Revise with AI"
            >
              {email.isRevising ? (
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff' }} className="pulse" />
              ) : (
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M1 6h10M6 1l5 5-5 5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main EmailReview component
// ---------------------------------------------------------------------------

export default function EmailReview({
  emails, setEmails,
  distributorResult,
  onSend, isSending, sendError, sendResults, isDone,
}) {
  // Show summary after done
  if (isDone && sendResults) {
    return <SendSummary sendResults={sendResults} emails={emails} />
  }

  const includedEmails = emails.filter(e => e.included)
  const includedCount = includedEmails.length
  const totalCount = emails.length

  function updateEmail(id, field, value) {
    setEmails(prev => prev.map(e => e.id === id ? { ...e, [field]: value } : e))
  }

  async function handleRevise(emailId, instruction) {
    updateEmail(emailId, 'isRevising', true)
    updateEmail(emailId, 'editInstruction', '')
    try {
      const resp = await fetch(`/api/emails/${emailId}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction }),
      })
      if (!resp.ok) throw new Error('Edit failed')
      const data = await resp.json()
      setEmails(prev => prev.map(e =>
        e.id === emailId
          ? { ...e, editSubject: data.subject, editBody: data.body, isRevising: false }
          : e
      ))
    } catch {
      updateEmail(emailId, 'isRevising', false)
    }
  }

  function handleSendSelected() {
    const ids = includedEmails.map(e => e.id)
    if (ids.length === 0) return
    onSend(ids)
  }

  function handleSendAll() {
    setEmails(prev => prev.map(e => ({ ...e, included: true })))
    onSend(null)
  }

  return (
    <div style={{ maxWidth: 680 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, gap: 16 }}>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 500,
            color: 'var(--text-primary)', marginBottom: 6, letterSpacing: '-0.3px',
          }}>
            Review RFP emails
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
            {totalCount} emails drafted · {includedCount} selected · edit or skip before sending
          </p>
        </div>

        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          <button
            onClick={handleSendSelected}
            disabled={isSending || includedCount === 0}
            style={{
              background: 'transparent',
              color: includedCount === 0 || isSending ? 'var(--text-hint)' : 'var(--text-primary)',
              border: '0.5px solid var(--border-default)',
              borderRadius: 'var(--radius-pill)',
              padding: '9px 18px', fontSize: 13, fontWeight: 500,
              cursor: includedCount === 0 || isSending ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            Send selected ({includedCount})
          </button>
          <button
            onClick={handleSendAll}
            disabled={isSending}
            style={{
              background: isSending ? 'var(--text-hint)' : 'var(--green-strong)',
              color: '#fff', border: 'none',
              borderRadius: 'var(--radius-pill)',
              padding: '9px 20px', fontSize: 13, fontWeight: 500,
              cursor: isSending ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {isSending ? 'Sending…' : 'Send all'}
          </button>
        </div>
      </div>

      {/* Error */}
      {sendError && (
        <div style={{
          background: 'var(--red-light)', border: '0.5px solid var(--red-strong)',
          borderRadius: 'var(--radius-md)', padding: '10px 14px',
          fontSize: 13, color: 'var(--red-text)', marginBottom: 16,
        }}>
          {sendError}
        </div>
      )}

      {/* Select all / deselect all */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
        <button
          onClick={() => setEmails(prev => prev.map(e => ({ ...e, included: true })))}
          style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline' }}
        >
          Select all
        </button>
        <button
          onClick={() => setEmails(prev => prev.map(e => ({ ...e, included: false })))}
          style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline' }}
        >
          Deselect all
        </button>
        <button
          onClick={() => setEmails(prev => prev.map(e => ({ ...e, isExpanded: true })))}
          style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline' }}
        >
          Expand all
        </button>
        <button
          onClick={() => setEmails(prev => prev.map(e => ({ ...e, isExpanded: false })))}
          style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline' }}
        >
          Collapse all
        </button>
      </div>

      {/* Email cards */}
      {emails.map(email => (
        <EmailCard
          key={email.id}
          email={email}
          ingredients={getIngredientsForDistributor(distributorResult, email.distributor_id)}
          onToggle={() => updateEmail(email.id, 'included', !email.included)}
          onChange={(field, value) => updateEmail(email.id, field, value)}
          onRevise={handleRevise}
        />
      ))}

      {/* Bottom send bar */}
      <div style={{ paddingTop: 8, paddingBottom: 32, display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          onClick={handleSendSelected}
          disabled={isSending || includedCount === 0}
          style={{
            background: isSending || includedCount === 0 ? 'var(--text-hint)' : 'var(--green-strong)',
            color: '#fff', border: 'none',
            borderRadius: 'var(--radius-pill)',
            padding: '11px 28px', fontSize: 14, fontWeight: 500,
            cursor: isSending || includedCount === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          {isSending ? 'Sending…' : `Send ${includedCount} email${includedCount !== 1 ? 's' : ''}`}
        </button>
        <span style={{ fontSize: 13, color: 'var(--text-hint)' }}>
          Nothing is sent until you click Send.
        </span>
      </div>
    </div>
  )
}
