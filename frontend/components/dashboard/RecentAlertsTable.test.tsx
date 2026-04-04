import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { RecentAlertsTable } from './RecentAlertsTable'
import type { Alert } from '@/features/alerts/types'

const sampleAlert: Alert = {
  alert_id: 'alert-1',
  timestamp: '2026-03-17T15:30:00Z',
  source_ip: '192.168.0.10',
  request_path: '/search',
  request_method: 'GET',
  payload_snippet: "' OR 1=1 --",
  prediction: 'SQL Injection',
  confidence: 0.91,
  confidence_level: 'HIGH',
  action_taken: 'BLOCKED',
  crs_score: 8.5,
  crs_rule_ids: ['942100'],
}

afterEach(() => {
  cleanup()
})

describe('RecentAlertsTable', () => {
  it('renders a read-only preview without selection controls', () => {
    render(<RecentAlertsTable alerts={[sampleAlert]} />)

    expect(screen.getByText('Recent alerts')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View all/i })).toHaveAttribute('href', '/alerts')
    expect(screen.getByText('SQL Injection')).toBeInTheDocument()
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
  })
})