import { describe, expect, it } from 'vitest'
import { isPublicProjectHost } from './public-site-host'

describe('isPublicProjectHost', () => {
  it.each([
    'cybertracesystems.com',
    'CYBERTRACESYSTEMS.COM',
    'cybertracesystems.com:443',
    'cybertracesystems.com.:3000',
    'cybertracesystems.com, proxy.internal',
  ])('accepts the apex host in %s', (host) => {
    expect(isPublicProjectHost(host)).toBe(true)
  })

  it.each([
    'www.cybertracesystems.com',
    'app.cybertracesystems.com',
    'target.cybertracesystems.com',
    'cybertracesystems.com.example.org',
    '',
    null,
    undefined,
    'not a host',
  ])('does not accept %s', (host) => {
    expect(isPublicProjectHost(host)).toBe(false)
  })
})