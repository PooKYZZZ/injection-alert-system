import { describe, expect, it } from 'vitest'
import { normalizeAlertSearchParams, DEFAULT_ALERT_FILTERS, toAlertQueryString } from './searchParams'

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

describe('toAlertQueryString', () => {
  it('serializes confidence_level array as repeated params', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      confidence_level: ['HIGH', 'MEDIUM'],
    })
    expect(result).toContain('confidence_level=HIGH')
    expect(result).toContain('confidence_level=MEDIUM')
  })

  it('omits null and undefined fields', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      action: undefined,
      triage_status: undefined,
      prediction: undefined,
      source_ip: undefined,
      search: undefined,
      window: undefined,
    })
    expect(result).not.toContain('action=')
    expect(result).not.toContain('triage_status=')
    expect(result).not.toContain('prediction=')
    expect(result).not.toContain('source_ip=')
    expect(result).not.toContain('search=')
    expect(result).not.toContain('window=')
  })

  it('maps window key correctly', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      window: '24h',
    })
    expect(result).toContain('window=24h')
  })

  it('serializes sort params', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      sort_by: 'confidence',
      sort_dir: 'asc',
    })
    expect(result).toContain('sort_by=confidence')
    expect(result).toContain('sort_dir=asc')
  })

  it('serializes page and pageSize', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      page: 3,
      pageSize: 50,
    })
    expect(result).toContain('page=3')
    expect(result).toContain('pageSize=50')
  })

  it('handles empty filters with only defaults', () => {
    const result = toAlertQueryString(DEFAULT_ALERT_FILTERS)
    expect(result).toContain('page=1')
    expect(result).toContain('pageSize=20')
    expect(result).toContain('sort_by=timestamp')
    expect(result).toContain('sort_dir=desc')
  })

  it('serializes single confidence_level value', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      confidence_level: ['HIGH'],
    })
    expect(result).toContain('confidence_level=HIGH')
  })

  it('serializes triage_status filter', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      triage_status: 'in_review',
    })
    expect(result).toContain('triage_status=in_review')
  })

  it('serializes prediction filter', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      prediction: 'SQL Injection',
    })
    expect(result).toContain('prediction=SQL+Injection')
  })

  it('serializes source_ip filter', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      source_ip: '192.168.1.1',
    })
    expect(result).toContain('source_ip=192.168.1.1')
  })

  it('serializes search filter', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      search: 'test query',
    })
    expect(result).toContain('search=test+query')
  })

  it('handles all filters combined', () => {
    const result = toAlertQueryString({
      page: 2,
      pageSize: 10,
      severity: 'HIGH',
      confidence_level: ['HIGH', 'LOW'],
      action: 'BLOCKED',
      triage_status: 'new',
      prediction: 'SQL Injection',
      source_ip: '10.0.0.1',
      search: 'admin',
      window: '6h',
      sort_by: 'confidence',
      sort_dir: 'asc',
    })
    expect(result).toContain('page=2')
    expect(result).toContain('pageSize=10')
    expect(result).toContain('confidence_level=HIGH')
    expect(result).toContain('confidence_level=LOW')
    expect(result).toContain('action=BLOCKED')
    expect(result).toContain('triage_status=new')
    expect(result).toContain('source_ip=10.0.0.1')
    expect(result).toContain('window=6h')
    expect(result).toContain('sort_by=confidence')
    expect(result).toContain('sort_dir=asc')
  })
})
