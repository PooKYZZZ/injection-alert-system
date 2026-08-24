import { describe, expect, it } from 'vitest'

import {
  formatAlertDateTime,
  formatConfidenceLabel,
  formatConfidencePercent,
  formatRelativeTime,
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

  it('does not describe future timestamps as already elapsed', () => {
    expect(formatRelativeTime('2026-08-24T14:07:17Z', Date.parse('2026-08-24T14:06:47Z'))).toBe(
      'in 30s'
    )
  })

  it('keeps high probabilities below 100 percent when rounding allows it', () => {
    expect(formatConfidencePercent(0.9998)).toBe('99.98%')
    expect(formatConfidenceLabel(0.9998, 'CRITICAL')).toBe(
      '99.98% (Critical confidence)'
    )
  })
})
