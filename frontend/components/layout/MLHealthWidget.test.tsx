import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { MLHealthWidget } from './MLHealthWidget'
import { useMLHealth } from '@/features/ml-health/queries'

vi.mock('@/features/ml-health/queries', () => ({
  useMLHealth: vi.fn(),
}))

const mockedUseMLHealth = vi.mocked(useMLHealth)

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

describe('MLHealthWidget', () => {
  it('renders simplified model identity and healthy status', () => {
    mockedUseMLHealth.mockReturnValue({
      data: {
        model_version: 'distilbert-v1',
        status: 'HEALTHY',
        latency_ms: 2.5,
        latency_trend: null,
        drift_score: null,
        drift_status: 'NORMAL',
        traffic_processed: 44,
        thresholds: {
          low: 0.5,
          medium: null,
          high: 0.8,
        },
      },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useMLHealth>)

    const Wrapper = createWrapper()
    render(<MLHealthWidget />, { wrapper: Wrapper })

    expect(screen.getByText('distilbert-v1')).toBeInTheDocument()
    expect(screen.getByText('Stable')).toBeInTheDocument()
  })

  it('renders unavailable message when ml health data is missing', () => {
    mockedUseMLHealth.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
    } as ReturnType<typeof useMLHealth>)

    const Wrapper = createWrapper()
    render(<MLHealthWidget />, { wrapper: Wrapper })

    expect(screen.getByText('Model')).toBeInTheDocument()
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
  })
})
