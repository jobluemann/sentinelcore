import React, { useEffect, useState } from 'react'
import TickerStrip from './components/TickerStrip.jsx'
import AssetCard from './components/AssetCard.jsx'
import AssetPanel from './components/AssetPanel.jsx'
import AssetPage from './components/AssetPage.jsx'
import Home from './components/Home.jsx'
import CategoryPage from './components/CategoryPage.jsx'
import Login from './components/Login.jsx'
import Onboarding from './components/Onboarding.jsx'
import TopCarousel from './components/TopCarousel.jsx'
import ProductCarousel from './components/ProductCarousel.jsx'
import AffiliateBanner from './components/AffiliateBanner.jsx'
import AdminCreatives from './components/AdminCreatives.jsx'
import AdminAIProviders from './components/AdminAIProviders.jsx'
import AdminProductCarousel from './components/AdminProductCarousel.jsx'
import AdminAffiliateAPIs from './components/AdminAffiliateAPIs.jsx'
import AdminScrollSettings from './components/AdminScrollSettings.jsx'
import AdminEmailCampaigns from './components/AdminEmailCampaigns.jsx'
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
  const [view, setView] = useState('home') // 'home' | 'category'
  const [viewCategory, setViewCategory] = useState(null)
  const [idToken, setIdToken] = useState(null)

  // Called after a successful buy/sell so the header balance and any open
  // trade forms reflect the new cash balance immediately, no page reload.
  function handleTradeComplete(newBalance) {
    setSession((prev) => prev && {
      ...prev,
      demo_account: { ...prev.demo_account, cash_balance: newBalance },
    })
  }

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

  useEffect(() => {
    if (!session) { setIdToken(null); return }
    auth.currentUser?.getIdToken().then(setIdToken)
  }, [session])

  const filtered = filter === 'all' ? assets : assets.filter((a) => a.asset_class === filter)

  // Admin routes are separate from the logged-in dashboard — protected by the
  // admin key you enter on each page, not by Firebase login.
  if (route === '#admin') return <AdminCreatives />
  if (route === '#admin-ai') return <AdminAIProviders />
  if (route === '#admin-products') return <AdminProductCarousel />
  if (route === '#admin-apis') return <AdminAffiliateAPIs />
  if (route === '#admin-scroll') return <AdminScrollSettings />
  if (route === '#admin-email') return <AdminEmailCampaigns />

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
      <AssetPage asset={pageAsset} session={session} onTradeComplete={handleTradeComplete} onBack={() => setPageAsset(null)} />
    )
  }

  if (view === 'category' && viewCategory) {
    return (
      <CategoryPage
        assetClass={viewCategory}
        assets={assets}
        onBack={() => setView('home')}
        onOpenAsset={setPanelAsset}
      />
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

      <TickerStrip items={assets} />

      <ProductCarousel />

      <Home
        idToken={idToken}
        onSelectCategory={(cat) => { setViewCategory(cat); setView('category') }}
        onOpenAsset={setPanelAsset}
      />

      <footer className="dashboard-footer">
        <AffiliateBanner zone="bottom_banner" />
      </footer>

      <AssetPanel
        asset={panelAsset}
        session={session}
        onTradeComplete={handleTradeComplete}
        onClose={() => setPanelAsset(null)}
        onViewFullPage={(a) => {
          setPanelAsset(null)
          setPageAsset(a)
        }}
      />
    </div>
  )
}
