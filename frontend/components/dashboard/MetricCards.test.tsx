import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MetricCards from './MetricCards'
import type { DashboardStats, ActivityBucket } from '@/features/stats/types'

const sampleActivityBuckets: ActivityBucket[] = [
  { bucket_index: 0, total_count: 50, blocked_count: 5, allowed_count: 45, throttled_count: 0, timestamp_start: new Date() },
  { bucket_index: 1, total_count: 45, blocked_count: 3, allowed_count: 42, throttled_count: 0, timestamp_start: new Date() },
]

const sampleStats: DashboardStats = {
  actionable_alerts: 145,
  total_requests: 8400000,
  avg_inference_latency_ms: 3.4,
  blocked_count: 89,
  allowed_count: 23,
  throttled_count: 12,
  avg_confidence: 0.78,
  activity_buckets: sampleActivityBuckets,
  attack_distribution: {},
  top_source_ips: [],
  top_targeted_paths: [],
}

afterEach(() => {
  cleanup()
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

describe('MetricCards', () => {
  it('renders loading skeleton', () => {
    const Wrapper = createWrapper()
    const { container } = render(
      <MetricCards stats={undefined} statsPending={true} statsError={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.queryByText('Total Requests')).not.toBeInTheDocument()
    expect(container.querySelectorAll('[aria-hidden="true"]').length).toBeGreaterThan(0)
  })

  it('renders five summary cards with real stats data', () => {
    const Wrapper = createWrapper()
    render(
      <MetricCards stats={sampleStats} statsPending={false} statsError={null} />,
      { wrapper: Wrapper }
    )

    // Five cards: High Alerts, Blocked, Allowed, Avg ML Confidence, Total Requests
    expect(screen.getByText('High Alerts')).toBeInTheDocument()
    expect(screen.getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByText('Allowed')).toBeInTheDocument()
    expect(screen.getByText('Avg ML Confidence')).toBeInTheDocument()
    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('145')).toBeInTheDocument() // actionable_alerts
    expect(screen.getByText('89')).toBeInTheDocument() // blocked_count
    expect(screen.getByText('23')).toBeInTheDocument() // allowed_count
    expect(screen.getByText('78%')).toBeInTheDocument() // avg_confidence
    expect(screen.getByText('8400000')).toBeInTheDocument() // total_requests
    // All five cards show "System-wide" subtitle
    expect(screen.getAllByText('System-wide').length).toBe(5)
  })

  it('renders stats-based metrics correctly', () => {
    const Wrapper = createWrapper()
    render(
      <MetricCards stats={sampleStats} statsPending={false} statsError={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.getByText('High Alerts')).toBeInTheDocument()
    expect(screen.getByText('145')).toBeInTheDocument() // actionable_alerts
    expect(screen.getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByText('89')).toBeInTheDocument() // blocked_count
    expect(screen.getByText('Allowed')).toBeInTheDocument()
    expect(screen.getByText('23')).toBeInTheDocument() // allowed_count
    expect(screen.getByText('Avg ML Confidence')).toBeInTheDocument()
    expect(screen.getByText('78%')).toBeInTheDocument() // avg_confidence
    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('8400000')).toBeInTheDocument() // total_requests
  })

  it('renders error state when stats error occurs', () => {
    const Wrapper = createWrapper()
    const statsError = new Error('Failed to fetch stats')
    render(
      <MetricCards stats={undefined} statsPending={false} statsError={statsError} />,
      { wrapper: Wrapper }
    )

    expect(screen.getByText('Unable to load dashboard metrics.')).toBeInTheDocument()
    expect(screen.getByText('Failed to fetch stats')).toBeInTheDocument()
  })

  it('renders empty state when no stats available', () => {
    const Wrapper = createWrapper()
    render(
      <MetricCards stats={undefined} statsPending={false} statsError={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.getByText('No stats data available.')).toBeInTheDocument()
  })
})
