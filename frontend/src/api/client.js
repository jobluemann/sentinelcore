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

// ---------- Admin: email campaigns ----------
export function adminListTemplates(adminKey) {
  return adminFetch('/admin/email-templates', adminKey)
}
export function adminCreateTemplate(adminKey, template) {
  return adminFetch('/admin/email-templates', adminKey, { method: 'POST', body: JSON.stringify(template) })
}
export function adminUpdateTemplate(adminKey, id, template) {
  return adminFetch(`/admin/email-templates/${id}`, adminKey, { method: 'PUT', body: JSON.stringify(template) })
}
export function adminDeleteTemplate(adminKey, id) {
  return adminFetch(`/admin/email-templates/${id}`, adminKey, { method: 'DELETE' })
}
export function adminPreviewAudience(adminKey, filters) {
  return adminFetch('/admin/audience/preview', adminKey, { method: 'POST', body: JSON.stringify(filters) })
}
export function adminSendCampaign(adminKey, campaign) {
  return adminFetch('/admin/email-campaigns/send', adminKey, { method: 'POST', body: JSON.stringify(campaign) })
}
export function adminListCampaigns(adminKey) {
  return adminFetch('/admin/email-campaigns', adminKey)
}

// ---------- Admin: affiliate API connections (credential storage only) ----------
export function adminListAffiliateAPIConnections(adminKey) {
  return adminFetch('/admin/affiliate-api-connections', adminKey)
}
export function adminCreateAffiliateAPIConnection(adminKey, conn) {
  return adminFetch('/admin/affiliate-api-connections', adminKey, { method: 'POST', body: JSON.stringify(conn) })
}
export function adminUpdateAffiliateAPIConnection(adminKey, id, conn) {
  return adminFetch(`/admin/affiliate-api-connections/${id}`, adminKey, { method: 'PUT', body: JSON.stringify(conn) })
}
export function adminDeleteAffiliateAPIConnection(adminKey, id) {
  return adminFetch(`/admin/affiliate-api-connections/${id}`, adminKey, { method: 'DELETE' })
}

// ---------- Product carousel (5-8 item Amazon-style strip) ----------
export async function getCarouselProducts() {
  const data = await safeFetch('/carousel-products')
  return data ?? []
}

export async function getSiteSetting(key) {
  const data = await safeFetch(`/site-settings/${key}`)
  return data?.value ?? ''
}

export function adminListCarouselProducts(adminKey) {
  return adminFetch('/admin/carousel-products', adminKey)
}
export function adminCreateCarouselProduct(adminKey, product) {
  return adminFetch('/admin/carousel-products', adminKey, { method: 'POST', body: JSON.stringify(product) })
}
export function adminUpdateCarouselProduct(adminKey, id, product) {
  return adminFetch(`/admin/carousel-products/${id}`, adminKey, { method: 'PUT', body: JSON.stringify(product) })
}
export function adminDeleteCarouselProduct(adminKey, id) {
  return adminFetch(`/admin/carousel-products/${id}`, adminKey, { method: 'DELETE' })
}
export function adminSetSiteSetting(adminKey, key, value) {
  return adminFetch(`/admin/site-settings/${key}`, adminKey, { method: 'PUT', body: JSON.stringify({ value }) })
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

// ---------- Admin: manage AI providers (requires X-Admin-Key) ----------
export function adminListAIProviders(adminKey) {
  return adminFetch('/admin/ai-providers', adminKey)
}
export function adminCreateAIProvider(adminKey, provider) {
  return adminFetch('/admin/ai-providers', adminKey, { method: 'POST', body: JSON.stringify(provider) })
}
export function adminUpdateAIProvider(adminKey, id, provider) {
  return adminFetch(`/admin/ai-providers/${id}`, adminKey, { method: 'PUT', body: JSON.stringify(provider) })
}
export function adminDeleteAIProvider(adminKey, id) {
  return adminFetch(`/admin/ai-providers/${id}`, adminKey, { method: 'DELETE' })
}
export function adminTestAIProvider(adminKey, id) {
  return adminFetch(`/admin/ai-providers/${id}/test`, adminKey, { method: 'POST' })
}
export function adminTestClaudeFallback(adminKey) {
  return adminFetch('/admin/ai-providers/test-claude-fallback', adminKey, { method: 'POST' })
}
export async function getOnboardingStatus(token) {
  return safeFetch('/onboarding/status', { headers: { Authorization: `Bearer ${token}` } })
}

export async function saveOnboarding(token, answers) {
  const res = await fetch(`${BASE}/onboarding`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(answers),
  })
  if (!res.ok) throw new Error(`Save failed (${res.status})`)
  return res.json()
}

// ---------- Watchlist ----------
export async function getWatchlist(token) {
  const res = await fetch(`${BASE}/watchlist`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) return []
  return res.json()
}

export async function addToWatchlist(token, symbol, assetClass) {
  const res = await fetch(`${BASE}/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ symbol, asset_class: assetClass }),
  })
  return res.ok
}

export async function removeFromWatchlist(token, symbol) {
  const res = await fetch(`${BASE}/watchlist/${symbol}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.ok
}

export async function getTopPerformers() {
  const data = await safeFetch('/ticker/top-performers')
  return data ?? { overall: null, by_class: {} }
}

export async function getPortfolio(token) {
  return safeFetch('/demo/portfolio', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

async function tradeFetch(path, token, order) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(order),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    let message = text
    try { message = JSON.parse(text).detail || text } catch { /* not JSON, use raw text */ }
    throw new Error(message || `Trade failed (${res.status})`)
  }
  return res.json()
}

export async function placeBuy(token, order) {
  return tradeFetch('/demo/buy', token, order)
}

export async function placeSell(token, order) {
  return tradeFetch('/demo/sell', token, order)
}
