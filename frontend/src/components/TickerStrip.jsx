import React from 'react'

export default function TickerStrip({ items }) {
  if (!items || items.length === 0) return null

  // Duplicate the list so the scroll loop feels seamless
  const loopItems = [...items, ...items]

  return (
    <div className="ticker-strip">
      <div className="ticker-track">
        {loopItems.map((item, i) => (
          <span className="ticker-item" key={`${item.symbol}-${i}`}>
            <span className="ticker-symbol">{item.symbol}</span>
            <span className="ticker-price">${Number(item.price).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
            <span className={`ticker-change ${item.change_pct >= 0 ? 'up' : 'down'}`}>
              {item.change_pct >= 0 ? '▲' : '▼'} {Math.abs(item.change_pct).toFixed(2)}%
            </span>
            <span className="ticker-spread">
              {item.spread_pct != null ? `Spread ${Number(item.spread_pct).toFixed(3)}%` : 'Spread N/A'}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}
