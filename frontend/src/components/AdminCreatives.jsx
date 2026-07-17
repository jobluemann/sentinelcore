import { useEffect, useState } from 'react'
import {
  adminListCreatives,
  adminCreateCreative,
  adminUpdateCreative,
  adminDeleteCreative,
} from '../api/client'

const ZONES = [
  { key: 'top_carousel', label: 'Top Carousel', defaultSize: 'leaderboard_728x90' },
  { key: 'side_banner', label: 'Side Banner', defaultSize: 'skyscraper_160x600' },
  { key: 'bottom_banner', label: 'Bottom Banner', defaultSize: 'rectangle_300x250' },
]
const SIZES = [
  { key: 'leaderboard_728x90', label: 'Leaderboard 728×90' },
  { key: 'skyscraper_160x600', label: 'Skyscraper 160×600' },
  { key: 'rectangle_300x250', label: 'Rectangle 300×250' },
]
const ASSET_CLASSES = ['', 'stock', 'crypto', 'commodity', 'forex']

const BLANK_FORM = {
  zone: 'top_carousel',
  size_key: 'leaderboard_728x90',
  image_url: '',
  click_url: '',
  product_name: '',
  affiliate_name: '',
  asset_class: '',
  symbol: '',
  behavior: 'static',
  priority: 0,
  is_active: true,
}

