import TickerStrip from './TickerStrip.jsx'
import AssetCard from './AssetCard.jsx'
import AffiliateBanner from './AffiliateBanner.jsx'

const LABELS = { stock: 'Shares', crypto: 'Crypto', commodity: 'Commodities', forex: 'Forex' }

export default function CategoryPage({ assetClass, assets, onBack, onOpenAsset }) {
  const filtered = assets.filter((a) => a.asset_class === assetClass)

  return (
    <div className="app">
      <header className="app-header">
        <button className="back-link" onClick={onBack}>← Back to home</button>
        <h1>{LABELS[assetClass] || assetClass}</h1>
      </header>

      <TickerStrip items={assets} />

      <div className="dashboard-layout">
        <main className="asset-grid">
          {filtered.map((asset) => (
            <AssetCard key={asset.symbol} asset={asset} onClick={onOpenAsset} />
          ))}
        </main>
        <aside className="side-rail">
          <AffiliateBanner zone="side_banner" assetClass={assetClass} />
        </aside>
      </div>

      <footer className="dashboard-footer">
        <AffiliateBanner zone="bottom_banner" assetClass={assetClass} />
      </footer>
    </div>
  )
}
