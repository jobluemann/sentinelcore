import React, { useEffect, useState } from 'react'
import { getAffiliateLinks, getWatchlist, addToWatchlist, removeFromWatchlist } from '../api/client'
import { auth } from '../firebase.js'
import TradeForm from './TradeForm.jsx'

export default function AssetPanel({ asset, session, onTradeComplete, onClose, onViewFullPage }) {
  const [affiliates, setAffiliates] = useState([])
  const [tab, setTab] = useState('trade') // 'trade' | 'forecast' | 'affiliate'
  const [watching, setWatching] = useState(false)

  useEffect(() => {
    if (!asset) return
    getAffiliateLinks(asset.symbol, asset.asset_class).then(setAffiliates)
    auth.currentUser?.getIdToken().then((idToken) =>
      getWatchlist(idToken).then((list) => setWatching(list.some((w) => w.symbol === asset.symbol)))
    )
  }, [asset])

  async function toggleWatch() {
    const idToken = await auth.currentUser.getIdToken()
    if (watching) {
      await removeFromWatchlist(idToken, asset.symbol)
    } else {
      await addToWatchlist(idToken, asset.symbol, asset.asset_class)
    }
    setWatching(!watching)
  }

  if (!asset) return null
  const positive = asset.change_pct >= 0

  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <button className="panel-close" onClick={onClose}>×</button>

        <div className="panel-header">
          <div>
            <h2>
              {asset.symbol}{' '}
              <button
                className={`watch-star ${watching ? 'active' : ''}`}
                onClick={toggleWatch}
                title={watching ? 'Remove from monitoring' : 'Mark for monitoring'}
                aria-label={watching ? 'Remove from monitoring' : 'Mark for monitoring'}
              >
                {watching ? '★' : '☆'}
              </button>
            </h2>
            <p className="asset-name">{asset.name}</p>
          </div>
          <div className="panel-price-block">
            <div className="asset-price large">
              ${Number(asset.price).toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </div>
            <div className={`asset-change ${positive ? 'up' : 'down'}`}>
              {positive ? '▲' : '▼'} {Math.abs(asset.change_pct).toFixed(2)}%
            </div>
          </div>
        </div>

        <div className="panel-tabs">
          <button className={tab === 'trade' ? 'active' : ''} onClick={() => setTab('trade')}>
            Trade
          </button>
          <button className={tab === 'forecast' ? 'active' : ''} onClick={() => setTab('forecast')}>
            AI Forecast
          </button>
          <button className={tab === 'affiliate' ? 'active' : ''} onClick={() => setTab('affiliate')}>
            Recommended
          </button>
        </div>

        <div className="panel-body">
          {tab === 'trade' && (
            <TradeForm
              asset={asset}
              cashBalance={session?.demo_account?.cash_balance}
              onTradeComplete={onTradeComplete}
            />
          )}

          {tab === 'forecast' && (
            <div className="forecast-placeholder">
              <p>AI Forecast for {asset.symbol} will appear here once the forecast engine is wired up.</p>
              <p className="muted">Signal, confidence, price target, and rationale will be generated per-symbol.</p>
            </div>
          )}

          {tab === 'affiliate' && (
            <div className="affiliate-list">
              {affiliates.length === 0 && <p className="muted">No matched products yet.</p>}
              {affiliates.map((a, i) => (
                <a className="affiliate-item" key={i} href={a.url} target="_blank" rel="noreferrer">
                  <span>{a.label}</span>
                  <span className="affiliate-source">{a.affiliate_name}</span>
                </a>
              ))}
            </div>
          )}
        </div>

        <button className="panel-fullpage-link" onClick={() => onViewFullPage(asset)}>
          View full page →
        </button>
      </div>
    </div>
  )
}
