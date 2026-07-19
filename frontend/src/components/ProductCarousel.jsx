import { useEffect, useState } from 'react'
import { getCarouselProducts, getSiteSetting } from '../api/client'

function Stars({ rating }) {
  if (!rating) return null
  const full = Math.round(rating)
  return (
    <span className="product-stars" title={`${rating} / 5`}>
      {'★'.repeat(full)}{'☆'.repeat(5 - full)}
    </span>
  )
}

export default function ProductCarousel() {
  const [products, setProducts] = useState([])
  const [disclaimer, setDisclaimer] = useState('')

  useEffect(() => {
    getCarouselProducts().then(setProducts)
    getSiteSetting('carousel_disclaimer_text').then(setDisclaimer)
  }, [])

  if (products.length === 0) return null

  // Duplicate the list so the scroll loop feels seamless, same technique as TickerStrip
  const loopProducts = products.length > 1 ? [...products, ...products] : products

  return (
    <div className="product-carousel-wrap">
      <div className="product-carousel-strip">
        {loopProducts.map((p, i) => (
          <a
            key={`${p.id}-${i}`}
            href={p.affiliate_link}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="product-card"
          >
            {p.badge && <span className={`product-badge badge-${p.badge.toLowerCase().replace(/\s+/g, '-')}`}>{p.badge}</span>}
            <img src={p.image_url} alt={p.title} className="product-card-img" />
            <div className="product-card-title">{p.title}</div>
            <Stars rating={p.rating} />
            <div className="product-card-price">
              {p.currency} {Math.ceil(Number(p.price))}
            </div>
          </a>
        ))}
      </div>
      {disclaimer && <p className="product-carousel-disclaimer">{disclaimer}</p>}
    </div>
  )
}
