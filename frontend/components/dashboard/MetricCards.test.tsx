import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MetricCards from './MetricCards'
import { useDashboardStats } from 'features/stats/queries'

vi.mock('features/stats/queries', () => ({
  useDashboardStats: vi.fn(),
}))

const mockedUseDashboardStats = vi.mocked(useDashboardStats)

afterEach(() => {
  cleanup()
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
    mockedUseDashboardStats.mockReturnValue({
      data: undefined,
      isPending: true,
    } as ReturnType<typeof useDashboardStats>)

    const Wrapper = createWrapper()
    const { container } = render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.queryByText('Total Requests')).not.toBeInTheDocument()
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('renders correct total_requests value (not total_crs_flagged)', () => {
    mockedUseDashboardStats.mockReturnValue({
      isPending: false,
      data: {
        actionable_alerts: 10,
        total_requests: 321,
        avg_inference_latency_ms: 0,
      },
    } as ReturnType<typeof useDashboardStats>)

    const Wrapper = createWrapper()
    render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('321')).toBeInTheDocument()
    expect(
      screen.getByText('All requests included in the current stats response')
    ).toBeInTheDocument()
  })

  it('renders latency and actionable-alert descriptions from real stats fields', () => {
    mockedUseDashboardStats.mockReturnValue({
      isPending: false,
      data: {
        actionable_alerts: 1,
        total_requests: 321,
        avg_inference_latency_ms: 4.5,
      },
    } as ReturnType<typeof useDashboardStats>)

    const Wrapper = createWrapper()
    render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.getByText('4.5 ms')).toBeInTheDocument()
    expect(
      screen.getByText('Count of non-normal labels in the current stats response')
    ).toBeInTheDocument()
  })
})
