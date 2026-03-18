import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MetricCards from './MetricCards'
import type { DashboardStats } from '@/features/stats/types'

const sampleStats: DashboardStats = {
  actionable_alerts: 145,
  total_requests: 8400000,
  avg_inference_latency_ms: 3.4,
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

  it('renders three summary cards with real stats data', () => {
    const Wrapper = createWrapper()
    render(
      <MetricCards stats={sampleStats} statsPending={false} statsError={null} />,
      { wrapper: Wrapper }
    )

    // Now we show only 3 cards with real data from stats
    expect(screen.getByText('High Alerts')).toBeInTheDocument()
    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('145')).toBeInTheDocument()
    expect(screen.getByText('8400000')).toBeInTheDocument()
    expect(screen.getByText('Avg ML Latency')).toBeInTheDocument()
    expect(screen.getByText('3.4ms')).toBeInTheDocument()
    // All three cards show "System-wide" subtitle
    expect(screen.getAllByText('System-wide').length).toBe(3)
  })

  it('renders stats-based metrics correctly', () => {
    const Wrapper = createWrapper()
    render(
      <MetricCards stats={sampleStats} statsPending={false} statsError={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.getByText('High Alerts')).toBeInTheDocument()
    expect(screen.getByText('145')).toBeInTheDocument() // actionable_alerts
    expect(screen.getByText('8400000')).toBeInTheDocument() // total_requests
    expect(screen.getByText('Avg ML Latency')).toBeInTheDocument()
    expect(screen.getByText('3.4ms')).toBeInTheDocument() // avg_inference_latency_ms
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
