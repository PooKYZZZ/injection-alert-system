import { describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))
vi.mock('next/headers', () => ({ cookies: vi.fn() }))

import {
  PREAUTH_COOKIE_NAME,
  digestPreAuthHandle,
  generatePreAuthHandle,
  readPreAuthHandle,
} from './preauth'

describe('pre-auth handle boundary', () => {
  it('uses an opaque random handle and a one-way digest', () => {
    const handle = generatePreAuthHandle()
    expect(handle).toMatch(/^[A-Za-z0-9_-]{40,128}$/)
    expect(digestPreAuthHandle(handle)).toMatch(/^[a-f0-9]{64}$/)
    expect(digestPreAuthHandle(handle)).not.toContain(handle)
  })

  it('reads only the dedicated cookie value from a request', () => {
    const handle = generatePreAuthHandle()
    const request = new Request('http://localhost/mfa/verify', {
      headers: { cookie: `${PREAUTH_COOKIE_NAME}=${handle}; other=value` },
    })
    expect(readPreAuthHandle(request)).toBe(handle)
    expect(readPreAuthHandle(new Request('http://localhost'))).toBeNull()
  })
})
