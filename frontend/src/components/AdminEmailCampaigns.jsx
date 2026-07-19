import { useEffect, useState } from 'react'
import {
  adminListTemplates,
  adminCreateTemplate,
  adminDeleteTemplate,
  adminPreviewAudience,
  adminSendCampaign,
  adminListCampaigns,
} from '../api/client'

const AGE_OPTIONS = ['', '18-24', '25-34', '35-44', '45-54', '55+']
const GENDER_OPTIONS = ['', 'male', 'female']
const PET_OPTIONS = ['', 'cat', 'dog', 'horse', 'bird']
const COLOR_OPTIONS = ['', 'red', 'orange', 'green', 'blue', 'purple', 'black']
const INTEREST_OPTIONS = ['books', 'food', 'tech', 'news']
const ASSET_OPTIONS = ['stock', 'crypto', 'commodity', 'forex']

const BLANK_FILTERS = { gender: '', age_range: '', favorite_color: '', favorite_pet: '', interests: [], asset_preferences: [] }

export default function AdminEmailCampaigns() {
  const [adminKey, setAdminKey] = useState('')
  const [keyInput, setKeyInput] = useState('')
  const [templates, setTemplates] = useState([])
  const [campaigns, setCampaigns] = useState([])
  const [error, setError] = useState(null)

  const [filters, setFilters] = useState(BLANK_FILTERS)
  const [preview, setPreview] = useState(null)
  const [previewing, setPreviewing] = useState(false)

  const [campaignName, setCampaignName] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyHtml, setBodyHtml] = useState('')
  const [windowHours, setWindowHours] = useState(48)
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState(null)

  async function loadAll(key) {
    try {
      setError(null)
      const [t, c] = await Promise.all([adminListTemplates(key), adminListCampaigns(key)])
      setTemplates(t)
      setCampaigns(c)
    } catch {
      setError('Could not load data — check your admin key.')
    }
  }

  useEffect(() => {
    if (adminKey) loadAll(adminKey)
  }, [adminKey])

  function handleUnlock(e) {
    e.preventDefault()
    setAdminKey(keyInput)
  }

  function toggleMulti(field, value) {
    const current = filters[field]
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value]
    setFilters({ ...filters, [field]: next })
  }

  async function handlePreview() {
    setPreviewing(true)
    try {
      const result = await adminPreviewAudience(adminKey, filters)
      setPreview(result)
    } catch {
      setError('Preview failed — check your admin key.')
    } finally {
      setPreviewing(false)
    }
  }

  function loadTemplate(t) {
    setSubject(t.subject)
    setBodyHtml(t.body_html)
    setCampaignName(t.name)
  }

  async function saveAsTemplate() {
    const name = prompt('Template name?')
    if (!name) return
    await adminCreateTemplate(adminKey, { name, category: 'custom', subject, body_html: bodyHtml })
    loadAll(adminKey)
  }

  async function handleQueueCampaign() {
    if (!subject || !bodyHtml || !campaignName) {
      setError('Campaign name, subject, and body are all required.')
      return
    }
    setSending(true)
    setSendResult(null)
    try {
      const result = await adminSendCampaign(adminKey, {
        name: campaignName, subject, body_html: bodyHtml, filters, window_hours: Number(windowHours),
      })
      setSendResult(result)
      loadAll(adminKey)
    } catch (e) {
      setError('Queueing failed — check your admin key and fields.')
    } finally {
      setSending(false)
    }
  }

  if (!adminKey) {
    return (
      <div className="admin-gate">
        <form onSubmit={handleUnlock} className="admin-gate-form">
          <h2>Admin — Email Campaigns</h2>
          <p className="muted">Enter your admin key to continue.</p>
          <input type="password" placeholder="Admin key" value={keyInput} onChange={(e) => setKeyInput(e.target.value)} />
          <button type="submit">Unlock</button>
        </form>
      </div>
    )
  }

  return (
    <div className="admin-creatives">
      <h1>Email Campaigns</h1>
      <p className="muted">
        Sends via your own domain's mailbox, queued with randomized timing spread across the window you set below —
        never fired all at once. Every email gets an unsubscribe link automatically, you don't need to add one yourself.
      </p>
      {error && <p className="admin-error">{error}</p>}

      <h2>1. Build your audience</h2>
      <div className="admin-form">
        <label>
          Gender
          <select value={filters.gender} onChange={(e) => setFilters({ ...filters, gender: e.target.value })}>
            {GENDER_OPTIONS.map((v) => <option key={v} value={v}>{v || 'Any'}</option>)}
          </select>
        </label>
        <label>
          Age range
          <select value={filters.age_range} onChange={(e) => setFilters({ ...filters, age_range: e.target.value })}>
            {AGE_OPTIONS.map((v) => <option key={v} value={v}>{v || 'Any'}</option>)}
          </select>
        </label>
        <label>
          Favorite pet
          <select value={filters.favorite_pet} onChange={(e) => setFilters({ ...filters, favorite_pet: e.target.value })}>
            {PET_OPTIONS.map((v) => <option key={v} value={v}>{v || 'Any'}</option>)}
          </select>
        </label>
        <label>
          Favorite color
          <select value={filters.favorite_color} onChange={(e) => setFilters({ ...filters, favorite_color: e.target.value })}>
            {COLOR_OPTIONS.map((v) => <option key={v} value={v}>{v || 'Any'}</option>)}
          </select>
        </label>

        <div className="admin-form-full-width">
          <label className="muted">Interests (any match)</label>
          <div className="filter-chip-row">
            {INTEREST_OPTIONS.map((v) => (
              <button
                type="button"
                key={v}
                className={`filter-chip ${filters.interests.includes(v) ? 'active' : ''}`}
                onClick={() => toggleMulti('interests', v)}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        <div className="admin-form-full-width">
          <label className="muted">Asset preferences (any match)</label>
          <div className="filter-chip-row">
            {ASSET_OPTIONS.map((v) => (
              <button
                type="button"
                key={v}
                className={`filter-chip ${filters.asset_preferences.includes(v) ? 'active' : ''}`}
                onClick={() => toggleMulti('asset_preferences', v)}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        <div className="admin-form-actions">
          <button type="button" onClick={handlePreview}>{previewing ? 'Checking...' : 'Preview audience'}</button>
        </div>
      </div>
      {preview && (
        <p className="muted">
          <strong>{preview.count}</strong> matching {preview.count === 1 ? 'person' : 'people'} (excluding unsubscribes).
        </p>
      )}

      <h2>2. Start from a template (optional)</h2>
      <div className="template-picker-row">
        {templates.map((t) => (
          <button key={t.id} className="link-btn template-pick-btn" onClick={() => loadTemplate(t)}>
            {t.name}
          </button>
        ))}
      </div>

      <h2>3. Write the email</h2>
      <div className="admin-form">
        <label>
          Campaign name (for your own reference)
          <input value={campaignName} onChange={(e) => setCampaignName(e.target.value)} />
        </label>
        <label>
          Spread window (hours)
          <input type="number" min="1" max="168" value={windowHours} onChange={(e) => setWindowHours(e.target.value)} />
        </label>
        <label className="admin-form-full-width">
          Subject line — use {'{{FIRST_NAME}}'} for personalization
          <input value={subject} onChange={(e) => setSubject(e.target.value)} />
        </label>
        <label className="admin-form-full-width">
          Body (HTML) — use {'{{FIRST_NAME}}'} for personalization
          <textarea className="admin-textarea" rows={10} value={bodyHtml} onChange={(e) => setBodyHtml(e.target.value)} />
        </label>
        <div className="admin-form-actions">
          <button type="button" onClick={saveAsTemplate}>Save as template</button>
          <button type="button" onClick={handleQueueCampaign} disabled={sending}>
            {sending ? 'Queueing...' : 'Queue campaign'}
          </button>
        </div>
      </div>
      {sendResult && (
        <p className="muted">
          Queued "{sendResult.name}" for {sendResult.total_recipients} recipients, spread over {windowHours}h.
        </p>
      )}

      <h2>Campaign history</h2>
      <table className="admin-table">
        <thead>
          <tr><th>Name</th><th>Recipients</th><th>Pending</th><th>Sent</th><th>Failed</th><th>Skipped</th></tr>
        </thead>
        <tbody>
          {campaigns.map((c) => (
            <tr key={c.id}>
              <td>{c.name}<div className="muted">{new Date(c.created_at).toLocaleString()}</div></td>
              <td>{c.total_recipients}</td>
              <td>{c.pending}</td>
              <td>{c.sent}</td>
              <td>{c.failed}</td>
              <td>{c.skipped}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
