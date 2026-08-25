import { describe, expect, it } from 'vitest'

import {
  formatAlertDateTime,
  formatConfidenceLabel,
  formatCompactConfidencePercent,
  formatConfidencePercent,
  formatRelativeTime,
  formatStableDateTime,
  parseApiTimestamp,
} from './date-time'

describe('API date and confidence formatting', () => {
  it('treats a legacy timezone-naive API timestamp as UTC', () => {
    expect(parseApiTimestamp('2026-08-24T14:06:47')).toEqual(
      new Date('2026-08-24T14:06:47Z')
    )
  })

  it('rejects malformed timestamps instead of rendering a misleading date', () => {
    expect(parseApiTimestamp('not-a-timestamp')).toBeNull()
    expect(parseApiTimestamp(null)).toBeNull()
    expect(formatAlertDateTime('not-a-timestamp')).toBe('Unknown timestamp')
  })

  it('includes calendar context when formatting an alert timestamp', () => {
    expect(
      formatAlertDateTime('2026-08-24T14:06:47Z', { timeZone: 'UTC' })
    ).toBe('Aug 24, 2026, 2:06 PM')
  })

  it('formats administrative timestamps deterministically in UTC', () => {
    expect(formatStableDateTime('2026-08-24T14:06:47Z')).toBe(
      'Aug 24, 2026, 2:06 PM UTC'
    )
    expect(formatStableDateTime('not-a-timestamp')).toBe('Unknown timestamp')
  })

  it('does not describe future timestamps as already elapsed', () => {
    expect(formatRelativeTime('2026-08-24T14:07:17Z', Date.parse('2026-08-24T14:06:47Z'))).toBe(
      'in 30s'
    )
  })

  it.each([360, 364])('does not render zero years at the 12-month boundary (%i days)', (days) => {
    const now = Date.parse('2026-08-24T14:06:47Z')
    const timestamp = new Date(now - days * 24 * 60 * 60 * 1000).toISOString()

    expect(formatRelativeTime(timestamp, now)).toBe('12 months ago')
    expect(formatRelativeTime(new Date(now + days * 24 * 60 * 60 * 1000).toISOString(), now)).toBe(
      'in 12 months'
    )
  })

  it('starts the year unit at one year instead of zero', () => {
    const now = Date.parse('2026-08-24T14:06:47Z')
    const timestamp = new Date(now - 365 * 24 * 60 * 60 * 1000).toISOString()

    expect(formatRelativeTime(timestamp, now)).toBe('1 year ago')
  })

  it('keeps source precision available while offering compact operator display', () => {
    expect(formatConfidencePercent(0.519262)).toBe('51.9262%')
    expect(formatCompactConfidencePercent(0.519262)).toBe('51.9%')
    expect(formatConfidencePercent(0.9998)).toBe('99.98%')
    expect(formatConfidenceLabel(0.9998, 'CRITICAL')).toBe(
      '99.98% (Critical confidence)'
    )
    expect(formatCompactConfidencePercent(0.9998)).toBe('99.98%')
  })
})
