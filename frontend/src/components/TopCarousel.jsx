import { useEffect, useState } from 'react'
import { getCreatives } from '../api/client'

// Shows at the top of every page. Auto-rotates through active
// 'top_carousel' creatives scoped to the current asset_class/symbol
// (or site-wide ones with no scoping set).
export default function TopCarousel({ assetClass = null, symbol = null, intervalMs = 6000 }) {
  const [slides, setSlides] = useState([])
  const [index, setIndex] = useState(0)

  useEffect(() => {
    let cancelled = false
    getCreatives('top_carousel', assetClass, symbol).then((data) => {
      if (!cancelled) setSlides(data)
    })
    return () => { cancelled = true }
  }, [assetClass, symbol])

  useEffect(() => {
    if (slides.length < 2) return
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % slides.length)
    }, intervalMs)
    return () => clearInterval(timer)
  }, [slides, intervalMs])

  if (slides.length === 0) return null

  const slide = slides[index]

  return (
    <div className="top-carousel">
      <a
        href={slide.click_url}
        target="_blank"
        rel="noopener noreferrer sponsored"
        className={`creative-leaderboard creative-${slide.behavior === 'fade_on_hover' ? 'fade-hover' : 'static'}`}
        style={{ backgroundImage: `url(${slide.image_url})` }}
        title={`${slide.product_name} — ${slide.affiliate_name}`}
      >
        <span className="creative-sponsored-tag">Sponsored</span>
      </a>
      {slides.length > 1 && (
        <div className="carousel-dots">
          {slides.map((s, i) => (
            <button
              key={s.id}
              className={`carousel-dot ${i === index ? 'active' : ''}`}
              onClick={() => setIndex(i)}
              aria-label={`Show slide ${i + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  )
}
