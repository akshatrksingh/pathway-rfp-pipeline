import { useState } from 'react'

function ServingsInput({ value, onChange }) {
  const [focused, setFocused] = useState(false)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <input
        type="number"
        min="1"
        value={value}
        onChange={e => onChange(Math.max(1, parseInt(e.target.value) || 1))}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          width: 64,
          padding: '6px 10px',
          border: `0.5px solid ${focused ? 'var(--text-muted)' : 'var(--border-default)'}`,
          borderRadius: 'var(--radius-md)',
          fontSize: 15,
          fontWeight: 500,
          color: 'var(--text-primary)',
          background: '#fff',
          textAlign: 'center',
          outline: 'none',
          transition: 'border-color 0.1s',
        }}
      />
      <span style={{ fontSize: 13, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
        servings / day
      </span>
    </div>
  )
}

function DishRow({ dish, servings, onServingsChange }) {
  const monthlyOrders = servings * 30

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '0.5px solid var(--border-default)',
      borderRadius: 'var(--radius-lg)',
      padding: '14px 20px',
      marginBottom: 8,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
    }}>
      {/* Left: name + category */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 15,
            fontWeight: 500,
            color: 'var(--text-primary)',
          }}>
            {dish.name}
          </span>
          {dish.category && (
            <span style={{
              fontSize: 11,
              padding: '2px 9px',
              background: 'var(--bg-tag)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              flexShrink: 0,
            }}>
              {dish.category}
            </span>
          )}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-hint)', marginTop: 3 }}>
          {dish.ingredients.length} ingredient{dish.ingredients.length !== 1 ? 's' : ''}
          {' · '}
          <span style={{ color: 'var(--text-muted)' }}>
            {monthlyOrders.toLocaleString()} orders / month
          </span>
        </div>
      </div>

      {/* Right: servings input */}
      <ServingsInput value={servings} onChange={onServingsChange} />
    </div>
  )
}

export default function DishServings({ dishes, onCalculate }) {
  // servingsMap: { [dish index]: servings_per_day }
  const [servingsMap, setServingsMap] = useState(() =>
    Object.fromEntries(dishes.map((d, i) => [i, d.servings_per_day || 10]))
  )

  function setServings(i, val) {
    setServingsMap(prev => ({ ...prev, [i]: val }))
  }

  function handleCalculate() {
    const dishesWithServings = dishes.map((d, i) => ({
      ...d,
      servings_per_day: servingsMap[i],
    }))
    onCalculate(dishesWithServings)
  }

  const totalMonthlyOrders = Object.values(servingsMap).reduce((s, v) => s + v * 30, 0)

  return (
    <div style={{ maxWidth: 680 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 20,
        gap: 16,
      }}>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--text-primary)',
            marginBottom: 5,
            letterSpacing: '-0.3px',
          }}>
            Review dishes
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
            {dishes.length} dishes · {totalMonthlyOrders.toLocaleString()} total orders / month
          </p>
        </div>

        <button
          onClick={handleCalculate}
          style={{
            background: 'var(--green-strong)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-pill)',
            padding: '10px 22px',
            fontSize: 14,
            fontWeight: 500,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 7,
          }}
        >
          Calculate ingredients
          {/* Arrow */}
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <path d="M2.5 6.5h8M7 3l3.5 3.5L7 10" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {/* Info banner */}
      <div style={{
        background: 'var(--amber-light)',
        border: '0.5px solid var(--amber-strong)',
        borderRadius: 'var(--radius-md)',
        padding: '11px 16px',
        marginBottom: 20,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
      }}>
        {/* Info icon */}
        <svg width="15" height="15" viewBox="0 0 15 15" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
          <circle cx="7.5" cy="7.5" r="6.5" stroke="var(--amber-strong)" strokeWidth="1"/>
          <path d="M7.5 6.5v4M7.5 5v-.5" stroke="var(--amber-strong)" strokeWidth="1.2" strokeLinecap="round"/>
        </svg>
        <div>
          <span style={{ fontSize: 13, color: 'var(--amber-text)', fontWeight: 500 }}>
            Estimated daily servings per dish.
          </span>
          <span style={{ fontSize: 13, color: 'var(--amber-text)' }}>
            {' '}Adjust to match your restaurant's volume. Ingredient quantities will be calculated as{' '}
            <em>servings/day × 30 days</em>.
          </span>
        </div>
      </div>

      {/* Column header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 12,
        padding: '0 20px 8px',
      }}>
        <span style={{ fontSize: 11, color: 'var(--text-hint)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
          Dish
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-hint)', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
          Volume
        </span>
      </div>

      {/* Dish rows */}
      {dishes.map((dish, i) => (
        <DishRow
          key={i}
          dish={dish}
          servings={servingsMap[i]}
          onServingsChange={val => setServings(i, val)}
        />
      ))}

      {/* Bottom CTA */}
      <div style={{ paddingTop: 12, paddingBottom: 32 }}>
        <button
          onClick={handleCalculate}
          style={{
            background: 'var(--green-strong)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-pill)',
            padding: '11px 32px',
            fontSize: 14,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          Calculate ingredients
        </button>
        <span style={{ fontSize: 13, color: 'var(--text-hint)', marginLeft: 14 }}>
          You can adjust individual quantities in the next step.
        </span>
      </div>
    </div>
  )
}
