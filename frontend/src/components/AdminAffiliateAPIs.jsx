import { useEffect, useState } from 'react'
import {
  adminListAffiliateAPIConnections,
  adminCreateAffiliateAPIConnection,
  adminUpdateAffiliateAPIConnection,
  adminDeleteAffiliateAPIConnection,
} from '../api/client'

// Common credential fields per platform. If a platform's actual required
// fields differ from these by the time you sign up, just use "Custom" below
// and label the fields yourself — nothing here is hardcoded into any live
// integration yet, it's storage only.
const PLATFORM_FIELDS = {
  amazon: {
    label: 'Amazon Associates / PA-API',
    fields: [
      { key: 'access_key', label: 'Access Key' },
      { key: 'secret_key', label: 'Secret Key' },
      { key: 'partner_tag', label: 'Partner Tag' },
      { key: 'marketplace', label: 'Marketplace (e.g. webservices.amazon.com)' },
    ],
  },
  ebay: {
    label: 'eBay Partner Network',
    fields: [
      { key: 'app_id', label: 'App ID (Client ID)' },
      { key: 'cert_id', label: 'Cert ID (Client Secret)' },
      { key: 'dev_id', label: 'Dev ID' },
    ],
  },
  etsy: {
    label: 'Etsy Affiliate',
    fields: [
      { key: 'api_key', label: 'API Key (Keystring)' },
      { key: 'shared_secret', label: 'Shared Secret' },
    ],
  },
  aliexpress: {
    label: 'AliExpress Affiliate',
    fields: [
      { key: 'app_key', label: 'App Key' },
      { key: 'app_secret', label: 'App Secret' },
      { key: 'tracking_id', label: 'Tracking ID' },
    ],
  },
  custom: {
    label: 'Custom / Other',
    fields: [
      { key: 'field_1', label: 'Field 1' },
      { key: 'field_2', label: 'Field 2' },
      { key: 'field_3', label: 'Field 3' },
    ],
  },
}

const BLANK_FORM = { platform: 'amazon', label: '', credentials: {}, is_active: true, notes: '' }

export default function AdminAffiliateAPIs() {
  const [adminKey, setAdminKey] = useState('')
  const [keyInput, setKeyInput] = useState('')
  const [connections, setConnections] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(BLANK_FORM)
  const [editingId, setEditingId] = useState(null)

  async function loadConnections(key) {
    try {
      setError(null)
      const data = await adminListAffiliateAPIConnections(key)
      setConnections(data)
    } catch {
      setError('Could not load connections — check your admin key.')
      setConnections([])
    }
  }

  useEffect(() => {
    if (adminKey) loadConnections(adminKey)
  }, [adminKey])

  function handleUnlock(e) {
    e.preventDefault()
    setAdminKey(keyInput)
  }

  function handlePlatformChange(platform) {
    setForm({ ...form, platform, credentials: {} })
  }

  function setCredentialField(fieldKey, value) {
    setForm({ ...form, credentials: { ...form.credentials, [fieldKey]: value } })
  }

  function startEdit(c) {
    setEditingId(c.id)
    setForm({ platform: c.platform, label: c.label, credentials: {}, is_active: c.is_active, notes: c.notes || '' })
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }

  function resetForm() {
    setEditingId(null)
    setForm(BLANK_FORM)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    try {
      if (editingId) {
        await adminUpdateAffiliateAPIConnection(adminKey, editingId, form)
      } else {
        await adminCreateAffiliateAPIConnection(adminKey, form)
      }
      resetForm()
      loadConnections(adminKey)
    } catch {
      setError('Save failed — check the fields and your admin key.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this connection?')) return
    await adminDeleteAffiliateAPIConnection(adminKey, id)
    loadConnections(adminKey)
  }

  if (!adminKey) {
    return (
      <div className="admin-gate">
        <form onSubmit={handleUnlock} className="admin-gate-form">
          <h2>Admin — Affiliate API Connections</h2>
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

  const currentFields = PLATFORM_FIELDS[form.platform].fields

  return (
    <div className="admin-creatives">
      <h1>Affiliate API Connections</h1>
      <p className="muted">
        This stores your credentials for each affiliate platform's API, ready for whenever an automatic
        product-pull is built for that platform. Storing a credential here does NOT start pulling products
        automatically yet — each platform needs its own integration built once you're ready (e.g. Amazon
        requires 3 qualifying sales in 180 days before they'll issue API access at all).
      </p>
      {error && <p className="admin-error">{error}</p>}

      <h2>Saved connections</h2>
      <table className="admin-table">
        <thead>
          <tr><th>Platform</th><th>Label</th><th>Notes</th><th>Active</th><th></th></tr>
        </thead>
        <tbody>
          {connections.map((c) => (
            <tr key={c.id}>
              <td>{PLATFORM_FIELDS[c.platform]?.label || c.platform}</td>
              <td>{c.label}</td>
              <td className="muted">{c.notes}</td>
              <td>{c.is_active ? 'Yes' : 'No'}</td>
              <td>
                <button className="link-btn" onClick={() => startEdit(c)}>Edit</button>{' '}
                <button className="link-btn" onClick={() => handleDelete(c.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>{editingId ? 'Edit connection' : 'Add a connection'}</h2>
      <form onSubmit={handleSubmit} className="admin-form">
        <label>
          Platform
          <select value={form.platform} onChange={(e) => handlePlatformChange(e.target.value)}>
            {Object.entries(PLATFORM_FIELDS).map(([key, p]) => (
              <option key={key} value={key}>{p.label}</option>
            ))}
          </select>
        </label>

        <label>
          Label (just for your reference)
          <input value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} required />
        </label>

        {currentFields.map((f) => (
          <label key={f.key}>
            {f.label}
            <input
              type="password"
              value={form.credentials[f.key] || ''}
              onChange={(e) => setCredentialField(f.key, e.target.value)}
              placeholder={editingId ? 'Leave blank to keep existing value' : ''}
            />
          </label>
        ))}

        <label>
          Notes (optional — e.g. eligibility status)
          <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </label>

        <label className="checkbox-label">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Active
        </label>

        <div className="admin-form-actions">
          <button type="submit">{editingId ? 'Save changes' : 'Add connection'}</button>
          {editingId && <button type="button" onClick={resetForm}>Cancel edit</button>}
        </div>
      </form>
    </div>
  )
}
