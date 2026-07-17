// In local dev, Vite's server proxy forwards '/api' to Render (see vite.config.js),
// so a relative path works. In a static production build (e.g. hosted on SiteGround),
// there's no proxy, so we need the full Render URL instead. Set VITE_API_BASE_URL
// at build time (see .env.production) to point at the live backend.
const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const MOCK_TICKER = [
  { symbol: 'AAPL', name: 'Apple Inc.', asset_class: 'stock', price: 224.31, change_pct: 1.2 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', asset_class: 'stock', price: 441.58, change_pct: -0.4 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', asset_class: 'stock', price: 132.76, change_pct: 3.1 },
  { symbol: 'TSLA', name: 'Tesla Inc.', asset_class: 'stock', price: 256.12, change_pct: -2.3 },
  { symbol: 'BTC-USD', name: 'Bitcoin', asset_class: 'crypto', price: 65210.4, change_pct: 2.7 },
  { symbol: 'ETH-USD', name: 'Ethereum', asset_class: 'crypto', price: 3402.9, change_pct: -1.1 },
  { symbol: 'GC=F', name: 'Gold', asset_class: 'commodity', price: 2389.5, change_pct: 0.3 },
  { symbol: 'CL=F', name: 'Crude Oil', asset_class: 'commodity', price: 78.22, change_pct: -0.8 },
  { symbol: 'EURUSD=X', name: 'EUR/USD', asset_class: 'forex', price: 1.0842, change_pct: 0.1 },
  { symbol: 'GBPUSD=X', name: 'GBP/USD', asset_class: 'forex', price: 1.2691, change_pct: -0.2 },
]

const MOCK_AFFILIATES = {
  stock: [
    { label: 'The Intelligent Investor', affiliate_name: 'Amazon', url: '#' },
  ],
  crypto: [
    { label: 'Ledger Nano X Hardware Wallet', affiliate_name: 'Amazon', url: '#' },
  ],
  commodity: [
    { label: 'Precious Metals Storage Box', affiliate_name: 'Amazon', url: '#' },
  ],
  forex: [
    { label: '3-Monitor Trading Desk Mount', affiliate_name: 'Amazon', url: '#' },
  ],
}

async function safeFetch(path, opts) {
  try {
    const res = await fetch(`${BASE}${path}`, opts)
    if (!res.ok) throw new Error(`${res.status}`)
    return await res.json()
  } catch (err) {
    console.warn(`[api] ${path} unreachable, using mock data (${err.message})`)
    return null
  }
}

export async function getTicker() {
  const data = await safeFetch('/ticker')
  return data ?? MOCK_TICKER
}

export async function getAffiliateLinks(symbol, assetClass) {
  const data = await safeFetch(`/affiliate-links?symbol=${symbol}&asset_class=${assetClass}`)
  return data ?? MOCK_AFFILIATES[assetClass] ?? []
}

// ---------- Affiliate creatives (banners + top carousel) ----------
export async function getCreatives(zone, assetClass, symbol) {
  const params = new URLSearchParams()
  if (zone) params.set('zone', zone)
  if (assetClass) params.set('asset_class', assetClass)
  if (symbol) params.set('symbol', symbol)
  const data = await safeFetch(`/creatives?${params.toString()}`)
  return data ?? []
}

// ---------- Admin: manage creatives (requires X-Admin-Key) ----------
async function adminFetch(path, adminKey, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', 'X-Admin-Key': adminKey, ...(opts.headers || {}) },
  })
  if (!res.ok) throw new Error(`Admin request failed (${res.status})`)
  return res.json()
}

export function adminListCreatives(adminKey) {
  return adminFetch('/admin/creatives', adminKey)
}

export function adminCreateCreative(adminKey, creative) {
  return adminFetch('/admin/creatives', adminKey, { method: 'POST', body: JSON.stringify(creative) })
}

export function adminUpdateCreative(adminKey, id, creative) {
  return adminFetch(`/admin/creatives/${id}`, adminKey, { method: 'PUT', body: JSON.stringify(creative) })
}

export function adminDeleteCreative(adminKey, id) {
  return adminFetch(`/admin/creatives/${id}`, adminKey, { method: 'DELETE' })
}

export async function getPortfolio(token) {
  return safeFetch('/demo/portfolio', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function placeBuy(token, order) {
  return safeFetch('/demo/buy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(order),
  })
}

export async function placeSell(token, order) {
  return safeFetch('/demo/sell', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(order),
  })
}
