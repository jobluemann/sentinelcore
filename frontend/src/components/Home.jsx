import { useEffect, useState } from 'react'
import { getTopPerformers, getWatchlist } from '../api/client'

const CATEGORY_META = {
  stock: { label: 'Shares', icon: '📈' },
  crypto: { label: 'Crypto', icon: '🪙' },
  commodity: { label: 'Commodities', icon: '🛢️' },
  forex: { label: 'Forex', icon: '💱' },
}

const TIPS = [
  "Sentinel Core pulls live pricing from independent sources across stocks, crypto, commodities, and forex.",
  "You can trade with your free $10,000 demo balance — zero real risk while you learn.",
  "Mark any asset for monitoring to keep it on your homepage without needing to trade it.",
  "Bid/ask spread is shown wherever real data supports it — that's the actual cost of trading, not just the sticker price.",
]

function MiniSparkline({ positive }) {
  const points = positive
    ? '0,35 30,30 60,32 90,20 120,24 150,10 180,14 200,6'
    : '0,10 30,14 60,12 90,22 120,20 150,32 180,28 200,36'
  return (
    <svg viewBox="0 0 200 40" className="home-spotlight-chart">
      <polyline points={points} fill="none" stroke={positive ? '#22c55e' : '#ef4444'} strokeWidth="2" />
    </svg>
  )
}

export default function Home({ idToken, onSelectCategory, onOpenAsset }) {
  const [performers, setPerformers] = useState({ overall: null, by_class: {} })
  const [watchlist, setWatchlist] = useState([])
  const [tip] = useState(TIPS[Math.floor(Math.random() * TIPS.length)])

  useEffect(() => {
    getTopPerformers().then(setPerformers)
    if (idToken) getWatchlist(idToken).then(setWatchlist)
  }, [idToken])

  const overall = performers.overall
  const overallPositive = overall && overall.change_pct >= 0

  return (
    <div className="home-page">
      <div className="home-category-grid">
        {Object.entries(CATEGORY_META).map(([key, meta]) => {
          const top = performers.by_class[key]
          return (
            <button key={key} className="home-category-card" onClick={() => onSelectCategory(key)}>
              <span className="home-category-icon">{meta.icon}</span>
              <span className="home-category-label">{meta.label}</span>
              {top && (
                <span className="home-category-top">
                  Top: {top.symbol} {top.change_pct >= 0 ? '+' : ''}{Number(top.change_pct).toFixed(1)}%
                </span>
              )}
            </button>
          )
        })}
      </div>

      <div className="home-spotlight-row">
        <div className="home-spotlight-card">
          <p className="home-panel-label">Top performer today</p>
          {overall ? (
            <>
              <p className="home-spotlight-value">
                {overall.name || overall.symbol} · {overallPositive ? '+' : ''}{Number(overall.change_pct).toFixed(2)}%
              </p>
              <MiniSparkline positive={overallPositive} />
            </>
          ) : (
            <p className="muted">Loading...</p>
          )}
        </div>
        <div className="home-tip-card">
          <p className="home-panel-label">Tip of the day</p>
          <p className="home-tip-text">{tip}</p>
        </div>
      </div>

      <p className="home-section-title">Your watchlist</p>
      <div className="home-watchlist-grid">
        {watchlist.map((a) => (
          <button key={a.symbol} className="home-watchlist-card" onClick={() => onOpenAsset(a)}>
            <span className="home-watchlist-symbol">{a.symbol}</span>
            <span className="home-watchlist-price">
              ${Number(a.price).toLocaleString(undefined, { maximumFractionDigits: 2 })}
              <span className={a.change_pct >= 0 ? 'up' : 'down'}>
                {' '}{a.change_pct >= 0 ? '▲' : '▼'} {Math.abs(a.change_pct).toFixed(2)}%
              </span>
            </span>
          </button>
        ))}
        <div className="home-watchlist-empty">
          <p className="muted">Mark assets for monitoring to see them here — open any asset and tap the star.</p>
        </div>
      </div>
    </div>
  )
}
