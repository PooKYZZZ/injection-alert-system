import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MLHealthPage from './page'
import { useMLHealth } from '@/features/ml-health/queries'

vi.mock('@/features/ml-health/queries', () => ({
  useMLHealth: vi.fn(),
}))

vi.mock('@/components/ui/StateViews', () => ({
  LoadingSkeleton: ({ rows }: { rows: number }) => <div data-testid="loading-skeleton">rows:{rows}</div>,
  ErrorState: ({ message }: { message: string }) => <div data-testid="error-state">{message}</div>,
}))

vi.mock('motion/react', () => ({
  motion: new Proxy({}, { get: () => 'div' }),
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('recharts', () => {
  const MockChart = () => <div data-testid="chart-mock" />

  return {
    ResponsiveContainer: () => <div data-testid="chart-container" />,
    AreaChart: MockChart,
    Area: () => <div />,
    CartesianGrid: () => <div />,
    LineChart: MockChart,
    Line: () => <div />,
    ReferenceLine: () => <div />,
    ScatterChart: MockChart,
    Scatter: () => <div />,
    Tooltip: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
  }
})

const mockedUseMLHealth = vi.mocked(useMLHealth)

beforeEach(() => {
  mockedUseMLHealth.mockReturnValue({
    data: {
      model_version: 'distilbert_cleaned_120k_20260324',
      status: 'HEALTHY',
      latency_ms: 32.5,
      latency_trend: null,
      drift_score: 0.034,
      drift_status: 'NORMAL',
      traffic_processed: 1440,
      thresholds: {
        low: 0.5,
        medium: 0.65,
        high: 0.8,
      },
      macro_f1: 0.91,
      ece: 0.04,
      per_class_f1: {},
      calibration_bins: [],
      prediction_distribution: {
        baseline: {
          'SQL Injection': 20,
          Normal: 80,
        },
        current: {
          'SQL Injection': 24,
          Normal: 76,
        },
      },
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useMLHealth>)
})

describe('MLHealthPage', () => {
  it('renders the redesigned overview workspace', () => {
    render(<MLHealthPage />)

    expect(screen.getAllByText('distilbert_cleaned_120k_20260324').length).toBeGreaterThan(0)
    expect(screen.getByPlaceholderText('Search metrics...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Diagnostics' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Detection Impact · Block Rate vs Request Volume')).toBeInTheDocument()
    expect(screen.getByText('Top Risks by Class')).toBeInTheDocument()
    expect(screen.getByText('Recent Activity')).toBeInTheDocument()
  })

  it('switches into diagnostics and shows tab-specific content', () => {
    render(<MLHealthPage />)

    fireEvent.click(screen.getAllByRole('button', { name: 'Diagnostics' })[0])

    expect(screen.getByRole('button', { name: 'Performance' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Drift' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Calibration' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Policy' })).toBeInTheDocument()
    expect(screen.getByText('Inference Latency — p50 and p95 vs target')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Policy' }))

    expect(screen.getByText('Active Policy — Strict Enforcement v2.4')).toBeInTheDocument()
    expect(screen.getByText('Policy Outcomes by Window')).toBeInTheDocument()
  })

  it('renders loading and error states from the workspace component', () => {
    mockedUseMLHealth.mockReturnValueOnce({
      data: undefined,
      isPending: true,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useMLHealth>)

    const { rerender } = render(<MLHealthPage />)

    expect(screen.getByTestId('loading-skeleton')).toHaveTextContent('rows:10')

    mockedUseMLHealth.mockReturnValueOnce({
      data: undefined,
      isPending: false,
      isError: true,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useMLHealth>)

    rerender(<MLHealthPage />)

    expect(screen.getByTestId('error-state')).toHaveTextContent('Failed to load ML health data')
  })
})
