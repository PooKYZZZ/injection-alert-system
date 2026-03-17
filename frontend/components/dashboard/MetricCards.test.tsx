import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MetricCards from './MetricCards'
import { useDashboardStats } from 'features/stats/queries'
import { useAlerts } from 'features/alerts/queries'
import { useSearchParams } from 'next/navigation'

vi.mock('features/stats/queries', () => ({
  useDashboardStats: vi.fn(),
}))

vi.mock('features/alerts/queries', () => ({
  useAlerts: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useSearchParams: vi.fn(),
}))

const mockedUseDashboardStats = vi.mocked(useDashboardStats)
const mockedUseAlerts = vi.mocked(useAlerts)
const mockedUseSearchParams = vi.mocked(useSearchParams)

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
  function mockDefaultSearchParams() {
    mockedUseSearchParams.mockReturnValue({
      get: (key: string) => new URLSearchParams().get(key),
    } as ReturnType<typeof useSearchParams>)
  }

  it('renders loading skeleton', () => {
    mockDefaultSearchParams()
    mockedUseDashboardStats.mockReturnValue({
      data: undefined,
      isPending: true,
    } as ReturnType<typeof useDashboardStats>)
    mockedUseAlerts.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as ReturnType<typeof useAlerts>)

    const Wrapper = createWrapper()
    const { container } = render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.queryByText('Total Requests')).not.toBeInTheDocument()
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('renders total requests card with updated description', () => {
    mockDefaultSearchParams()
    mockedUseDashboardStats.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        actionable_alerts: 10,
        total_requests: 321,
        avg_inference_latency_ms: 0,
      },
    } as ReturnType<typeof useDashboardStats>)
    mockedUseAlerts.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        items: [
          { confidence: 0.91, prediction: 'SQL Injection', action_taken: 'BLOCKED' },
          { confidence: 0.25, prediction: 'Normal', action_taken: 'ALLOWED' },
        ],
      },
    } as ReturnType<typeof useAlerts>)

    const Wrapper = createWrapper()
    render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('321')).toBeInTheDocument()
    expect(screen.getByText('All requests in the current stats response')).toBeInTheDocument()
    expect(screen.getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByText('Allowed')).toBeInTheDocument()
  })

  it('renders alert-derived metrics from the loaded alerts dataset', () => {
    mockDefaultSearchParams()
    mockedUseDashboardStats.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        actionable_alerts: 1,
        total_requests: 321,
        avg_inference_latency_ms: 4.5,
      },
    } as ReturnType<typeof useDashboardStats>)
    mockedUseAlerts.mockReturnValue({
      isPending: false,
      isError: false,
      data: {
        items: [
          { confidence: 0.9, prediction: 'SQL Injection', action_taken: 'BLOCKED' },
          { confidence: 0.3, prediction: 'Normal', action_taken: 'ALLOWED' },
        ],
      },
    } as ReturnType<typeof useAlerts>)

    const Wrapper = createWrapper()
    render(<MetricCards />, { wrapper: Wrapper })

    expect(screen.getByText('Actionable Alerts')).toBeInTheDocument()
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(3)
    expect(screen.getByText('Derived from 2 currently loaded alerts')).toBeInTheDocument()
    expect(screen.getByText('60.0%')).toBeInTheDocument()
    expect(screen.getByText('Average confidence across the current loaded alert set')).toBeInTheDocument()
  })
})
