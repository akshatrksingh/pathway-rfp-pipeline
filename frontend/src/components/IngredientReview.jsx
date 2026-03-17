// Edit status → visual treatment
const STATUS_STYLES = {
  unchanged: {
    row: { borderLeft: '3px solid transparent', background: 'transparent' },
    inputs: {},
  },
  edited: {
    row: { borderLeft: '3px solid var(--amber-strong)', background: 'var(--amber-light)' },
    inputs: { background: 'rgba(255,255,255,0.6)' },
  },
  added: {
    row: { borderLeft: '3px solid var(--green-strong)', background: 'var(--green-light)' },
    inputs: { background: 'rgba(255,255,255,0.6)' },
  },
  deleted: {
    row: { borderLeft: '3px solid transparent', background: 'transparent', opacity: 0.4 },
    inputs: {},
  },
}

function IngredientRow({ ing, onUpdate, onDelete, onUndo }) {
  const status = STATUS_STYLES[ing.editStatus] || STATUS_STYLES.unchanged
  const isDeleted = ing.editStatus === 'deleted'

  const fieldInput = (field, placeholder, extra = {}) => (
    <input
      value={ing[field]}
      disabled={isDeleted}
      placeholder={placeholder}
      onChange={e => onUpdate(field, e.target.value)}
      style={{
        width: '100%',
        padding: '5px 8px',
        border: '0.5px solid transparent',
        borderRadius: 'var(--radius-sm)',
        fontSize: 13,
        color: 'var(--text-primary)',
        background: 'transparent',
        boxSizing: 'border-box',
        outline: 'none',
        textDecoration: isDeleted ? 'line-through' : 'none',
        transition: 'border-color 0.1s, background 0.1s',
        ...status.inputs,
        ...extra,
      }}
      onFocus={e => { e.target.style.borderColor = 'var(--border-default)'; e.target.style.background = '#fff' }}
      onBlur={e => { e.target.style.borderColor = 'transparent'; e.target.style.background = status.inputs.background || 'transparent' }}
    />
  )

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 90px 80px 1fr 36px',
      gap: 6,
      padding: '7px 20px',
      alignItems: 'center',
      transition: 'all 0.15s',
      ...status.row,
    }}>
      {fieldInput('name', 'Ingredient name')}
      {fieldInput('quantity', '—', { textAlign: 'right' })}
      {fieldInput('unit', 'unit')}
      {fieldInput('notes', 'notes')}

      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        {isDeleted ? (
          <button
            onClick={onUndo}
            style={{
              fontSize: 11,
              color: 'var(--text-secondary)',
              background: 'none',
              border: 'none',
              textDecoration: 'underline',
              padding: 0,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            Undo
          </button>
        ) : (
          <button
            onClick={onDelete}
            style={{
              fontSize: 18,
              lineHeight: 1,
              color: 'var(--text-hint)',
              background: 'none',
              border: 'none',
              padding: '0 4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Remove ingredient"
          >
            ×
          </button>
        )}
      </div>
    </div>
  )
}

function DishCard({ dish, onToggle, onUpdateIngredient, onDeleteIngredient, onUndoDelete, onAddIngredient }) {
  const activeCount = dish.ingredients.filter(i => i.editStatus !== 'deleted').length
  const hasEdits = dish.ingredients.some(i => i.editStatus !== 'unchanged')

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '0.5px solid var(--border-default)',
      borderRadius: 'var(--radius-lg)',
      marginBottom: 10,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <button
        onClick={onToggle}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '15px 20px',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          gap: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <span style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 16,
            fontWeight: 500,
            color: 'var(--text-primary)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {dish.name}
          </span>
          {dish.category && (
            <span style={{
              fontSize: 11,
              padding: '3px 10px',
              background: 'var(--bg-tag)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-secondary)',
              flexShrink: 0,
            }}>
              {dish.category}
            </span>
          )}
          {hasEdits && (
            <span style={{
              fontSize: 10,
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: 'var(--amber-strong)',
              flexShrink: 0,
              display: 'inline-block',
            }} />
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          <span style={{ fontSize: 12, color: 'var(--text-hint)' }}>
            {activeCount} ingredient{activeCount !== 1 ? 's' : ''}
          </span>
          {/* Chevron */}
          <svg
            width="12" height="12" viewBox="0 0 12 12" fill="none"
            style={{
              transform: dish.isExpanded ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.15s',
              color: 'var(--text-hint)',
            }}
          >
            <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </button>

      {/* Expanded content */}
      {dish.isExpanded && (
        <div style={{ borderTop: '0.5px solid var(--border-light)' }}>
          {/* Column headers */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 90px 80px 1fr 36px',
            gap: 6,
            padding: '7px 20px 5px',
            borderBottom: '0.5px solid var(--border-light)',
          }}>
            {['Ingredient', 'Qty / month', 'Unit', 'Notes', ''].map((h, i) => (
              <span key={i} style={{
                fontSize: 11,
                color: 'var(--text-hint)',
                textTransform: 'uppercase',
                letterSpacing: '0.3px',
              }}>
                {h}
              </span>
            ))}
          </div>

          {dish.ingredients.map(ing => (
            <IngredientRow
              key={ing.id}
              ing={ing}
              onUpdate={(field, value) => onUpdateIngredient(ing.id, field, value)}
              onDelete={() => onDeleteIngredient(ing.id)}
              onUndo={() => onUndoDelete(ing.id)}
            />
          ))}

          {/* Add ingredient */}
          <div style={{ padding: '10px 20px 14px', borderTop: '0.5px solid var(--border-light)' }}>
            <button
              onClick={onAddIngredient}
              style={{
                fontSize: 13,
                color: 'var(--green-strong)',
                background: 'none',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
              }}
            >
              + Add ingredient
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function IngredientReview({ dishes, setDishes, onConfirm }) {
  function toggleDish(dishId) {
    setDishes(prev => prev.map(d =>
      d.id === dishId ? { ...d, isExpanded: !d.isExpanded } : d
    ))
  }

  function updateIngredient(dishId, ingId, field, value) {
    setDishes(prev => prev.map(d => {
      if (d.id !== dishId) return d
      return {
        ...d,
        ingredients: d.ingredients.map(ing => {
          if (ing.id !== ingId) return ing
          const nextStatus = ing.editStatus === 'added' ? 'added' : 'edited'
          return { ...ing, [field]: value, editStatus: nextStatus }
        }),
      }
    }))
  }

  function deleteIngredient(dishId, ingId) {
    setDishes(prev => prev.map(d => {
      if (d.id !== dishId) return d
      return {
        ...d,
        ingredients: d.ingredients.map(ing =>
          ing.id === ingId ? { ...ing, editStatus: 'deleted' } : ing
        ),
      }
    }))
  }

  function undoDelete(dishId, ingId) {
    setDishes(prev => prev.map(d => {
      if (d.id !== dishId) return d
      return {
        ...d,
        ingredients: d.ingredients.map(ing => {
          if (ing.id !== ingId) return ing
          return { ...ing, ...ing.original, editStatus: 'unchanged' }
        }),
      }
    }))
  }

  function addIngredient(dishId) {
    const newIng = {
      id: `new-${Date.now()}`,
      name: '',
      quantity: '',
      unit: '',
      notes: '',
      editStatus: 'added',
      original: { name: '', quantity: '', unit: '', notes: '' },
    }
    setDishes(prev => prev.map(d =>
      d.id === dishId ? { ...d, ingredients: [...d.ingredients, newIng] } : d
    ))
  }

  const allIngredients = dishes.flatMap(d => d.ingredients)
  const activeCount = allIngredients.filter(i => i.editStatus !== 'deleted').length
  const editedCount = allIngredients.filter(i => i.editStatus === 'edited').length
  const addedCount = allIngredients.filter(i => i.editStatus === 'added').length
  const deletedCount = allIngredients.filter(i => i.editStatus === 'deleted').length

  return (
    <div style={{ maxWidth: 720 }}>
      {/* Header row */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 24,
        gap: 16,
      }}>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--text-primary)',
            marginBottom: 6,
            letterSpacing: '-0.3px',
          }}>
            Review ingredients
          </h1>
          <p style={{ fontSize: 14, color: 'var(--text-muted)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span>{dishes.length} dishes · {activeCount} ingredients</span>
            {editedCount > 0 && (
              <span style={{ color: 'var(--amber-text)' }}>· {editedCount} edited</span>
            )}
            {addedCount > 0 && (
              <span style={{ color: 'var(--green-text)' }}>· {addedCount} added</span>
            )}
            {deletedCount > 0 && (
              <span>· {deletedCount} removed</span>
            )}
          </p>
        </div>

        <button
          onClick={onConfirm}
          style={{
            background: 'var(--green-strong)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: 'var(--radius-pill)',
            padding: '10px 24px',
            fontSize: 14,
            fontWeight: 500,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          Confirm & run pipeline
        </button>
      </div>

      {/* Expand / collapse all */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
        <button
          onClick={() => setDishes(prev => prev.map(d => ({ ...d, isExpanded: true })))}
          style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline' }}
        >
          Expand all
        </button>
        <button
          onClick={() => setDishes(prev => prev.map(d => ({ ...d, isExpanded: false })))}
          style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline' }}
        >
          Collapse all
        </button>
      </div>

      {/* Dish cards */}
      {dishes.map(dish => (
        <DishCard
          key={dish.id}
          dish={dish}
          onToggle={() => toggleDish(dish.id)}
          onUpdateIngredient={(ingId, field, value) => updateIngredient(dish.id, ingId, field, value)}
          onDeleteIngredient={(ingId) => deleteIngredient(dish.id, ingId)}
          onUndoDelete={(ingId) => undoDelete(dish.id, ingId)}
          onAddIngredient={() => addIngredient(dish.id)}
        />
      ))}

      {/* Bottom CTA */}
      <div style={{ paddingTop: 12, paddingBottom: 32 }}>
        <button
          onClick={onConfirm}
          style={{
            background: 'var(--green-strong)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: 'var(--radius-pill)',
            padding: '11px 32px',
            fontSize: 14,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          Confirm & run pipeline
        </button>
        <span style={{ fontSize: 13, color: 'var(--text-hint)', marginLeft: 14 }}>
          Nothing is saved until you confirm.
        </span>
      </div>
    </div>
  )
}
