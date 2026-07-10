import { describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import {
  buildTrustedActionUrl,
  digestOpaqueToken,
  generateOpaqueToken,
} from './account-tokens'

describe('account action tokens', () => {
  it('generates at least 32 random bytes and stores only a digest', () => {
    const token = generateOpaqueToken()
    const digest = digestOpaqueToken(token)

    expect(token.length).toBeGreaterThanOrEqual(43)
    expect(digest).toMatch(/^[a-f0-9]{64}$/)
    expect(digest).not.toContain(token)
  })

  it('builds links only from a trusted configured origin', () => {
    expect(
      buildTrustedActionUrl(
        'https://dashboard.example.test',
        '/setup-password',
        'opaque-token'
      )
    ).toBe(
      'https://dashboard.example.test/setup-password?token=opaque-token'
    )
    expect(() =>
      buildTrustedActionUrl('https://dashboard.example.test.evil/path', '/', 'x')
    ).toThrow()
    expect(() =>
      buildTrustedActionUrl('http://dashboard.example.test', '/', 'x')
    ).toThrow()
    expect(
      buildTrustedActionUrl('http://localhost:3000', '/verify-email', 'x')
    ).toBe('http://localhost:3000/verify-email?token=x')
  })
})
