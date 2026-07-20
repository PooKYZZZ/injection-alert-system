import { describe, expect, it } from 'vitest'
import { parseAlertDeepLink, removeAlertDeepLink } from './deepLink'

describe('alert deep links', () => {
  it('accepts exactly one positive decimal alert id', () => {
    expect(parseAlertDeepLink(new URLSearchParams('alert_id=10591'))).toEqual({
      kind: 'valid',
      id: '10591',
    })
  })

  it.each([
    'alert_id=',
    'alert_id=0',
    'alert_id=-1',
    'alert_id=1.5',
    'alert_id=abc',
    'alert_id=10591&alert_id=10592',
  ])('rejects invalid alert_id query: %s', (query) => {
    expect(parseAlertDeepLink(new URLSearchParams(query))).toEqual({ kind: 'invalid' })
  })

  it('returns no intent when alert_id is absent', () => {
    expect(parseAlertDeepLink(new URLSearchParams())).toEqual({ kind: 'none' })
  })

  it('removes only alert_id while preserving other navigation state', () => {
    expect(removeAlertDeepLink('/alerts?confidence_tier=HIGH&page=2&alert_id=10591')).toBe(
      '/alerts?confidence_tier=HIGH&page=2'
    )
  })
})
