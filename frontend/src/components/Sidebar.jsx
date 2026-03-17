const SectionLabel = ({ children }) => (
  <div style={{
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: 'var(--text-muted)',
    padding: '0 8px',
    marginBottom: 4,
    marginTop: 4,
  }}>
    {children}
  </div>
)

const SidebarItem = ({ label, sub, selected, onClick }) => (
  <button
    onClick={onClick}
    style={{
      width: '100%',
      textAlign: 'left',
      padding: '7px 10px',
      border: 'none',
      borderRadius: 'var(--radius-md)',
      background: selected ? 'var(--bg-page)' : 'transparent',
      cursor: 'pointer',
      display: 'block',
      marginBottom: 1,
    }}
  >
    <div style={{
      fontSize: 14,
      color: 'var(--text-primary)',
      fontWeight: selected ? 500 : 400,
      lineHeight: 1.3,
    }}>
      {label}
    </div>
    {sub && (
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>{sub}</div>
    )}
  </button>
)

export default function Sidebar({ restaurants, selectedRestId, onSelect, onNew, pipelineRuns }) {
  return (
    <aside style={{
      width: 220,
      background: 'var(--bg-sidebar)',
      borderRight: '0.5px solid var(--border-default)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0,
      overflowY: 'auto',
      padding: '14px 10px',
    }}>
      <SectionLabel>Restaurants</SectionLabel>

      {restaurants.map(r => (
        <SidebarItem
          key={r.id}
          label={r.name || 'Unnamed restaurant'}
          selected={selectedRestId === r.id}
          onClick={() => onSelect(r.id)}
        />
      ))}

      <button
        onClick={onNew}
        style={{
          width: '100%',
          textAlign: 'left',
          padding: '7px 10px',
          border: 'none',
          borderRadius: 'var(--radius-md)',
          background: selectedRestId === null ? 'var(--bg-page)' : 'transparent',
          cursor: 'pointer',
          fontSize: 14,
          color: 'var(--text-muted)',
          marginBottom: 1,
        }}
      >
        + New restaurant
      </button>

      {selectedRestId && (
        <>
          <div style={{
            borderTop: '0.5px solid var(--border-default)',
            margin: '14px 0 10px',
          }} />
          <SectionLabel>Pipeline Runs</SectionLabel>

          {pipelineRuns && pipelineRuns.length > 0 ? (
            pipelineRuns.map(run => (
              <SidebarItem
                key={run.id}
                label={run.label}
                sub={run.sub}
                selected={run.selected}
              />
            ))
          ) : (
            <div style={{
              padding: '6px 10px',
              fontSize: 13,
              color: 'var(--text-hint)',
            }}>
              No runs yet
            </div>
          )}
        </>
      )}
    </aside>
  )
}
