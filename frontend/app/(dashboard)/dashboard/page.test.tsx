import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { DashboardStats } from '@/features/stats/types'

const { useDashboardStats, useAlerts } = vi.hoisted(() => ({
  useDashboardStats: vi.fn(),
  useAlerts: vi.fn(),
}))

vi.mock('@/features/stats/queries', () => ({ useDashboardStats }))
vi.mock('@/features/alerts/queries', () => ({ useAlerts }))
vi.mock('next/dynamic', () => ({ default: () => () => null }))
vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: { div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div> },
}))

vi.mock('@/components/dashboard/StatCard', () => ({
  StatCard: ({ label, value, secondary }: { label: string; value: string | number; secondary?: string }) => (
    <div>
      <span>{label}</span>
      <span>{value}</span>
      {secondary ? <span>{secondary}</span> : null}
    </div>
  ),
}))

vi.mock('@/components/dashboard/AttackTypePanel', () => ({ AttackTypePanel: () => null }))
vi.mock('@/components/dashboard/MLConfidenceBands', () => ({ MLConfidenceBands: () => null }))
vi.mock('@/components/dashboard/MLEnforcementMap', () => ({ MLEnforcementMap: () => null }))
vi.mock('@/components/dashboard/TopSourceIPs', () => ({ TopSourceIPs: () => null }))
vi.mock('@/components/dashboard/TopTargetedPaths', () => ({ TopTargetedPaths: () => null }))
vi.mock('@/components/dashboard/RecentAlertsTable', () => ({ RecentAlertsTable: () => null }))

import DashboardPage from './page'

const stats: DashboardStats = {
  actionable_alerts: 1,
  total_requests: 10,
  avg_inference_latency_ms: 1,
  blocked_count: 1,
  allowed_count: 8,
  throttled_count: 1,
  avg_confidence: 0.9,
  false_positive_rate: 10,
  false_positive_count: 1,
  high_alert_count: 1,
  prev_high_alert_count: null,
  prev_total_requests: null,
  prev_blocked_count: null,
  prev_allowed_count: null,
  prev_throttled_count: null,
  activity_buckets: [],
  attack_distribution: {},
  top_source_ips: [],
  top_targeted_paths: [],
}

describe('DashboardPage metric definitions', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    useDashboardStats.mockReturnValue({ data: stats, isPending: false })
    useAlerts.mockReturnValue({ data: { items: [] }, isPending: false })
  })

  it('labels the traffic false-positive field as an operational proxy', () => {
    render(<DashboardPage />)

    expect(screen.getByText('Allowed non-Normal prediction rate (proxy)')).toBeInTheDocument()
    expect(screen.getByText('Not ground-truth FPR')).toBeInTheDocument()
  })

  it('exposes the time-window control as an accessible pressed-button group', async () => {
    const user = userEvent.setup()
    render(<DashboardPage />)

    const group = screen.getByRole('group', { name: 'Timeline window' })
    const sixHourButton = screen.getByRole('button', { name: '6h' })
    const dayButton = screen.getByRole('button', { name: '24h' })

    expect(group).toBeInTheDocument()
    expect(sixHourButton).toHaveAttribute('aria-pressed', 'true')
    expect(sixHourButton).toHaveClass('focus-visible:outline-none')

    await user.click(dayButton)

    expect(sixHourButton).toHaveAttribute('aria-pressed', 'false')
    expect(dayButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('surfaces dashboard query errors without removing the dashboard shell', () => {
    const refetchStats = vi.fn()
    useDashboardStats.mockReturnValue({
      data: undefined,
      isPending: false,
      error: new Error('Stats API failed'),
      refetch: refetchStats,
    })

    render(<DashboardPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('Dashboard metrics are unavailable')
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    expect(screen.getByText('High-confidence alerts')).toBeInTheDocument()
  })
})
