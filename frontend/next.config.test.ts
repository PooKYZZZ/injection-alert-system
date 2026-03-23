import { describe, expect, it } from 'vitest'

import { buildContentSecurityPolicy } from './next.config'

describe('buildContentSecurityPolicy', () => {
  it('omits unsafe script directives in production', () => {
    const csp = buildContentSecurityPolicy('production')

    expect(csp).toContain("default-src 'self'")
    expect(csp).toContain("script-src 'self'")
    expect(csp).not.toContain("script-src 'self' 'unsafe-eval' 'unsafe-inline'")
    expect(csp).not.toContain("'unsafe-eval'")
  })

  it('keeps relaxed script directives in development', () => {
    const csp = buildContentSecurityPolicy('development')

    expect(csp).toContain("script-src 'self' 'unsafe-eval' 'unsafe-inline'")
  })
})
