import { useEffect, useState } from 'react'
import {
  adminListAIProviders,
  adminCreateAIProvider,
  adminUpdateAIProvider,
  adminDeleteAIProvider,
  adminTestAIProvider,
  adminTestClaudeFallback,
} from '../api/client'

const PROVIDER_PRESETS = {
  openai: { label: 'OpenAI / ChatGPT', base_url: 'https://api.openai.com/v1', model_hint: 'e.g. gpt-4o-mini' },
  xai_grok: { label: 'Grok (xAI)', base_url: 'https://api.x.ai/v1', model_hint: 'e.g. grok-2-latest' },
  openrouter: { label: 'OpenRouter', base_url: 'https://openrouter.ai/api/v1', model_hint: 'e.g. openai/gpt-4o or anthropic/claude-3.5-sonnet' },
  custom: { label: 'Custom / Manual', base_url: '', model_hint: 'Any OpenAI-compatible endpoint + model name' },
}

const BLANK_FORM = {
  name: '',
  provider_type: 'openai',
  api_base_url: PROVIDER_PRESETS.openai.base_url,
  api_key: '',
  model_name: '',
  priority: 0,
  is_active: true,
}

export default function AdminAIProviders() {
  const [adminKey, setAdminKey] = useState('')
  const [keyInput, setKeyInput] = useState('')
  const [providers, setProviders] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(BLANK_FORM)
  const [editingId, setEditingId] = useState(null)
  const [testResults, setTestResults] = useState({}) // id -> {success, response/error}
  const [testingClaude, setTestingClaude] = useState(false)
  const [claudeResult, setClaudeResult] = useState(null)

  async function loadProviders(key) {
    try {
      setError(null)
      const data = await adminListAIProviders(key)
      setProviders(data)
    } catch {
      setError('Could not load providers — check your admin key.')
      setProviders([])
    }
  }

  useEffect(() => {
    if (adminKey) loadProviders(adminKey)
  }, [adminKey])

  function handleUnlock(e) {
    e.preventDefault()
    setAdminKey(keyInput)
  }

  function handleTypeChange(type) {
    setForm({
      ...form,
      provider_type: type,
      api_base_url: PROVIDER_PRESETS[type].base_url,
    })
  }

  function startEdit(p) {
    setEditingId(p.id)
    setForm({
      name: p.name,
      provider_type: p.provider_type,
      api_base_url: p.api_base_url,
      api_key: '', // key is masked in the list — re-enter to change it
      model_name: p.model_name,
      priority: p.priority,
      is_active: p.is_active,
    })
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }

  function resetForm() {
    setEditingId(null)
    setForm(BLANK_FORM)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    try {
      const payload = { ...form, priority: Number(form.priority) }
      if (editingId) {
        await adminUpdateAIProvider(adminKey, editingId, payload)
      } else {
        await adminCreateAIProvider(adminKey, payload)
      }
      resetForm()
      loadProviders(adminKey)
    } catch {
      setError('Save failed — check the fields and your admin key.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this provider?')) return
    await adminDeleteAIProvider(adminKey, id)
    loadProviders(adminKey)
  }

  async function toggleActive(p) {
    await adminUpdateAIProvider(adminKey, p.id, { ...p, api_key: undefined, is_active: !p.is_active })
    loadProviders(adminKey)
  }

  async function runTest(id) {
    setTestResults((prev) => ({ ...prev, [id]: { loading: true } }))
    try {
      const result = await adminTestAIProvider(adminKey, id)
      setTestResults((prev) => ({ ...prev, [id]: result }))
    } catch (e) {
      setTestResults((prev) => ({ ...prev, [id]: { success: false, error: e.message } }))
    }
  }

  async function runClaudeTest() {
    setTestingClaude(true)
    setClaudeResult(null)
    try {
      const result = await adminTestClaudeFallback(adminKey)
      setClaudeResult(result)
    } catch (e) {
      setClaudeResult({ success: false, error: e.message })
    } finally {
      setTestingClaude(false)
    }
  }

  if (!adminKey) {
    return (
      <div className="admin-gate">
        <form onSubmit={handleUnlock} className="admin-gate-form">
          <h2>Admin — AI Providers</h2>
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
      <h1>AI Providers — Failover Order</h1>
      <p className="muted">
        Providers below are tried in priority order (highest first). If every one fails or none are
        configured, Claude is used automatically as a guaranteed last resort — that one isn't listed
        here since it can't be edited or removed, on purpose.
      </p>
      {error && <p className="admin-error">{error}</p>}

      <h2>Configured providers</h2>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Priority</th><th>Name</th><th>Type</th><th>Model</th>
            <th>Active</th><th>Test</th><th></th>
          </tr>
        </thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.id}>
              <td>{p.priority}</td>
              <td>{p.name}</td>
              <td>{PROVIDER_PRESETS[p.provider_type]?.label || p.provider_type}</td>
              <td>{p.model_name}</td>
              <td>
                <button className="link-btn" onClick={() => toggleActive(p)}>
                  {p.is_active ? 'Yes' : 'No'}
                </button>
              </td>
              <td>
                <button className="link-btn" onClick={() => runTest(p.id)}>
                  {testResults[p.id]?.loading ? 'Testing...' : 'Test'}
                </button>
                {testResults[p.id] && !testResults[p.id].loading && (
                  <div className={testResults[p.id].success ? 'test-ok' : 'test-fail'}>
                    {testResults[p.id].success
                      ? `OK: ${testResults[p.id].response}`
                      : `Failed: ${testResults[p.id].error}`}
                  </div>
                )}
              </td>
              <td>
                <button className="link-btn" onClick={() => startEdit(p)}>Edit</button>{' '}
                <button className="link-btn" onClick={() => handleDelete(p.id)}>Delete</button>
              </td>
            </tr>
          ))}
          <tr className="claude-fallback-row">
            <td>—</td>
            <td>Claude (hardcoded fallback)</td>
            <td>Anthropic</td>
            <td>Set via ANTHROPIC_API_KEY / CLAUDE_FALLBACK_MODEL</td>
            <td>Always on</td>
            <td>
              <button className="link-btn" onClick={runClaudeTest}>
                {testingClaude ? 'Testing...' : 'Test'}
              </button>
              {claudeResult && (
                <div className={claudeResult.success ? 'test-ok' : 'test-fail'}>
                  {claudeResult.success ? `OK: ${claudeResult.response}` : `Failed: ${claudeResult.error}`}
                </div>
              )}
            </td>
            <td className="muted">Not editable here</td>
          </tr>
        </tbody>
      </table>

      <h2>{editingId ? 'Edit provider' : 'Add a new provider'}</h2>
      <form onSubmit={handleSubmit} className="admin-form">
        <label>
          Name (just for your reference)
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </label>

        <label>
          Type
          <select value={form.provider_type} onChange={(e) => handleTypeChange(e.target.value)}>
            {Object.entries(PROVIDER_PRESETS).map(([key, p]) => (
              <option key={key} value={key}>{p.label}</option>
            ))}
          </select>
        </label>

        <label>
          API base URL
          <input value={form.api_base_url} onChange={(e) => setForm({ ...form, api_base_url: e.target.value })} required />
        </label>

        <label>
          API key {editingId && <span className="muted">(leave blank to keep the current one)</span>}
          <input
            type="password"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            required={!editingId}
          />
        </label>

        <label>
          Model name
          <input
            value={form.model_name}
            onChange={(e) => setForm({ ...form, model_name: e.target.value })}
            placeholder={PROVIDER_PRESETS[form.provider_type].model_hint}
            required
          />
        </label>

        <label>
          Priority (higher tries first)
          <input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
        </label>

        <label className="checkbox-label">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Active
        </label>

        <div className="admin-form-actions">
          <button type="submit">{editingId ? 'Save changes' : 'Add provider'}</button>
          {editingId && <button type="button" onClick={resetForm}>Cancel edit</button>}
        </div>
      </form>
    </div>
  )
}
