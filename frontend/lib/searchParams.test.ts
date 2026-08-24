import { describe, expect, it } from 'vitest'
import {
  normalizeAlertSearchParams,
  DEFAULT_ALERT_FILTERS,
  getCurrentSearchParams,
  toAlertQueryString,
} from './searchParams'

describe('getCurrentSearchParams', () => {
  it('reads the browser URL at event time', () => {
    window.history.replaceState({}, '', '/alerts?window=7d&page=2')

    expect(getCurrentSearchParams(new URLSearchParams('window=1h')).toString()).toBe(
      'window=7d&page=2'
    )
  })
})

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

  it('reads legacy severity filter into preferred confidence_tier state', () => {
    const result = normalizeAlertSearchParams({
      severity: 'HIGH',
    })
    expect(result.confidence_tier).toBe('HIGH')
    expect(result.severity).toBe('HIGH')
  })

  it('accepts CRITICAL confidence_tier and severity filters', () => {
    const preferred = normalizeAlertSearchParams({
      confidence_tier: 'CRITICAL',
    })
    expect(preferred.confidence_tier).toBe('CRITICAL')

    const legacy = normalizeAlertSearchParams({
      severity: 'CRITICAL',
    })
    expect(legacy.severity).toBe('CRITICAL')
  })

  it('preserves conflicting legacy and preferred confidence-tier params for backend validation', () => {
    const result = normalizeAlertSearchParams({
      severity: 'LOW',
      confidence_tier: 'HIGH',
    })
    expect(result.severity).toBe('LOW')
    expect(result.confidence_tier).toBe('HIGH')
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
      confidence_tier: 'CRITICAL',
      confidence_level: ['CRITICAL', 'HIGH', 'LOW'],
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
    expect(result).toContain('confidence_tier=CRITICAL')
    expect(result).toContain('confidence_level=CRITICAL')
    expect(result).toContain('confidence_level=HIGH')
    expect(result).toContain('confidence_level=LOW')
    expect(result).toContain('action=BLOCKED')
    expect(result).toContain('triage_status=new')
    expect(result).toContain('source_ip=10.0.0.1')
    expect(result).toContain('window=6h')
    expect(result).toContain('sort_by=confidence')
    expect(result).toContain('sort_dir=asc')
  })

  it('serializes both confidence_tier and legacy severity when both are present', () => {
    const result = toAlertQueryString({
      ...DEFAULT_ALERT_FILTERS,
      confidence_tier: 'CRITICAL',
      severity: 'CRITICAL',
    })

    expect(result).toContain('confidence_tier=CRITICAL')
    expect(result).toContain('severity=CRITICAL')
  })

  it('uses a canonical key order for equivalent alert query keys', () => {
    const first = normalizeAlertSearchParams({
      window: '7d',
      page: '2',
      search: 'sql',
      confidence_level: ['HIGH', 'LOW'],
      sort_dir: 'asc',
    })
    const second = normalizeAlertSearchParams({
      sort_dir: 'asc',
      confidence_level: ['HIGH', 'LOW'],
      search: 'sql',
      page: '2',
      window: '7d',
    })

    expect(toAlertQueryString(first)).toBe(toAlertQueryString(second))
  })
})
