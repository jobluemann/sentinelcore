import React, { useEffect, useState } from 'react'
import { getSiteSetting } from '../api/client'

const DEFAULT_SCROLL = { enabled: true, direction: 'left', speed_seconds: 40 }

export default function TickerStrip({ items }) {
  const [scroll, setScroll] = useState(DEFAULT_SCROLL)

  useEffect(() => {
    getSiteSetting('ticker_scroll_config').then((raw) => {
      if (!raw) return
      try {
        setScroll({ ...DEFAULT_SCROLL, ...JSON.parse(raw) })
      } catch {
        // malformed setting — keep defaults
      }
    })
  }, [])

  if (!items || items.length === 0) return null

  // Duplicate the list so the scroll loop feels seamless
  const loopItems = [...items, ...items]

  const trackStyle = scroll.enabled
    ? {
        animationDuration: `${scroll.speed_seconds}s`,
        animationDirection: scroll.direction === 'right' ? 'reverse' : 'normal',
      }
    : { animation: 'none' }

  return (
    <div className="ticker-strip">
      <div className="ticker-track" style={trackStyle}>
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
