import { useState, useEffect } from 'react'
import EmailReview from './EmailReview'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PHASE_ORDER = ['pricing', 'distributors', 'email_draft', 'email_review', 'sending', 'done']
const EMAIL_PHASES = new Set(['email_review', 'sending', 'done'])

function stepStatus(currentPhase, stepPhase) {
  const cur = PHASE_ORDER.indexOf(currentPhase)
  const step = PHASE_ORDER.indexOf(stepPhase)
  if (step < cur) return 'complete'
  if (step === cur) return 'running'
  return 'pending'
}

// ---------------------------------------------------------------------------
// Small shared components
// ---------------------------------------------------------------------------

function StatusPill({ status, hasError }) {
  const map = {
    complete: { bg: 'var(--green-light)', color: 'var(--green-strong)', label: 'Complete' },
    running:  { bg: 'var(--amber-light)', color: 'var(--amber-text)',   label: 'Running'  },
    pending:  { bg: 'var(--bg-tag)',      color: 'var(--text-muted)',   label: 'Pending'  },
  }
  const s = hasError ? { bg: 'var(--red-light)', color: 'var(--red-text)', label: 'Error' } : (map[status] || map.pending)
  return (
    <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 'var(--radius-pill)', background: s.bg, color: s.color, whiteSpace: 'nowrap' }}>
      {s.label}
    </span>
  )
}

