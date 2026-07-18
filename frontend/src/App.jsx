import React, { useEffect, useState } from 'react'
import TickerStrip from './components/TickerStrip.jsx'
import AssetCard from './components/AssetCard.jsx'
import AssetPanel from './components/AssetPanel.jsx'
import AssetPage from './components/AssetPage.jsx'
import Login from './components/Login.jsx'
import Onboarding from './components/Onboarding.jsx'
import TopCarousel from './components/TopCarousel.jsx'
import AffiliateBanner from './components/AffiliateBanner.jsx'
import AdminCreatives from './components/AdminCreatives.jsx'
import AdminAIProviders from './components/AdminAIProviders.jsx'
import { getTicker, getOnboardingStatus } from './api/client.js'
import { auth } from './firebase.js'
import { onAuthStateChanged, signOut } from 'firebase/auth'

export default function App() {
  const [assets, setAssets] = useState([])
  const [panelAsset, setPanelAsset] = useState(null)
  const [pageAsset, setPageAsset] = useState(null)
  const [filter, setFilter] = useState('all')
  const [session, setSession] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [needsOnboarding, setNeedsOnboarding] = useState(false)
  const [onboardingChecked, setOnboardingChecked] = useState(false)

  // Simple hash-based routes for admin pages — no router dependency needed.
  // Visit yoursite.com/#admin for creatives, /#admin-ai for AI providers.
  const [route, setRoute] = useState(window.location.hash)
  useEffect(() => {
    const onHashChange = () => setRoute(window.location.hash)
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (user) => {
      setAuthChecked(true)
      if (!user) setSession(null)
    })
    return unsub
  }, [])

  useEffect(() => {
    getTicker().then(setAssets)
    const interval = setInterval(() => getTicker().then(setAssets), 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!session) return
    let cancelled = false
    auth.currentUser?.getIdToken().then((idToken) =>
      getOnboardingStatus(idToken).then((status) => {
        if (cancelled) return
        setNeedsOnboarding(!(status?.completed))
        setOnboardingChecked(true)
      })
    )
    return () => { cancelled = true }
  }, [session])

  const filtered = filter === 'all' ? assets : assets.filter((a) => a.asset_class === filter)

  // Admin routes are separate from the logged-in dashboard — protected by the
  // admin key you enter on each page, not by Firebase login.
  if (route === '#admin') return <AdminCreatives />
  if (route === '#admin-ai') return <AdminAIProviders />

  if (!authChecked) {
    return <div className="loading-screen">Loading...</div>
  }

  if (!session) {
    return <Login onLoggedIn={setSession} />
  }

  if (session && onboardingChecked && needsOnboarding) {
    return <Onboarding onComplete={() => setNeedsOnboarding(false)} />
  }

  if (pageAsset) {
    return (
      <AssetPage asset={pageAsset} onBack={() => setPageAsset(null)} />
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Sentinel Core</h1>
        <div className="header-right">
          <span className="muted">
            {session.user.email} · ${Number(session.demo_account.cash_balance).toLocaleString()}
          </span>
          <button className="link-btn" onClick={() => signOut(auth)}>
            Sign out
          </button>
        </div>
      </header>

      <TopCarousel />

      <TickerStrip items={assets} />

      <div className="filter-bar">
        {['all', 'stock', 'crypto', 'commodity', 'forex'].map((f) => (
          <button key={f} className={filter === f ? 'active' : ''} onClick={() => setFilter(f)}>
            {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="dashboard-layout">
        <main className="asset-grid">
          {filtered.map((asset) => (
            <AssetCard key={asset.symbol} asset={asset} onClick={setPanelAsset} />
          ))}
        </main>
        <aside className="side-rail">
          <AffiliateBanner zone="side_banner" assetClass={filter === 'all' ? null : filter} />
        </aside>
      </div>

      <footer className="dashboard-footer">
        <AffiliateBanner zone="bottom_banner" assetClass={filter === 'all' ? null : filter} />
      </footer>

      <AssetPanel
        asset={panelAsset}
        onClose={() => setPanelAsset(null)}
        onViewFullPage={(a) => {
          setPanelAsset(null)
          setPageAsset(a)
        }}
      />
    </div>
  )
}
