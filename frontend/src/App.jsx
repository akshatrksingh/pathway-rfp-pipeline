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

/**
 * After the user confirms servings/day, multiply per-serving quantities by
 * servings_per_day × 30 to get monthly bulk quantities for ingredient review.
 */
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
      // Round to 1 decimal; show whole numbers when ≥ 10
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

  // New restaurant form
  const [restForm, setRestForm] = useState({ name: '', address: '', city: '', state: '' })

  // Parse state
  const [isParsing, setIsParsing] = useState(false)
  const [parseError, setParseError] = useState(null)

  // Raw parsed dishes from API (with servings_per_day + quantity_per_serving)
  const [parsedDishes, setParsedDishes] = useState([])

  // Editable dishes for IngredientReview (monthly quantities calculated)
  const [editableDishes, setEditableDishes] = useState([])

  const selectedRestaurant = restaurants.find(r => r.id === selectedRestId) || null
  const titleName = selectedRestaurant?.name || (restForm.name.trim() || null)

  function handleSelectRestaurant(id) {
    setSelectedRestId(id)
    setRestForm({ name: '', address: '', city: '', state: '' })
    setParsedDishes([])
    setEditableDishes([])
    setParseError(null)
    setView('upload')
  }

  function handleNewRestaurant() {
    setSelectedRestId(null)
    setRestForm({ name: '', address: '', city: '', state: '' })
    setParsedDishes([])
    setEditableDishes([])
    setParseError(null)
    setView('upload')
  }

  async function handleParse({ file, url }) {
    setIsParsing(true)
    setParseError(null)

    try {
      const formData = new FormData()
      if (file) formData.append('file', file)
      else formData.append('url', url)

      const resp = await fetch('/api/menus/parse', { method: 'POST', body: formData })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `Server error ${resp.status}`)
      }

      const data = await resp.json()

      // Register new restaurant locally if needed
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

  function handleConfirm() {
    // TODO: persist to backend in next step
    setView('pipeline')
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
            <DishServings
              dishes={parsedDishes}
              onCalculate={handleCalculate}
            />
          )}

          {view === 'review' && (
            <IngredientReview
              dishes={editableDishes}
              setDishes={setEditableDishes}
              onConfirm={handleConfirm}
            />
          )}

          {view === 'pipeline' && (
            <div style={{ paddingTop: 60, textAlign: 'center' }}>
              <div style={{
                fontFamily: 'var(--font-serif)',
                fontSize: 20,
                color: 'var(--text-primary)',
                marginBottom: 8,
              }}>
                Ingredients confirmed.
              </div>
              <p style={{ fontSize: 14, color: 'var(--text-muted)' }}>
                Pipeline steps (pricing, distributors, emails) coming in the next build.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
