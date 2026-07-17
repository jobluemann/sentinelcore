import React, { useEffect, useState } from 'react'
import TickerStrip from './components/TickerStrip.jsx'
import AssetCard from './components/AssetCard.jsx'
import AssetPanel from './components/AssetPanel.jsx'
import AssetPage from './components/AssetPage.jsx'
import Login from './components/Login.jsx'
import { getTicker } from './api/client.js'
import { auth } from './firebase.js'
import { onAuthStateChanged, signOut } from 'firebase/auth'

export default function App() {
  const [assets, setAssets] = useState([])
  const [panelAsset, setPanelAsset] = useState(null)
  const [pageAsset, setPageAsset] = useState(null)
  const [filter, setFilter] = useState('all')
  const [session, setSession] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)

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

  const filtered = filter === 'all' ? assets : assets.filter((a) => a.asset_class === filter)

  if (!authChecked) {
    return <div className="loading-screen">Loading...</div>
  }

  if (!session) {
    return <Login onLoggedIn={setSession} />
  }

  if (pageAsset) {
    return <AssetPage asset={pageAsset} onBack={() => setPageAsset(null)} />
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

      <div className="filter-bar">
        {['all', 'stock', 'crypto', 'commodity', 'forex'].map((f) => (
          <button key={f} className={filter === f ? 'active' : ''} onClick={() => setFilter(f)}>
            {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <main className="asset-grid">
        {filtered.map((asset) => (
          <AssetCard key={asset.symbol} asset={asset} onClick={setPanelAsset} />
        ))}
      </main>

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
