import { describe, expect, it } from 'vitest'

import { buildTrafficHistoryHref } from './traffic-history-route'

describe('buildTrafficHistoryHref', () => {
  it('keeps alert detail links and active list filters during the legacy route redirect', () => {
    expect(
      buildTrafficHistoryHref({
        alert_id: '42',
        include_normal: 'true',
        page: '3',
        search: 'SQL Injection',
      })
    ).toBe(
      '/traffic-history?alert_id=42&include_normal=true&page=3&search=SQL+Injection'
    )
  })

  it('preserves repeated query parameters and omits undefined values', () => {
    expect(
      buildTrafficHistoryHref({ tag: ['waf', 'ml'], ignored: undefined })
    ).toBe('/traffic-history?tag=waf&tag=ml')
  })

  it('uses the canonical route when no query parameters are present', () => {
    expect(buildTrafficHistoryHref({})).toBe('/traffic-history')
  })
})
