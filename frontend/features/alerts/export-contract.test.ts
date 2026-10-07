import { describe, expect, it } from 'vitest'

import { TrafficHistoryExportRequestSchema } from './export-contract'

const baseRequest = {
  start_date: '2024-02-29',
  end_date: '2024-02-29',
  timezone: 'Asia/Singapore',
}

describe('TrafficHistoryExportRequestSchema', () => {
  it('accepts leap-day ranges up to 31 inclusive calendar days', () => {
    expect(
      TrafficHistoryExportRequestSchema.safeParse({
        ...baseRequest,
        start_date: '2024-02-01',
        end_date: '2024-03-02',
      }).success
    ).toBe(true)
  })

  it('rejects reversed and over-limit ranges', () => {
    expect(
      TrafficHistoryExportRequestSchema.safeParse({
        ...baseRequest,
        start_date: '2024-03-01',
        end_date: '2024-02-29',
      }).success
    ).toBe(false)
    expect(
      TrafficHistoryExportRequestSchema.safeParse({
        ...baseRequest,
        start_date: '2024-02-01',
        end_date: '2024-03-03',
      }).success
    ).toBe(false)
  })

  it('rejects conflicting confidence aliases and unknown sensitive fields', () => {
    expect(
      TrafficHistoryExportRequestSchema.safeParse({
        ...baseRequest,
        severity: 'HIGH',
        confidence_tier: 'LOW',
      }).success
    ).toBe(false)
    expect(
      TrafficHistoryExportRequestSchema.safeParse({
        ...baseRequest,
        request_body: 'must not enter the export contract',
      }).success
    ).toBe(false)
  })
})
