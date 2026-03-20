import { describe, expect, it } from 'vitest'
import { normalizeAlertSearchParams, DEFAULT_ALERT_FILTERS } from './searchParams'

describe('normalizeAlertSearchParams', () => {
  it('returns default filters for empty params', () => {
    const result = normalizeAlertSearchParams({})
    expect(result).toEqual(DEFAULT_ALERT_FILTERS)
  })

  it('normalizes single confidence_level string to array', () => {
    const result = normalizeAlertSearchParams({
      confidence_level: 'HIGH',
    })
    expect(result.confidence_level).toEqual(['HIGH'])
  })

  it('normalizes multiple confidence_level values to deduplicated array', () => {
    const result = normalizeAlertSearchParams({
      confidence_level: ['HIGH', 'MEDIUM', 'HIGH'],
    })
    expect(result.confidence_level).toEqual(['HIGH', 'MEDIUM'])
  })

  it('preserves other params as strings', () => {
    const result = normalizeAlertSearchParams({
      page: '2',
      pageSize: '50',
      sort_by: 'timestamp',
      sort_dir: 'asc',
    })
    expect(result.page).toBe(2)
    expect(result.pageSize).toBe(50)
    expect(result.sort_by).toBe('timestamp')
    expect(result.sort_dir).toBe('asc')
  })

  it('handles mixed confidence_level formats', () => {
    const result = normalizeAlertSearchParams({
      confidence_level: 'HIGH',
    })
    expect(result.confidence_level).toEqual(['HIGH'])
  })

  it('uses default for invalid params', () => {
    const result = normalizeAlertSearchParams({
      page: 'invalid',
      unknown: 'value',
    })
    // page should fall back to default since it's invalid
    expect(result.page).toBe(DEFAULT_ALERT_FILTERS.page)
  })
})
