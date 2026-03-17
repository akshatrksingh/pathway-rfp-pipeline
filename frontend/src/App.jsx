import { useState } from 'react'
import TitleBar from './components/TitleBar'
import Sidebar from './components/Sidebar'
import MenuUpload from './components/MenuUpload'
import DishServings from './components/DishServings'
import IngredientReview from './components/IngredientReview'

const MOCK_RESTAURANTS = [
  { id: 1, name: "Luca's Trattoria", address: '123 Main St', city: 'Brooklyn', state: 'NY' },
  { id: 2, name: "Joe's Pizza", address: '456 Park Ave', city: 'Manhattan', state: 'NY' },
]

function buildEditableDishes(dishesWithServings) {
  return dishesWithServings.map((dish, di) => ({
    id: `d${di}`,
    name: dish.name,
    description: dish.description || null,
    category: dish.category || null,
    isExpanded: di === 0,
    ingredients: dish.ingredients.map((ing, ii) => {
      const servings = dish.servings_per_day || 10
      const raw = ing.quantity_per_serving != null
        ? ing.quantity_per_serving * servings * 30
        : null
      const rounded = raw != null
        ? (raw >= 10 ? Math.round(raw) : Math.round(raw * 10) / 10)
        : null
      const qtyStr = rounded != null ? String(rounded) : ''
      return {
        id: `d${di}i${ii}`,
        name: ing.name,
        quantity: qtyStr,
        unit: ing.unit || '',
        notes: ing.notes || '',
        editStatus: 'unchanged',
        original: { name: ing.name, quantity: qtyStr, unit: ing.unit || '', notes: ing.notes || '' },
      }
    }),
  }))
}

export default function App() {
  const [restaurants, setRestaurants] = useState(MOCK_RESTAURANTS)
  const [selectedRestId, setSelectedRestId] = useState(null)

  // 'upload' | 'servings' | 'review' | 'pipeline'
  const [view, setView] = useState('upload')

  const [restForm, setRestForm] = useState({ name: '', address: '', city: '', state: '' })

  const [isParsing, setIsParsing]       = useState(false)
  const [parseError, setParseError]     = useState(null)
  const [isConfirming, setIsConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState(null)

  const [parsedDishes, setParsedDishes]     = useState([])
  const [editableDishes, setEditableDishes] = useState([])
  const [runId, setRunId]                   = useState(null)

  const selectedRestaurant = restaurants.find(r => r.id === selectedRestId) || null
  const titleName = selectedRestaurant?.name || (restForm.name.trim() || null)

  function handleSelectRestaurant(id) {
    setSelectedRestId(id)
    setRestForm({ name: '', address: '', city: '', state: '' })
    setParsedDishes([])
    setEditableDishes([])
    setParseError(null)
    setConfirmError(null)
    setRunId(null)
    setView('upload')
  }

  function handleNewRestaurant() {
    setSelectedRestId(null)
    setRestForm({ name: '', address: '', city: '', state: '' })
    setParsedDishes([])
    setEditableDishes([])
    setParseError(null)
    setConfirmError(null)
    setRunId(null)
    setView('upload')
  }

  async function handleParse({ file }) {
    setIsParsing(true)
    setParseError(null)

    try {
      const fd = new FormData()
      fd.append('file', file)

      const resp = await fetch('/api/menus/parse', { method: 'POST', body: fd })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || 'Something went wrong. Please try again.')
      }

      const data = await resp.json()

      if (!selectedRestId) {
        const newRest = {
          id: Date.now(),
          name: restForm.name.trim() || 'New restaurant',
          address: restForm.address,
          city: restForm.city,
          state: restForm.state,
        }
        setRestaurants(prev => [...prev, newRest])
        setSelectedRestId(newRest.id)
      }

      setParsedDishes(data.dishes)
      setView('servings')
    } catch (e) {
      setParseError(e.message)
    } finally {
      setIsParsing(false)
    }
  }

  function handleCalculate(dishesWithServings) {
    setEditableDishes(buildEditableDishes(dishesWithServings))
    setView('review')
  }

  async function handleConfirm() {
    setIsConfirming(true)
    setConfirmError(null)

    try {
      const rest = selectedRestaurant || {
        name: restForm.name, address: restForm.address,
        city: restForm.city, state: restForm.state,
      }

      const confirmedDishes = editableDishes
        .map(d => ({
          name: d.name,
          description: d.description || null,
          category: d.category || null,
          ingredients: d.ingredients
            .filter(i => i.editStatus !== 'deleted' && i.name.trim())
            .map(i => ({
              name: i.name.trim(),
              quantity: i.quantity ? parseFloat(i.quantity) : null,
              unit: i.unit || null,
              notes: i.notes || null,
            })),
        }))
        .filter(d => d.ingredients.length > 0)

      const resp = await fetch('/api/pipeline/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          restaurant_name:    rest.name    || '',
          restaurant_address: rest.address || '',
          restaurant_city:    rest.city    || '',
          restaurant_state:   rest.state   || '',
          dishes: confirmedDishes,
        }),
      })

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || 'Failed to save. Please try again.')
      }

      const data = await resp.json()
      setRunId(data.run_id)
      setView('pipeline')
    } catch (e) {
      setConfirmError(e.message)
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TitleBar restaurantName={titleName} />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar
          restaurants={restaurants}
          selectedRestId={selectedRestId}
          onSelect={handleSelectRestaurant}
          onNew={handleNewRestaurant}
          pipelineRuns={[]}
        />

        <main style={{
          flex: 1,
          background: 'var(--bg-page)',
          overflowY: 'auto',
          padding: '32px 36px',
        }}>
          {view === 'upload' && (
            <MenuUpload
              restForm={restForm}
              setRestForm={setRestForm}
              selectedRestaurant={selectedRestaurant}
              isParsing={isParsing}
              parseError={parseError}
              onParse={handleParse}
            />
          )}

          {view === 'servings' && (
            <DishServings dishes={parsedDishes} onCalculate={handleCalculate} />
          )}

          {view === 'review' && (
            <IngredientReview
              dishes={editableDishes}
              setDishes={setEditableDishes}
              onConfirm={handleConfirm}
              isConfirming={isConfirming}
              confirmError={confirmError}
            />
          )}

          {view === 'pipeline' && (
            <div style={{ paddingTop: 60, textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 20, color: 'var(--text-primary)', marginBottom: 8 }}>
                Pipeline started
              </div>
              <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 4 }}>
                Run #{runId} · ingredients confirmed and saved.
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-hint)' }}>
                Pricing, distributor search, and email steps coming next.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
