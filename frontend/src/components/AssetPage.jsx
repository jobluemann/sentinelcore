import React, { useEffect, useState } from 'react'
import { getAffiliateLinks } from '../api/client'
import TopCarousel from './TopCarousel.jsx'
import ProductCarousel from './ProductCarousel.jsx'
import AffiliateBanner from './AffiliateBanner.jsx'

export default function AssetPage({ asset, onBack }) {
  const [affiliates, setAffiliates] = useState([])

  useEffect(() => {
    if (!asset) return
    getAffiliateLinks(asset.symbol, asset.asset_class).then(setAffiliates)
  }, [asset])

  if (!asset) return null
  const positive = asset.change_pct >= 0

  return (
    <div className="asset-page">
      <button className="back-link" onClick={onBack}>← Back to dashboard</button>

      <ProductCarousel />

      <div className="asset-page-header">
        <div>
          <h1>{asset.symbol}</h1>
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

      <div className="asset-page-grid">
        <section className="asset-page-chart">
          <h3>Chart</h3>
          <div className="chart-placeholder">Full historical chart goes here</div>
        </section>

        <section className="asset-page-stats">
          <h3>Key Stats</h3>
          <dl>
            <dt>Asset class</dt><dd>{asset.asset_class}</dd>
            <dt>Price</dt><dd>${Number(asset.price).toFixed(2)}</dd>
            <dt>24h change</dt><dd>{asset.change_pct.toFixed(2)}%</dd>
          </dl>
        </section>

        <section className="asset-page-forecast">
          <h3>AI Forecast</h3>
          <p className="muted">Forecast engine not yet wired up — signal, confidence, and price target will appear here.</p>
        </section>

        <section className="asset-page-affiliate">
          <h3>Recommended for you</h3>
          {affiliates.length === 0 && <p className="muted">No matched products yet.</p>}
          {affiliates.map((a, i) => (
            <a className="affiliate-item" key={i} href={a.url} target="_blank" rel="noreferrer">
              <span>{a.label}</span>
              <span className="affiliate-source">{a.affiliate_name}</span>
            </a>
          ))}
        </section>
      </div>

      <footer className="dashboard-footer">
        <AffiliateBanner zone="bottom_banner" assetClass={asset.asset_class} symbol={asset.symbol} />
      </footer>
    </div>
  )
}
