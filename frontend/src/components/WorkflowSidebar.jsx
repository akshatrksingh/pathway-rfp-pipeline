const STEPS = [
  { id: 'upload',       label: 'Upload menu'        },
  { id: 'servings',     label: 'Review dishes'       },
  { id: 'review',       label: 'Review ingredients'  },
  { id: 'pricing',      label: 'Pricing'             },
  { id: 'distributors', label: 'Find distributors'   },
  { id: 'email_draft',  label: 'Draft emails'        },
  { id: 'email_review', label: 'Review emails'       },
  { id: 'done',         label: 'Send & track'        },
]

function viewToStepId(view, pipelinePhase) {
  if (view === 'upload')    return 'upload'
  if (view === 'servings')  return 'servings'
  if (view === 'review')    return 'review'
  if (view === 'pipeline') {
    if (pipelinePhase === 'sending') return 'email_review'
    if (pipelinePhase === 'done')    return 'done'
    return pipelinePhase  // 'pricing' | 'distributors' | 'email_draft' | 'email_review'
  }
  return 'upload'
}

export default function WorkflowSidebar({ view, pipelinePhase }) {
  const currentId    = viewToStepId(view, pipelinePhase)
  const currentIndex = STEPS.findIndex(s => s.id === currentId)

  return (
    <aside style={{
      width: 188,
      flexShrink: 0,
      borderLeft: '0.5px solid var(--border-default)',
      background: 'var(--bg-sidebar)',
      padding: '24px 16px',
      overflowY: 'auto',
    }}>
      <div style={{
        fontSize: 11,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        color: 'var(--text-muted)',
        marginBottom: 16,
      }}>
        Progress
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {STEPS.map((step, i) => {
          const isComplete = i < currentIndex
          const isCurrent  = i === currentIndex
          const isFuture   = i > currentIndex

          return (
            <div key={step.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 8px', borderRadius: 'var(--radius-md)' }}>
              {/* Dot / check */}
              <div style={{
                width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: isComplete ? 'var(--green-strong)' : isCurrent ? 'var(--green-strong)' : 'transparent',
                border: isFuture ? '1.5px solid var(--border-default)' : 'none',
                transition: 'background 0.3s',
              }}>
                {isComplete ? (
                  <svg width="9" height="8" viewBox="0 0 9 8" fill="none">
                    <path d="M1.5 4l2.5 2.5 4-5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : isCurrent ? (
                  <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#fff' }} />
                ) : null}
              </div>

              {/* Label */}
              <span style={{
                fontSize: 12,
                color: isFuture ? 'var(--text-hint)' : 'var(--text-primary)',
                fontWeight: isCurrent ? 500 : 400,
                lineHeight: 1.3,
              }}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
