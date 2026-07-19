import React from 'react'

// Tiny inline sparkline using deterministic pseudo-data derived from the
// symbol + price, so each card looks distinct without needing historical
// price data wired up yet.
function MiniSparkline({ seed, positive }) {
  const points = Array.from({ length: 12 }, (_, i) => {
    const n = Math.sin(seed * (i + 1)) * 10 + 20
    return n
  })
  const max = Math.max(...points)
  const min = Math.min(...points)
  const norm = points.map((p) => 30 - ((p - min) / (max - min || 1)) * 28)
  const path = norm.map((y, i) => `${i === 0 ? 'M' : 'L'} ${i * 9},${y}`).join(' ')

  return (
    <svg viewBox="0 0 99 32" className="sparkline">
      <path d={path} fill="none" stroke={positive ? '#22c55e' : '#ef4444'} strokeWidth="2" />
    </svg>
  )
}

export default function AssetCard({ asset, onClick }) {
  const positive = asset.change_pct >= 0
  const seed = asset.symbol.split('').reduce((a, c) => a + c.charCodeAt(0), 0) / 7

  return (
    <button className="asset-card" onClick={() => onClick(asset)}>
      <div className="asset-card-top">
        <div>
          <div className="asset-symbol">{asset.symbol}</div>
          <div className="asset-name">{asset.name}</div>
        </div>
        <span className={`badge ${asset.asset_class}`}>{asset.asset_class}</span>
      </div>

      <MiniSparkline seed={seed} positive={positive} />

      <div className="asset-card-bottom">
        <span className="asset-price">
          ${Number(asset.price).toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </span>
        <span className={`asset-change ${positive ? 'up' : 'down'}`}>
          {positive ? '▲' : '▼'} {Math.abs(asset.change_pct).toFixed(2)}%
        </span>
      </div>
      <div className="asset-card-spread">
        {asset.spread_pct != null ? `Spread: ${Number(asset.spread_pct).toFixed(3)}%` : 'Spread: N/A'}
      </div>
    </button>
  )
}
