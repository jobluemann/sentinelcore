import { useEffect, useState } from 'react'
import { getCreatives } from '../api/client'

const SIZE_CLASS = {
  leaderboard_728x90: 'creative-leaderboard',
  skyscraper_160x600: 'creative-skyscraper',
  rectangle_300x250: 'creative-rectangle',
}

// zone: 'side_banner' | 'bottom_banner'
export default function AffiliateBanner({ zone, assetClass = null, symbol = null }) {
  const [creative, setCreative] = useState(null)

  useEffect(() => {
    let cancelled = false
    getCreatives(zone, assetClass, symbol).then((data) => {
      if (!cancelled) setCreative(data[0] || null) // highest-priority match for this slot
    })
    return () => { cancelled = true }
  }, [zone, assetClass, symbol])

  if (!creative) return null

  const sizeClass = SIZE_CLASS[creative.size_key] || 'creative-rectangle'
  const behaviorClass = creative.behavior === 'fade_on_hover' ? 'creative-fade-hover' : 'creative-static'

  if (creative.creative_type === 'raw_html') {
    return (
      <div
        className={`affiliate-banner ${sizeClass} ${behaviorClass} affiliate-banner-embed`}
        dangerouslySetInnerHTML={{ __html: creative.embed_html }}
      />
    )
  }

  return (
    <a
      href={creative.click_url}
      target="_blank"
      rel="noopener noreferrer sponsored"
      className={`affiliate-banner ${sizeClass} ${behaviorClass}`}
      style={{ backgroundImage: `url(${creative.image_url})` }}
      title={`${creative.product_name} — ${creative.affiliate_name}`}
    >
      <span className="creative-sponsored-tag">Sponsored</span>
    </a>
  )
}
