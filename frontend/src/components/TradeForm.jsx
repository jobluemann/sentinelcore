import { useState } from 'react'
import { auth } from '../firebase.js'
import { placeBuy, placeSell } from '../api/client.js'

export default function TradeForm({ asset, cashBalance, onTradeComplete }) {
  const [side, setSide] = useState('buy') // 'buy' | 'sell'
  const [quantity, setQuantity] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Realistic execution price: buy fills at the ask, sell fills at the bid,
  // same as a real platform — falls back to the plain price if spread data
  // isn't available for this asset (e.g. most crypto right now).
  const execPrice =
    side === 'buy'
      ? Number(asset.ask_price ?? asset.price)
      : Number(asset.bid_price ?? asset.price)

  const hasSpread = asset.bid_price != null && asset.ask_price != null
  const qtyNum = Number(quantity) || 0
  const estimatedTotal = qtyNum * execPrice

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    if (qtyNum <= 0) {
      setError('Enter a quantity greater than 0')
      return
    }
    setSubmitting(true)
    try {
      const idToken = await auth.currentUser.getIdToken()
      const order = { symbol: asset.symbol, asset_class: asset.asset_class, quantity: qtyNum, price: execPrice }
      const result = side === 'buy' ? await placeBuy(idToken, order) : await placeSell(idToken, order)
      setSuccess(
        `${side === 'buy' ? 'Bought' : 'Sold'} ${qtyNum} ${asset.symbol} @ $${execPrice.toFixed(2)}`
      )
      setQuantity('')
      onTradeComplete?.(result.new_balance)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="trade-form">
      <div className="trade-side-toggle">
        <button
          type="button"
          className={side === 'buy' ? 'trade-side-btn buy active' : 'trade-side-btn buy'}
          onClick={() => setSide('buy')}
        >
          Buy
        </button>
        <button
          type="button"
          className={side === 'sell' ? 'trade-side-btn sell active' : 'trade-side-btn sell'}
          onClick={() => setSide('sell')}
        >
          Sell
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <label className="trade-qty-label">
          Quantity
          <input
            type="number"
            step="any"
            min="0"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="0"
            required
          />
        </label>

        <div className="trade-cost-preview">
          <div className="trade-cost-row">
            <span>Execution price</span>
            <span>${execPrice.toLocaleString(undefined, { maximumFractionDigits: 4 })}</span>
          </div>
          <div className="trade-cost-row">
            <span>Estimated {side === 'buy' ? 'cost' : 'proceeds'}</span>
            <span className="trade-cost-total">
              ${estimatedTotal.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="trade-cost-note">
            {hasSpread
              ? `Includes real bid/ask spread (${Number(asset.spread_pct).toFixed(3)}%) — same as a live platform.`
              : 'Live bid/ask spread not available for this asset yet — using last traded price.'}
          </div>
          {cashBalance != null && (
            <div className="trade-cost-row muted">
              <span>Available cash</span>
              <span>${Number(cashBalance).toLocaleString()}</span>
            </div>
          )}
        </div>

        <button type="submit" className={`trade-submit-btn ${side}`} disabled={submitting}>
          {submitting ? 'Placing order...' : `${side === 'buy' ? 'Buy' : 'Sell'} ${asset.symbol}`}
        </button>

        {error && <p className="trade-error">{error}</p>}
        {success && <p className="trade-success">{success}</p>}
      </form>
    </div>
  )
}
