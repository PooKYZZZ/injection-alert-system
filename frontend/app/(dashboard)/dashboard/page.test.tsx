import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { DashboardStats } from '@/features/stats/types'

const { useDashboardStats, useAlerts } = vi.hoisted(() => ({
  useDashboardStats: vi.fn(),
  useAlerts: vi.fn(),
}))

const { mockReplace, mockSearchParams } = vi.hoisted(() => ({
  mockReplace: vi.fn(),
  mockSearchParams: new URLSearchParams(),
}))

vi.mock('@/features/stats/queries', () => ({ useDashboardStats }))
vi.mock('@/features/alerts/queries', () => ({ useAlerts }))
vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
}))
vi.mock('next/dynamic', () => ({
  default: () => () => <div data-testid="timeline-chart" />,
}))
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

vi.mock('@/components/dashboard/AttackTypePanel', () => ({
  AttackTypePanel: ({ countsByLabel }: { countsByLabel: Record<string, number> }) => (
    <div data-testid="attack-type-panel">Attack type panel: {countsByLabel['SQL Injection'] ?? 0}</div>
  ),
}))
vi.mock('@/components/dashboard/MLConfidenceBands', () => ({
  MLConfidenceBands: ({ high, critical, medium, low }: { high: number; critical: number; medium: number; low: number }) => (
    <div data-testid="confidence-bands">Confidence bands: {critical}/{high}/{medium}/{low}</div>
  ),
}))
vi.mock('@/components/dashboard/MLEnforcementMap', () => ({
  MLEnforcementMap: ({ nonNormalCounts }: { nonNormalCounts: { critical: number; high: number; medium: number; low: number } }) => (
    <div data-testid="enforcement-map">Enforcement map: {nonNormalCounts.critical}/{nonNormalCounts.high}/{nonNormalCounts.medium}/{nonNormalCounts.low}</div>
  ),
}))
vi.mock('@/components/dashboard/TopSourceIPs', () => ({
  TopSourceIPs: () => <div data-testid="top-source-ips">Top source IPs</div>,
}))
vi.mock('@/components/dashboard/TopTargetedPaths', () => ({
  TopTargetedPaths: () => <div data-testid="top-targeted-paths">Top targeted paths</div>,
}))
vi.mock('@/components/dashboard/RecentAlertsTable', () => ({
  RecentAlertsTable: () => <div data-testid="recent-alerts-table">Recent alerts table</div>,
}))

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
  attack_distribution: { 'SQL Injection': 7 },
  counts_by_confidence_tier: { critical: 1, high: 2, medium: 3, low: 4 },
  non_normal_counts_by_confidence_tier: { critical: 5, high: 6, medium: 7, low: 8 },
  top_source_ips: [],
  top_targeted_paths: [],
}

describe('DashboardPage metric definitions', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    mockReplace.mockReset()
    mockSearchParams.delete('window')
    mockSearchParams.delete('timeRange')
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
    expect(screen.getByRole('list', { name: 'Activity series' })).toBeInTheDocument()
    expect(sixHourButton).toHaveAttribute('aria-pressed', 'true')
    expect(sixHourButton).toHaveClass('focus-visible:outline-none')
    expect(dayButton).toHaveClass('text-text-muted', 'hover:bg-surface-inset', 'hover:text-text-primary')

    await user.click(dayButton)

    expect(sixHourButton).toHaveAttribute('aria-pressed', 'false')
    expect(dayButton).toHaveAttribute('aria-pressed', 'true')
    expect(mockReplace).toHaveBeenCalledWith('/dashboard?window=24h', { scroll: false })
  })

  it('restores a valid timeframe from the URL', () => {
    mockSearchParams.set('window', '7d')

    render(<DashboardPage />)

    expect(screen.getByRole('button', { name: '7d' })).toHaveAttribute('aria-pressed', 'true')
    expect(useDashboardStats).toHaveBeenCalledWith('7d')
  })

  it('uses window-wide stats for distributions instead of the paginated alert preview', () => {
    useAlerts.mockReturnValue({
      data: {
        items: [
          {
            alert_id: 'preview-only',
            prediction: 'SQL Injection',
            confidence_level: 'LOW',
          },
        ],
      },
      isPending: false,
    })

    render(<DashboardPage />)

    expect(screen.getByTestId('attack-type-panel')).toHaveTextContent('Attack type panel: 7')
    expect(screen.getByTestId('confidence-bands')).toHaveTextContent('1/2/3/4')
    expect(screen.getByTestId('enforcement-map')).toHaveTextContent('5/6/7/8')
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
    expect(screen.getByText('Non-Normal alerts')).toBeInTheDocument()
    expect(screen.getByText('Timeline unavailable')).toBeInTheDocument()
    expect(screen.queryByTestId('timeline-chart')).not.toBeInTheDocument()
    expect(screen.queryByTestId('top-source-ips')).not.toBeInTheDocument()
  })

  it('does not present an alerts query failure as an empty result', () => {
    const refetchAlerts = vi.fn()
    useAlerts.mockReturnValue({
      data: undefined,
      isPending: false,
      error: new Error('Alerts API failed'),
      refetch: refetchAlerts,
    })

    render(<DashboardPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('Alert data is unavailable')
    expect(screen.getByTestId('attack-type-panel')).toHaveTextContent('Attack type panel: 7')
    expect(screen.getByTestId('confidence-bands')).toHaveTextContent('1/2/3/4')
    expect(screen.getByTestId('enforcement-map')).toHaveTextContent('5/6/7/8')
    expect(screen.queryByTestId('recent-alerts-table')).not.toBeInTheDocument()
  })

  it('keeps cached dashboard data visible when a refresh fails', () => {
    useDashboardStats.mockReturnValue({
      data: stats,
      isPending: false,
      error: new Error('Stats refresh failed'),
      refetch: vi.fn(),
    })

    render(<DashboardPage />)

    expect(screen.getByText('Non-Normal alerts')).toBeInTheDocument()
    expect(screen.getByTestId('timeline-chart')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/showing the last successful data/i)
  })

  it('keeps cached alert data visible when a refresh fails', () => {
    useAlerts.mockReturnValue({
      data: { items: [{ alert_id: 'cached-alert' }] },
      isPending: false,
      error: new Error('Alerts refresh failed'),
      refetch: vi.fn(),
    })

    render(<DashboardPage />)

    expect(screen.getByTestId('attack-type-panel')).toBeInTheDocument()
    expect(screen.getByTestId('recent-alerts-table')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/showing the last successful data/i)
  })
})
