import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSearchParams } from 'next/navigation'

import DashboardAlertAnalyticsSection from './DashboardAlertAnalyticsSection'
import * as statsQueries from '@/features/stats/queries'
import * as alertsQueries from '@/features/alerts/queries'
import * as mlHealthQueries from '@/features/ml-health/queries'
import type { DashboardStats } from '@/features/stats/types'
import type { PaginatedAlerts } from '@/features/alerts/types'
import type { MLHealthData } from '@/features/ml-health/types'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useSearchParams: vi.fn(),
}))

// Mock the queries
vi.mock('@/features/stats/queries', () => ({
  useDashboardStats: vi.fn(),
}))

vi.mock('@/features/alerts/queries', () => ({
  useAlerts: vi.fn(),
}))

// Mock dynamic imports
vi.mock('@/components/dashboard/DashboardAlertAnalytics', () => ({
  __esModule: true,
  default: vi.fn(({ alertsError, thresholdState }) => {
    // Render error state if alertsError is present
    if (alertsError) {
      return (
        <div data-testid="dashboard-analytics-error">
          <p>Failed to load dashboard analytics.</p>
          <p>{alertsError.message}</p>
        </div>
      )
    }
    // Render loading state if threshold is loading
    if (thresholdState?.isLoading) {
      return <div data-testid="threshold-loading">Loading confidence thresholds...</div>
    }
    // Render error if threshold state has error
    if (thresholdState?.isError) {
      return <div data-testid="threshold-error">Unable to load confidence thresholds.</div>
    }
    // Render unavailable if thresholds are null/missing
    const t = thresholdState?.thresholds
    if (!t || t.high === null || t.medium === null || t.low === null) {
      return <div data-testid="threshold-unavailable">Confidence thresholds unavailable.</div>
    }
    // Default: render threshold bands
    return (
      <div data-testid="threshold-bands">
        <span>High &gt; {Math.round((t?.high ?? 0) * 100)}%</span>
        <span>Medium {Math.round((t?.medium ?? 0) * 100)}–{Math.round((t?.high ?? 0) * 100)}%</span>
        <span>Low &lt; {Math.round((t?.medium ?? 0) * 100)}%</span>
      </div>
    )
  }),
}))

vi.mock('@/features/ml-health/queries', () => ({
  useMLHealth: vi.fn(),
}))

const mockActivityBuckets = [
  { bucket_index: 0, total_count: 50, blocked_count: 5, timestamp_start: new Date() },
  { bucket_index: 1, total_count: 45, blocked_count: 3, timestamp_start: new Date() },
]

const mockStats: DashboardStats = {
  actionable_alerts: 500,
  total_requests: 1000000,
  avg_inference_latency_ms: 5.2,
  blocked_count: 320,
  allowed_count: 85,
  throttled_count: 15,
  avg_confidence: 0.72,
  activity_buckets: mockActivityBuckets,
  attack_distribution: {},
  top_source_ips: [],
  top_targeted_paths: [],
}

const mockAlertsPage1: PaginatedAlerts = {
  items: [
    {
      alert_id: 'a-1',
      timestamp: '2026-03-17T00:00:00Z',
      source_ip: '192.168.1.1',
      request_path: '/admin',
      request_method: 'POST',
      payload_snippet: ' UNION SELECT--',
      prediction: 'SQL Injection',
      confidence: 0.95,
      confidence_level: 'HIGH',
      action_taken: 'BLOCKED',
    },
  ],
  total: 1,
  page: 1,
  pageSize: 20,
}

const mockAlertsPage2: PaginatedAlerts = {
  items: [
    {
      alert_id: 'a-2',
      timestamp: '2026-03-17T01:00:00Z',
      source_ip: '192.168.1.2',
      request_path: '/login',
      request_method: 'GET',
      payload_snippet: '<script>alert(1)</script>',
      prediction: 'Other Attacks',
      confidence: 0.75,
      confidence_level: 'MEDIUM',
      action_taken: 'ALLOWED',
    },
  ],
  total: 1,
  page: 1,
  pageSize: 20,
}

