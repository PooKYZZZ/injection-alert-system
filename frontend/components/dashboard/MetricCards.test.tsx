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
        actionable_alerts_trend: 0,
        avg_confidence: 0,
        avg_confidence_trend: 0,
        threat_ip_count: 0,
        threat_ip_count_trend: 0,
        crs_comparison: {
          total_crs_flagged: 99,
          ml_confirmed: 0,
          ml_overturned: 0,
          false_positive_reduction_pct: 0,
          total_requests: 321,
          avg_inference_ms: 0,
        },
      },
    } as ReturnType<typeof useDashboardStats>)

    const Wrapper = createWrapper()
    render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('321')).toBeInTheDocument()
    expect(screen.queryByText('99')).not.toBeInTheDocument()
  })

  it('assert displayed value is 321 when total_requests=321 and total_crs_flagged=99', () => {
    mockedUseDashboardStats.mockReturnValue({
      isPending: false,
      data: {
        actionable_alerts: 1,
        actionable_alerts_trend: 0,
        avg_confidence: 0,
        avg_confidence_trend: 0,
        threat_ip_count: 0,
        threat_ip_count_trend: 0,
        crs_comparison: {
          total_crs_flagged: 99,
          ml_confirmed: 0,
          ml_overturned: 0,
          false_positive_reduction_pct: 0,
          total_requests: 321,
          avg_inference_ms: 0,
        },
      },
    } as ReturnType<typeof useDashboardStats>)

    const Wrapper = createWrapper()
    render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.getByText('321')).toHaveTextContent('321')
  })
})
