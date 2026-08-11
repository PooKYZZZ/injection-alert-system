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
    const { container } = render(<RecentAlertsTable alerts={[sampleAlert]} />)

    expect(screen.getByText('Recent alerts')).toBeInTheDocument()
    const viewAllLink = screen.getByRole('link', { name: /View all/i })

    expect(viewAllLink).toHaveAttribute('href', '/alerts')
    expect(viewAllLink).toHaveClass('text-[var(--color-accent-analytic)]')
    expect(screen.getByText('SQL Injection')).toBeInTheDocument()
    expect(screen.queryAllByRole('checkbox')).toHaveLength(0)

    const tableCard = container.firstElementChild
    expect(tableCard).not.toBeNull()
    expect(tableCard).toHaveClass('bg-surface-card')
  })

  it('keeps the empty table state understandable and horizontally contained', () => {
    const { container } = render(<RecentAlertsTable alerts={[]} />)

    expect(screen.getByRole('region', { name: 'Recent alerts table' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Recent alerts' })).toBeInTheDocument()
    expect(screen.getByText('No recent alerts in this window.')).toBeInTheDocument()
    expect(container.querySelector('[data-testid="recent-alerts-scroll"]')).not.toBeNull()
  })
})
