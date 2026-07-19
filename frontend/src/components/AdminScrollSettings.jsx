import { useEffect, useState } from 'react'
import { getSiteSetting, adminSetSiteSetting } from '../api/client'

const DEFAULT_CONFIG = { enabled: true, direction: 'left', speed_seconds: 40 }

const ROWS = [
  { key: 'ticker_scroll_config', label: 'Top Price Ticker', defaultSpeed: 40 },
  { key: 'product_carousel_scroll_config', label: 'Product Carousel', defaultSpeed: 45 },
]

export default function AdminScrollSettings() {
  const [adminKey, setAdminKey] = useState('')
  const [keyInput, setKeyInput] = useState('')
  const [configs, setConfigs] = useState({})
  const [saved, setSaved] = useState({})
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!adminKey) return
    ROWS.forEach((row) => {
      getSiteSetting(row.key).then((raw) => {
        let parsed = { ...DEFAULT_CONFIG, speed_seconds: row.defaultSpeed }
        if (raw) {
          try { parsed = { ...parsed, ...JSON.parse(raw) } } catch { /* use defaults */ }
        }
        setConfigs((prev) => ({ ...prev, [row.key]: parsed }))
      })
    })
  }, [adminKey])

  function handleUnlock(e) {
    e.preventDefault()
    setAdminKey(keyInput)
  }

  function updateField(rowKey, field, value) {
    setConfigs((prev) => ({ ...prev, [rowKey]: { ...prev[rowKey], [field]: value } }))
  }

  async function handleSave(rowKey) {
    try {
      setError(null)
      await adminSetSiteSetting(adminKey, rowKey, JSON.stringify(configs[rowKey]))
      setSaved((prev) => ({ ...prev, [rowKey]: true }))
      setTimeout(() => setSaved((prev) => ({ ...prev, [rowKey]: false })), 2000)
    } catch {
      setError('Save failed — check your admin key.')
    }
  }

  if (!adminKey) {
    return (
      <div className="admin-gate">
        <form onSubmit={handleUnlock} className="admin-gate-form">
          <h2>Admin — Scroll Settings</h2>
          <p className="muted">Enter your admin key to continue.</p>
          <input
            type="password"
            placeholder="Admin key"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
          />
          <button type="submit">Unlock</button>
        </form>
      </div>
    )
  }

  return (
    <div className="admin-creatives">
      <h1>Scroll Settings</h1>
      <p className="muted">
        Controls how fast (or whether) each scrolling row moves. Lower seconds = faster.
        Changes apply live — no rebuild needed, just refresh the dashboard.
      </p>
      {error && <p className="admin-error">{error}</p>}

      {ROWS.map((row) => {
        const cfg = configs[row.key]
        if (!cfg) return <p key={row.key} className="muted">Loading {row.label}...</p>
        return (
          <div key={row.key} className="scroll-settings-card">
            <h2>{row.label}</h2>
            <form
              className="admin-form"
              onSubmit={(e) => { e.preventDefault(); handleSave(row.key) }}
            >
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={cfg.enabled}
                  onChange={(e) => updateField(row.key, 'enabled', e.target.checked)}
                />
                Moving (uncheck to keep it still)
              </label>

              <label>
                Direction
                <select
                  value={cfg.direction}
                  onChange={(e) => updateField(row.key, 'direction', e.target.value)}
                  disabled={!cfg.enabled}
                >
                  <option value="left">Left</option>
                  <option value="right">Right</option>
                </select>
              </label>

              <label>
                Speed — seconds for one full loop (lower = faster)
                <input
                  type="number"
                  min="5"
                  max="300"
                  value={cfg.speed_seconds}
                  onChange={(e) => updateField(row.key, 'speed_seconds', Number(e.target.value))}
                  disabled={!cfg.enabled}
                />
              </label>

              <div className="admin-form-actions">
                <button type="submit">{saved[row.key] ? 'Saved ✓' : 'Save'}</button>
              </div>
            </form>
          </div>
        )
      })}
    </div>
  )
}
