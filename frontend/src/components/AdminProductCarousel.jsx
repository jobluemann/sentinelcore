import { useEffect, useState } from 'react'
import {
  adminListCarouselProducts,
  adminCreateCarouselProduct,
  adminUpdateCarouselProduct,
  adminDeleteCarouselProduct,
  adminSetSiteSetting,
  getSiteSetting,
} from '../api/client'

const CURRENCIES = ['USD', 'ZAR', 'EUR', 'GBP']
const BADGES = ['', 'Best Seller', 'New Arrival', 'Trending Now', 'Limited Stock']

const BLANK_FORM = {
  title: '',
  image_url: '',
  price: '',
  currency: 'USD',
  affiliate_link: '',
  category: '',
  rating: '',
  badge: '',
  disclosed_shipping: false,
  priority: 0,
  is_active: true,
}

export default function AdminProductCarousel() {
  const [adminKey, setAdminKey] = useState('')
  const [keyInput, setKeyInput] = useState('')
  const [products, setProducts] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(BLANK_FORM)
  const [editingId, setEditingId] = useState(null)
  const [disclaimer, setDisclaimer] = useState('')
  const [disclaimerSaved, setDisclaimerSaved] = useState(false)

  async function loadProducts(key) {
    try {
      setError(null)
      const data = await adminListCarouselProducts(key)
      setProducts(data)
    } catch {
      setError('Could not load products — check your admin key.')
      setProducts([])
    }
  }

  useEffect(() => {
    if (adminKey) {
      loadProducts(adminKey)
      getSiteSetting('carousel_disclaimer_text').then(setDisclaimer)
    }
  }, [adminKey])

  function handleUnlock(e) {
    e.preventDefault()
    setAdminKey(keyInput)
  }

  function startEdit(p) {
    setEditingId(p.id)
    setForm({
      title: p.title,
      image_url: p.image_url,
      price: p.price,
      currency: p.currency,
      affiliate_link: p.affiliate_link,
      category: p.category || '',
      rating: p.rating || '',
      badge: p.badge || '',
      disclosed_shipping: p.disclosed_shipping,
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
    const payload = {
      ...form,
      price: Number(form.price),
      rating: form.rating ? Number(form.rating) : null,
      badge: form.badge || null,
      category: form.category || null,
      priority: Number(form.priority),
    }
    try {
      if (editingId) {
        await adminUpdateCarouselProduct(adminKey, editingId, payload)
      } else {
        await adminCreateCarouselProduct(adminKey, payload)
      }
      resetForm()
      loadProducts(adminKey)
    } catch {
      setError('Save failed — check the fields and your admin key.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Remove this product?')) return
    await adminDeleteCarouselProduct(adminKey, id)
    loadProducts(adminKey)
  }

  async function toggleField(p, field) {
    await adminUpdateCarouselProduct(adminKey, p.id, { ...p, [field]: !p[field] })
    loadProducts(adminKey)
  }

  async function saveDisclaimer() {
    await adminSetSiteSetting(adminKey, 'carousel_disclaimer_text', disclaimer)
    setDisclaimerSaved(true)
    setTimeout(() => setDisclaimerSaved(false), 2000)
  }

  if (!adminKey) {
    return (
      <div className="admin-gate">
        <form onSubmit={handleUnlock} className="admin-gate-form">
          <h2>Admin — Product Carousel</h2>
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
      <h1>Product Carousel</h1>
      <p className="muted">
        Add as many products as you want, manually — title, image URL, price, your affiliate link, rating,
        and an optional badge. A product will not go live (even if "Active" is ticked) unless "Disclosed
        shipping/costs" is also ticked.
      </p>
      {error && <p className="admin-error">{error}</p>}

      <h2>Disclaimer text</h2>
      <p className="muted">Shown in small print under the carousel. Leave blank to hide it.</p>
      <textarea
        className="admin-textarea"
        value={disclaimer}
        onChange={(e) => setDisclaimer(e.target.value)}
        rows={2}
      />
      <button onClick={saveDisclaimer} className="link-btn">
        {disclaimerSaved ? 'Saved ✓' : 'Save disclaimer text'}
      </button>

      <h2>Products ({products.filter((p) => p.is_active && p.disclosed_shipping).length} live)</h2>
      <table className="admin-table">
        <thead>
          <tr>
            <th>On</th><th>Preview</th><th>Title</th><th>Price</th><th>Rating</th>
            <th>Badge</th><th>Disclosed</th><th></th>
          </tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              <td>
                <button className="link-btn" onClick={() => toggleField(p, 'is_active')}>
                  {p.is_active ? 'Yes' : 'No'}
                </button>
              </td>
              <td><img src={p.image_url} alt="" className="admin-table-thumb" /></td>
              <td>{p.title}<div className="muted">{p.category}</div></td>
              <td>{p.currency} {Math.ceil(Number(p.price))}</td>
              <td>{p.rating ? `${p.rating} ★` : '—'}</td>
              <td>{p.badge || '—'}</td>
              <td>
                <button className="link-btn" onClick={() => toggleField(p, 'disclosed_shipping')}>
                  {p.disclosed_shipping ? 'Yes' : 'No'}
                </button>
              </td>
              <td>
                <button className="link-btn" onClick={() => startEdit(p)}>Edit</button>{' '}
                <button className="link-btn" onClick={() => handleDelete(p.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>{editingId ? 'Edit product' : 'Add a product'}</h2>
      <form onSubmit={handleSubmit} className="admin-form">
        <label>
          Title
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        </label>

        <label>
          Image URL
          <input value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} required />
        </label>

        <label>
          Price
          <input type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required />
        </label>

        <label>
          Currency
          <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
            {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>

        <label>
          Affiliate link
          <input value={form.affiliate_link} onChange={(e) => setForm({ ...form, affiliate_link: e.target.value })} required />
        </label>

        <label>
          Category (optional)
          <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="e.g. Electronics" />
        </label>

        <label>
          Rating (optional, 0–5)
          <input type="number" min="0" max="5" step="0.5" value={form.rating} onChange={(e) => setForm({ ...form, rating: e.target.value })} />
        </label>

        <label>
          Badge (optional)
          <select value={form.badge} onChange={(e) => setForm({ ...form, badge: e.target.value })}>
            {BADGES.map((b) => <option key={b} value={b}>{b || 'None'}</option>)}
          </select>
        </label>

        <label>
          Priority (higher shows first)
          <input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
        </label>

        <label className="checkbox-label">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
          Active
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={form.disclosed_shipping}
            onChange={(e) => setForm({ ...form, disclosed_shipping: e.target.checked })}
          />
          Disclosed shipping/import costs? (required to go live)
        </label>

        <div className="admin-form-actions">
          <button type="submit">{editingId ? 'Save changes' : 'Add product'}</button>
          {editingId && <button type="button" onClick={resetForm}>Cancel edit</button>}
        </div>
      </form>
    </div>
  )
}