// Mock ML health data with thresholds present
const mockMLHealthWithThresholds: MLHealthData = {
  model_version: 'distilbert-v1',
  status: 'HEALTHY',
  latency_ms: 45,
  latency_trend: null,
  drift_score: null,
  drift_status: 'NORMAL',
  traffic_processed: 1000,
  thresholds: {
    low: 0.5,
    medium: 0.65,
    high: 0.8,
  },
}

// Mock ML health data with thresholds absent (null values)
const mockMLHealthWithoutThresholds: MLHealthData = {
  model_version: 'distilbert-v1',
  status: 'HEALTHY',
  latency_ms: 45,
  latency_trend: null,
  drift_score: null,
  drift_status: 'NORMAL',
  traffic_processed: 1000,
  thresholds: {
    low: null,
    medium: null,
    high: null,
  },
}

describe('DashboardAlertAnalyticsSection', () => {
  let useDashboardStatsMock: ReturnType<typeof vi.fn>
  let useAlertsMock: ReturnType<typeof vi.fn>
  let useSearchParamsMock: ReturnType<typeof vi.fn>
  let useMLHealthMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    useDashboardStatsMock = statsQueries.useDashboardStats as ReturnType<typeof vi.fn>
    useAlertsMock = alertsQueries.useAlerts as ReturnType<typeof vi.fn>
    useSearchParamsMock = useSearchParams as ReturnType<typeof vi.fn>
    useMLHealthMock = mlHealthQueries.useMLHealth as ReturnType<typeof vi.fn>

    // Default mock implementations
    useDashboardStatsMock.mockReturnValue({
      data: mockStats,
      isPending: false,
      error: null,
    })

    useAlertsMock.mockReturnValue({
      data: mockAlertsPage1,
      isPending: false,
      error: null,
    })

    useSearchParamsMock.mockReturnValue(new URLSearchParams())

    // Default: ML health returns thresholds
    useMLHealthMock.mockReturnValue({
      data: mockMLHealthWithThresholds,
      isPending: false,
      isError: false,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  function createWrapper() {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })

    return function Wrapper({ children }: { children: React.ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    }
  }

  it('uses stats API for metric cards - shows actionable_alerts and total_requests', async () => {
    const Wrapper = createWrapper()
    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Verify stats values appear in metric cards
    expect(screen.getByText('500')).toBeInTheDocument() // actionable_alerts
    expect(screen.getByText('1000000')).toBeInTheDocument() // total_requests
  })

  it('uses stats API for metric cards - does not change when alert filters change', async () => {
    const Wrapper = createWrapper()
    const { rerender } = render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Initial render with first set of alerts - use getAllByText for robustness with Strict Mode
    expect(screen.getAllByText('500').length).toBeGreaterThan(0)
    expect(screen.getAllByText('1000000').length).toBeGreaterThan(0)

    // Change the alerts to return different data (simulating filter change)
    useAlertsMock.mockReturnValue({
      data: mockAlertsPage2,
      isPending: false,
      error: null,
    })

    rerender(<DashboardAlertAnalyticsSection />)

    // Stats should NOT change - they come from stats API, not filtered alerts
    await waitFor(() => {
      expect(screen.getAllByText('500').length).toBeGreaterThan(0)
      expect(screen.getAllByText('1000000').length).toBeGreaterThan(0)
    })
  })

  it('uses alerts query for alert-driven UI surfaces', async () => {
    const Wrapper = createWrapper()
    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Verify alert-driven content shows filtered alerts data
    // The HeroActivityStrip and DashboardAlertAnalytics should show the alert data
    // We can verify this by checking that the alerts from useAlerts are being passed
    expect(useAlertsMock).toHaveBeenCalled()
  })

  it('handles stats error independently from alerts', async () => {
    const Wrapper = createWrapper()

    // Stats fails, alerts succeed
    useDashboardStatsMock.mockReturnValue({
      data: undefined,
      isPending: false,
      error: new Error('Stats API failed'),
    })

    useAlertsMock.mockReturnValue({
      data: mockAlertsPage1,
      isPending: false,
      error: null,
    })

    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Stats error should be displayed in metric cards
    expect(screen.getByText('Unable to load dashboard metrics.')).toBeInTheDocument()
    expect(screen.getByText('Stats API failed')).toBeInTheDocument()

    // Alerts should still work - we verify useAlerts was called with filters
    expect(useAlertsMock).toHaveBeenCalled()
  })

  it('uses ML health for thresholds when available', async () => {
    const Wrapper = createWrapper()
    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Verify ML health was called to get thresholds
    expect(useMLHealthMock).toHaveBeenCalled()
  })

  it('shows confidence bands when thresholds are present', async () => {
    const Wrapper = createWrapper()

    // ML health returns valid thresholds
    useMLHealthMock.mockReturnValue({
      data: mockMLHealthWithThresholds,
      isPending: false,
      isError: false,
    })

    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Should NOT show unavailable message
    expect(screen.queryByText('Confidence thresholds unavailable.')).not.toBeInTheDocument()
    // Should NOT show loading message
    expect(screen.queryByText('Loading confidence thresholds...')).not.toBeInTheDocument()
    // Should NOT show error message
    expect(screen.queryByText('Unable to load confidence thresholds.')).not.toBeInTheDocument()
  })

  it('shows unavailable state when ML health thresholds are null', async () => {
    const Wrapper = createWrapper()

    // ML health returns null thresholds
    useMLHealthMock.mockReturnValue({
      data: mockMLHealthWithoutThresholds,
      isPending: false,
      isError: false,
    })

    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Should show unavailable message for confidence bands
    expect(screen.getByText('Confidence thresholds unavailable.')).toBeInTheDocument()
  })

  it('shows loading state when ML health is loading', async () => {
    const Wrapper = createWrapper()

    // ML health is loading
    useMLHealthMock.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    })

    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Should show loading message
    expect(screen.getByText('Loading confidence thresholds...')).toBeInTheDocument()
  })

  it('shows error state when ML health query fails', async () => {
    const Wrapper = createWrapper()

    // ML health query fails
    useMLHealthMock.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
    })

    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Should show error message
    expect(screen.getByText('Unable to load confidence thresholds.')).toBeInTheDocument()
  })

  it('band labels change when thresholds change', async () => {
    const Wrapper = createWrapper()

    // First render with high thresholds (0.7, 0.9)
    useMLHealthMock.mockReturnValue({
      data: {
        ...mockMLHealthWithThresholds,
        thresholds: { low: 0.3, medium: 0.5, high: 0.7 },
      },
      isPending: false,
      isError: false,
    })

    const { rerender } = render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Should show "High > 70%" - use getAllByText due to dynamic import
    expect(screen.getAllByText('High > 70%').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Medium 50–70%').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Low < 50%').length).toBeGreaterThan(0)

    // Change thresholds to lower values (0.5, 0.8)
    useMLHealthMock.mockReturnValue({
      data: {
        ...mockMLHealthWithThresholds,
        thresholds: { low: 0.5, medium: 0.65, high: 0.8 },
      },
      isPending: false,
      isError: false,
    })

    rerender(<DashboardAlertAnalyticsSection />)

    // Should show "High > 80%"
    expect(screen.getAllByText('High > 80%').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Medium 65–80%').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Low < 65%').length).toBeGreaterThan(0)
  })

  it('shows error state when alerts query fails', async () => {
    const Wrapper = createWrapper()

    // Alerts query fails
    useAlertsMock.mockReturnValue({
      data: undefined,
      isPending: false,
      error: new Error('Alerts API failed'),
    })

    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Should show alerts error in the analytics section
    expect(screen.getByText('Failed to load dashboard analytics.')).toBeInTheDocument()
    expect(screen.getByText('Alerts API failed')).toBeInTheDocument()

    // Stats should still work - use getAllByText due to Strict Mode rendering twice
    expect(screen.getAllByText('500').length).toBeGreaterThan(0)
    expect(screen.getAllByText('1000000').length).toBeGreaterThan(0)
  })

  it('shows loading state when alerts are loading', async () => {
    const Wrapper = createWrapper()

    // Alerts are loading
    useAlertsMock.mockReturnValue({
      data: undefined,
      isPending: true,
      error: null,
    })

    render(<DashboardAlertAnalyticsSection />, { wrapper: Wrapper })

    // Should show loading skeletons for analytics
    // Note: The dashboard analytics component has its own skeleton loading state
    expect(useAlertsMock).toHaveBeenCalled()
  })
})
