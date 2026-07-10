import { describe, expect, it } from 'vitest'

import nextConfig, { buildContentSecurityPolicy } from './next.config'

describe('buildContentSecurityPolicy', () => {
  it('keeps inline scripts enabled in production without eval', () => {
    const csp = buildContentSecurityPolicy('production')

    expect(csp).toContain("default-src 'self'")
    expect(csp).toContain("script-src 'self' 'unsafe-inline'")
    expect(csp).not.toContain("'unsafe-eval'")
  })

  it('keeps relaxed script directives in development', () => {
    const csp = buildContentSecurityPolicy('development')

    expect(csp).toContain("script-src 'self' 'unsafe-eval' 'unsafe-inline'")
  })

  it('adds scanner-safe no-store headers to setup and verification pages', async () => {
    const headers = await nextConfig.headers!()
    const globalIndex = headers.findIndex((entry) => entry.source === '/(.*)')
    for (const source of ['/setup-password', '/verify-email']) {
      const specificIndex = headers.findIndex((entry) => entry.source === source)
      const rule = headers[specificIndex]
      expect(specificIndex).toBeGreaterThan(globalIndex)
      expect(rule?.headers).toEqual(
        expect.arrayContaining([
          { key: 'Referrer-Policy', value: 'no-referrer' },
          { key: 'Cache-Control', value: 'no-store' },
          { key: 'X-Robots-Tag', value: 'noindex, nofollow' },
        ])
      )
    }
  })
})
