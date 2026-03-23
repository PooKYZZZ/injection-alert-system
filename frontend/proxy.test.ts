import { describe, expect, it, vi } from 'vitest'

const authMock = vi.fn()

vi.mock('next-auth', () => ({
  default: vi.fn(() => ({
    auth: authMock,
  })),
}))

vi.mock('./auth.config', () => ({
  authConfig: {},
}))

describe('proxy middleware', () => {
  it('adds the shared security headers to proxy-generated responses', async () => {
    authMock.mockReturnValueOnce(async () => new Response(null, { status: 302 }))

    const { default: middleware } = await import('./proxy')

    const response = await middleware({} as never, {} as never)

    expect(response.headers.get('X-Content-Type-Options')).toBe('nosniff')
    expect(response.headers.get('X-Frame-Options')).toBe('DENY')
    expect(response.headers.get('Referrer-Policy')).toBe(
      'strict-origin-when-cross-origin'
    )
    expect(response.headers.get('Permissions-Policy')).toBe(
      'camera=(), microphone=(), geolocation=(), payment=()'
    )
  })
})