function Chip({ children, style }) {
  return (
    <span style={{
      fontSize: 12, padding: '3px 10px',
      background: 'var(--bg-tag)',
      borderRadius: 'var(--radius-sm)',
      color: 'var(--text-secondary)',
      ...style,
    }}>
      {children}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Stepper
// ---------------------------------------------------------------------------

function Stepper({ phase }) {
  const steps = [
    { id: 'pricing',      label: 'Pricing'       },
    { id: 'distributors', label: 'Distributors'  },
    { id: 'email_draft',  label: 'Email drafts'  },
  ]

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 32, gap: 0 }}>
      {steps.map((step, i) => {
        const s = stepStatus(phase, step.id)
        const isLast = i === steps.length - 1
        const nextComplete = !isLast && stepStatus(phase, steps[i + 1].id) !== 'pending'

        return (
          <div key={step.id} style={{ display: 'flex', alignItems: 'flex-start' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
                background: s === 'complete' ? 'var(--green-strong)' : s === 'running' ? 'var(--amber-strong)' : 'var(--bg-sidebar)',
                border: s === 'pending' ? '1.5px solid var(--border-default)' : 'none',
                fontSize: 12, fontWeight: 500,
                color: s === 'pending' ? 'var(--text-muted)' : '#fff',
                transition: 'background 0.3s',
              }}>
                {s === 'complete' ? (
                  <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                    <path d="M1.5 5l3 3 6-7" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : s === 'running' ? (
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />
                ) : i + 1}
              </div>
              <span style={{
                fontSize: 11,
                color: s === 'complete' ? 'var(--green-text)' : s === 'running' ? 'var(--amber-text)' : 'var(--text-hint)',
                whiteSpace: 'nowrap',
              }}>
                {step.label}
              </span>
            </div>

            {!isLast && (
              <div style={{
                width: 56, height: 2,
                background: nextComplete || s === 'complete' ? 'var(--green-light)' : 'var(--border-light)',
                margin: '13px 8px 0',
                flexShrink: 0,
                transition: 'background 0.4s',
              }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Pricing results (shown inside step card when complete)
// ---------------------------------------------------------------------------

function PricingResults({ result }) {
  if (!result || !result.results) return null
  const { results, total, llm_count, api_count, cached_count } = result

  return (
    <div>
      <p style={{ fontSize: 12, color: 'var(--text-hint)', marginBottom: 14 }}>
        {total} ingredients priced
        {api_count > 0 && ` · ${api_count} from USDA`}
        {cached_count > 0 && ` · ${cached_count} cached`}
        {llm_count > 0 && ` · ${llm_count} LLM estimates`}
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
        gap: 10,
      }}>
        {results.map(r => {
          const isEstimate = r.source === 'llm_estimate'
          const hasPrice = r.price_avg != null

          return (
            <div key={r.ingredient_id} style={{
              background: isEstimate ? 'var(--amber-light)' : 'var(--bg-tag)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
            }}>
              <div style={{
                fontSize: 11,
                color: isEstimate ? 'var(--amber-text)' : 'var(--text-muted)',
                marginBottom: 6,
                textTransform: 'capitalize',
              }}>
                {r.ingredient_name}
              </div>

              {hasPrice ? (
                <>
                  <div style={{
                    fontSize: 18, fontWeight: 500,
                    color: isEstimate ? 'var(--amber-text)' : 'var(--text-primary)',
                    lineHeight: 1.1,
                  }}>
                    ${r.price_avg.toFixed(2)}
                    <span style={{ fontSize: 12, fontWeight: 400, color: isEstimate ? 'var(--amber-text)' : 'var(--text-muted)', marginLeft: 4 }}>
                      /{r.unit || 'unit'}
                    </span>
                  </div>
                  {(r.price_low != null || r.price_high != null) && (
                    <div style={{ fontSize: 11, color: isEstimate ? 'var(--amber-text)' : 'var(--text-hint)', marginTop: 4 }}>
                      {r.price_low != null && `$${r.price_low.toFixed(2)}`}
                      {r.price_low != null && r.price_high != null && ' – '}
                      {r.price_high != null && `$${r.price_high.toFixed(2)}`}
                    </div>
                  )}
                </>
              ) : (
                <div style={{ fontSize: 13, color: 'var(--text-hint)' }}>—</div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 8 }}>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: isEstimate ? 'var(--amber-strong)' : 'var(--green-strong)',
                  flexShrink: 0,
                }} />
                <span style={{ fontSize: 10, color: isEstimate ? 'var(--amber-text)' : 'var(--green-text)' }}>
                  {isEstimate ? 'LLM estimate' : r.source === 'cached' ? 'cached' : 'high confidence'}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Distributor results (shown inside step card when complete)
// ---------------------------------------------------------------------------

function DistributorResults({ result }) {
  if (!result) return null
  const { coverage, gaps, total_ingredients, covered_count, gap_count } = result

  return (
    <div>
      <p style={{ fontSize: 12, color: 'var(--text-hint)', marginBottom: 14 }}>
        {covered_count} of {total_ingredients} ingredients covered
        {gap_count > 0 && ` · ${gap_count} without a distributor`}
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {coverage.map((cov, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 11, padding: '3px 10px',
              background: 'var(--green-light)',
              color: 'var(--green-text)',
              borderRadius: 'var(--radius-pill)',
              flexShrink: 0,
              textTransform: 'capitalize',
            }}>
              {cov.category}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)', paddingTop: 2 }}>
              {cov.distributor_names.slice(0, 3).join(', ')}
              {cov.distributor_names.length > 3 && ` +${cov.distributor_names.length - 3}`}
            </span>
          </div>
        ))}

        {gaps.length > 0 && (
          <div style={{ marginTop: 4 }}>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>No distributor found for:</p>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {gaps.flatMap(g => g.ingredient_names).map((name, i) => (
                <Chip key={i} style={{ background: 'var(--red-light)', color: 'var(--red-text)' }}>{name}</Chip>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step card
// ---------------------------------------------------------------------------

function StepCard({ title, phase, stepPhase, hasError, errorMsg, isExpanded, onToggle, children }) {
  const status = hasError ? 'error' : stepStatus(phase, stepPhase)
  const isRunning = status === 'running'
  const isComplete = status === 'complete'
  const isPending = status === 'pending'

  const runningLabels = {
    pricing:      'Looking up ingredient prices…',
    distributors: 'Searching for local distributors…',
    email_draft:  'Drafting RFP emails…',
  }

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: isRunning
        ? '1.5px solid var(--amber-strong)'
        : hasError
          ? '1px solid var(--red-strong)'
          : '0.5px solid var(--border-default)',
      borderRadius: 'var(--radius-lg)',
      marginBottom: 10,
      overflow: 'hidden',
      opacity: isPending ? 0.45 : 1,
      transition: 'opacity 0.3s, border-color 0.4s',
    }}>
      <div style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontFamily: 'var(--font-serif)', fontSize: 16, fontWeight: 500, color: 'var(--text-primary)' }}>
              {title}
            </span>
            <StatusPill status={status} hasError={hasError} />
          </div>

          {isComplete && children && (
            <button
              onClick={onToggle}
              style={{ background: 'none', border: 'none', color: 'var(--text-hint)', cursor: 'pointer', padding: 4, display: 'flex' }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path
                  d={isExpanded ? 'M3 9l4-4 4 4' : 'M3 5l4 4 4-4'}
                  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
                />
              </svg>
            </button>
          )}
        </div>

        {isRunning && (
          <div style={{ marginTop: 12 }}>
            <div style={{ height: 3, background: 'var(--border-light)', borderRadius: 2, overflow: 'hidden' }}>
              <div
                key={stepPhase}
                className="progress-sweep"
                style={{ height: '100%', background: 'var(--amber-strong)', borderRadius: 2 }}
              />
            </div>
            <p className="pulse" style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
              {runningLabels[stepPhase]}
            </p>
          </div>
        )}

        {hasError && (
          <p style={{ fontSize: 12, color: 'var(--red-text)', marginTop: 6 }}>{errorMsg}</p>
        )}
      </div>

      {isComplete && isExpanded && children && (
        <div style={{ borderTop: '0.5px solid var(--border-light)', padding: '14px 20px' }}>
          {children}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PipelineProgress({ runId }) {
  const [phase, setPhase] = useState('pricing')
  const [pricingResult, setPricingResult] = useState(null)
  const [distributorResult, setDistributorResult] = useState(null)
  const [emails, setEmails] = useState([])
  const [sendResults, setSendResults] = useState(null)
  const [errors, setErrors] = useState({})
  const [expanded, setExpanded] = useState({ pricing: true, distributors: true })

  useEffect(() => {
    runPipeline()
  }, [runId])

  async function runPipeline() {
    // Step 1: Pricing
    try {
      setPhase('pricing')
      const resp = await fetch(`/api/pipeline/${runId}/pricing`, { method: 'POST' })
      if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Pricing failed')
      const data = await resp.json()
      setPricingResult(data)
    } catch (e) {
      setErrors(prev => ({ ...prev, pricing: e.message }))
      return
    }

    // Step 2: Distributors
    try {
      setPhase('distributors')
      const resp = await fetch(`/api/pipeline/${runId}/distributors`, { method: 'POST' })
      if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Distributor search failed')
      const data = await resp.json()
      setDistributorResult(data)
    } catch (e) {
      setErrors(prev => ({ ...prev, distributors: e.message }))
      return
    }

    // Step 3: Email draft
    try {
      setPhase('email_draft')
      const resp = await fetch(`/api/pipeline/${runId}/emails/draft`, { method: 'POST' })
      if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).detail || 'Email drafting failed')
      const data = await resp.json()
      setEmails(data.emails.map(e => ({
        ...e,
        included: true,
        editBody: e.body,
        editSubject: e.subject,
        isExpanded: false,
        editInstruction: '',
        isRevising: false,
      })))
      setPhase('email_review')
    } catch (e) {
      setErrors(prev => ({ ...prev, email_draft: e.message }))
    }
  }

  async function handleSend(emailIds) {
    setPhase('sending')
    try {
      const resp = await fetch(`/api/pipeline/${runId}/emails/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email_ids: emailIds }),
      })
      if (!resp.ok) throw new Error('Send failed')
      const data = await resp.json()
      setSendResults(data)
      setPhase('done')
    } catch (e) {
      setErrors(prev => ({ ...prev, send: e.message }))
      setPhase('email_review')
    }
  }

  // After all steps → hand off to email review
  if (EMAIL_PHASES.has(phase)) {
    return (
      <EmailReview
        emails={emails}
        setEmails={setEmails}
        distributorResult={distributorResult}
        onSend={handleSend}
        isSending={phase === 'sending'}
        sendError={errors.send || null}
        sendResults={sendResults}
        isDone={phase === 'done'}
      />
    )
  }

  return (
    <div style={{ maxWidth: 680 }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{
          fontFamily: 'var(--font-serif)',
          fontSize: 22, fontWeight: 500,
          color: 'var(--text-primary)',
          marginBottom: 6, letterSpacing: '-0.3px',
        }}>
          Running pipeline
        </h1>
        <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
          Run #{runId} · Steps run automatically — sit tight.
        </p>
      </div>

      <Stepper phase={phase} />

      <StepCard
        title="Pricing ingredients"
        phase={phase}
        stepPhase="pricing"
        hasError={!!errors.pricing}
        errorMsg={errors.pricing}
        isExpanded={expanded.pricing}
        onToggle={() => setExpanded(prev => ({ ...prev, pricing: !prev.pricing }))}
      >
        <PricingResults result={pricingResult} />
      </StepCard>

      <StepCard
        title="Finding distributors"
        phase={phase}
        stepPhase="distributors"
        hasError={!!errors.distributors}
        errorMsg={errors.distributors}
        isExpanded={expanded.distributors}
        onToggle={() => setExpanded(prev => ({ ...prev, distributors: !prev.distributors }))}
      >
        <DistributorResults result={distributorResult} />
      </StepCard>

      <StepCard
        title="Drafting RFP emails"
        phase={phase}
        stepPhase="email_draft"
        hasError={!!errors.email_draft}
        errorMsg={errors.email_draft}
        isExpanded={false}
        onToggle={() => {}}
      >
        {null}
      </StepCard>
    </div>
  )
}