export default function AdminCreatives() {
  const [adminKey, setAdminKey] = useState(sessionStorage_getKey())
  const [keyInput, setKeyInput] = useState('')
  const [creatives, setCreatives] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(BLANK_FORM)
  const [editingId, setEditingId] = useState(null)

  function sessionStorage_getKey() {
    // Not persisted across reloads on purpose — admin key is re-entered each session.
    return ''
  }

  async function loadCreatives(key) {
    try {
      setError(null)
      const data = await adminListCreatives(key)
      setCreatives(data)
    } catch (e) {
      setError('Could not load creatives — check your admin key.')
      setCreatives([])
    }
  }

  useEffect(() => {
    if (adminKey) loadCreatives(adminKey)
  }, [adminKey])

  function handleUnlock(e) {
    e.preventDefault()
    setAdminKey(keyInput)
  }

  function startEdit(creative) {
    setEditingId(creative.id)
    setForm({
      zone: creative.zone,
      size_key: creative.size_key,
      image_url: creative.image_url,
      click_url: creative.click_url,
      product_name: creative.product_name,
      affiliate_name: creative.affiliate_name,
      asset_class: creative.asset_class || '',
      symbol: creative.symbol || '',
      behavior: creative.behavior,
      priority: creative.priority,
      is_active: creative.is_active,
    })
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
  }

  function resetForm() {
    setEditingId(null)
    setForm(BLANK_FORM)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const payload = {
      ...form,
      asset_class: form.asset_class || null,
      symbol: form.symbol || null,
      priority: Number(form.priority),
    }
    try {
      if (editingId) {
        await adminUpdateCreative(adminKey, editingId, payload)
      } else {
        await adminCreateCreative(adminKey, payload)
      }
      resetForm()
      loadCreatives(adminKey)
    } catch (e) {
      setError('Save failed — check the fields and your admin key.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Delete this creative?')) return
    await adminDeleteCreative(adminKey, id)
    loadCreatives(adminKey)
  }

  async function toggleActive(creative) {
    await adminUpdateCreative(adminKey, creative.id, { ...creative, is_active: !creative.is_active })
    loadCreatives(adminKey)
  }

  if (!adminKey) {
    return (
      <div className="admin-gate">
        <form onSubmit={handleUnlock} className="admin-gate-form">
          <h2>Admin — Affiliate Creatives</h2>
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

  const byZone = (zoneKey) => creatives.filter((c) => c.zone === zoneKey)

  return (
    <div className="admin-creatives">
      <h1>Affiliate Creatives — Layout &amp; Management</h1>
      <p className="muted">
        This is a scaled-down map of where each placement type sits on the live site. Use it to decide
        product placement before publishing. Sizes shown are proportional, not literal pixels.
      </p>
      {error && <p className="admin-error">{error}</p>}

      {/* ---------- VISUAL LAYOUT PREVIEW ---------- */}
      <div className="site-map">
        <div className="site-map-header">Header / Sign-in bar</div>

        <div className="site-map-zone site-map-carousel">
          <span className="zone-label">Top Carousel — 728×90 (rotates through active slides)</span>
          <div className="zone-thumbs">
            {byZone('top_carousel').length === 0 && <span className="zone-empty">No creatives yet</span>}
            {byZone('top_carousel').map((c) => (
              <img key={c.id} src={c.image_url} alt={c.product_name} className="zone-thumb-wide" />
            ))}
          </div>
        </div>

        <div className="site-map-body">
          <div className="site-map-grid">Asset cards grid (dashboard content)</div>
          <div className="site-map-zone site-map-side">
            <span className="zone-label">Side Banner — 160×600</span>
            <div className="zone-thumbs">
              {byZone('side_banner').length === 0 && <span className="zone-empty">No creatives yet</span>}
              {byZone('side_banner').map((c) => (
                <img key={c.id} src={c.image_url} alt={c.product_name} className="zone-thumb-tall" />
              ))}
            </div>
          </div>
        </div>

        <div className="site-map-zone site-map-bottom">
          <span className="zone-label">Bottom Banner — 300×250</span>
          <div className="zone-thumbs">
            {byZone('bottom_banner').length === 0 && <span className="zone-empty">No creatives yet</span>}
            {byZone('bottom_banner').map((c) => (
              <img key={c.id} src={c.image_url} alt={c.product_name} className="zone-thumb-square" />
            ))}
          </div>
        </div>
      </div>

      {/* ---------- LIST / MANAGE ---------- */}
      <h2>All creatives</h2>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Preview</th><th>Product</th><th>Zone</th><th>Scope</th>
            <th>Behavior</th><th>Priority</th><th>Active</th><th></th>
          </tr>
        </thead>
        <tbody>
          {creatives.map((c) => (
            <tr key={c.id}>
              <td><img src={c.image_url} alt="" className="admin-table-thumb" /></td>
              <td>{c.product_name}<div className="muted">{c.affiliate_name}</div></td>
              <td>{ZONES.find((z) => z.key === c.zone)?.label || c.zone}</td>
              <td>{c.symbol || c.asset_class || 'All pages'}</td>
              <td>{c.behavior === 'fade_on_hover' ? 'Fades on hover' : 'Static'}</td>
              <td>{c.priority}</td>
              <td>
                <button className="link-btn" onClick={() => toggleActive(c)}>
                  {c.is_active ? 'Yes' : 'No'}
                </button>
              </td>
              <td>
                <button className="link-btn" onClick={() => startEdit(c)}>Edit</button>{' '}
                <button className="link-btn" onClick={() => handleDelete(c.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* ---------- ADD / EDIT FORM ---------- */}
      <h2>{editingId ? 'Edit creative' : 'Add a new creative'}</h2>
      <form onSubmit={handleSubmit} className="admin-form">
        <label>
          Zone
          <select
            value={form.zone}
            onChange={(e) => {
              const zone = e.target.value
              const z = ZONES.find((z) => z.key === zone)
              setForm({ ...form, zone, size_key: z.defaultSize })
            }}
          >
            {ZONES.map((z) => <option key={z.key} value={z.key}>{z.label}</option>)}
          </select>
        </label>

        <label>
          Size
          <select value={form.size_key} onChange={(e) => setForm({ ...form, size_key: e.target.value })}>
            {SIZES.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </label>

        <label>
          Image URL
          <input value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} required />
        </label>

        <label>
          Click-through URL (your affiliate link)
          <input value={form.click_url} onChange={(e) => setForm({ ...form, click_url: e.target.value })} required />
        </label>

        <label>
          Product name
          <input value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} required />
        </label>

        <label>
          Affiliate / partner name
          <input value={form.affiliate_name} onChange={(e) => setForm({ ...form, affiliate_name: e.target.value })} required />
        </label>

        <label>
          Asset class (blank = show on every page)
          <select value={form.asset_class} onChange={(e) => setForm({ ...form, asset_class: e.target.value })}>
            {ASSET_CLASSES.map((a) => <option key={a} value={a}>{a || 'All'}</option>)}
          </select>
        </label>

        <label>
          Symbol (optional — narrows to one asset page, e.g. AAPL)
          <input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} />
        </label>

        <label>
          Behavior
          <select value={form.behavior} onChange={(e) => setForm({ ...form, behavior: e.target.value })}>
            <option value="static">Static — always visible</option>
            <option value="fade_on_hover">Fade on hover — dims when moused over</option>
          </select>
        </label>

        <label>
          Priority (higher shows first when multiple match)
          <input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
        </label>

        <label className="checkbox-label">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Active
        </label>

        <div className="admin-form-actions">
          <button type="submit">{editingId ? 'Save changes' : 'Add creative'}</button>
          {editingId && <button type="button" onClick={resetForm}>Cancel edit</button>}
        </div>
      </form>
    </div>
  )
}
