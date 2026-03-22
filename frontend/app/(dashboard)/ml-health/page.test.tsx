import React from 'react'
import { render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MLHealthPage from './page'
import { useMLHealth } from '@/features/ml-health/queries'

const mockPredictionDistribution = vi.fn(({ countsByLabel }) => (
  <div data-testid="prediction-distribution" data-counts={JSON.stringify(countsByLabel)} />
))

vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<React.ComponentType<any>>, options?: { loading?: () => React.ReactNode }) => {
    return function DynamicComponent(props: Record<string, unknown>) {
      const [LoadedComponent, setLoadedComponent] = React.useState<React.ComponentType<any> | null>(null)

      React.useEffect(() => {
        let active = true
        loader().then((component) => {
          if (active) {
            setLoadedComponent(() => component)
          }
        })
        return () => {
          active = false
        }
      }, [loader])

      if (LoadedComponent) {
        return <LoadedComponent {...props} />
      }

      return options?.loading ? <>{options.loading()}</> : null
    }
  },
}))

vi.mock('@/features/ml-health/queries', () => ({
  useMLHealth: vi.fn(),
}))

vi.mock('@/components/ml-health/ModelHeader', () => ({
  ModelHeader: () => <div data-testid="model-header" />,
}))

vi.mock('@/components/ml-health/ConfidenceThresholds', () => ({
  ConfidenceThresholds: () => <div data-testid="confidence-thresholds" />,
}))

vi.mock('@/components/ui/StateViews', () => ({
  LoadingSkeleton: () => <div data-testid="loading-skeleton" />,
  ErrorState: () => <div data-testid="error-state" />,
}))

vi.mock('@/components/ml-health/PerClassF1Chart', () => ({
  PerClassF1Chart: () => <div data-testid="per-class-f1" />,
}))

vi.mock('@/components/ml-health/ReliabilityDiagram', () => ({
  ReliabilityDiagram: () => <div data-testid="reliability-diagram" />,
}))

vi.mock('@/components/ml-health/ConfidenceDriftChart', () => ({
  ConfidenceDriftChart: () => <div data-testid="confidence-drift" />,
}))

vi.mock('@/components/ml-health/PredictionDistribution', () => ({
  PredictionDistribution: mockPredictionDistribution,
}))

const mockedUseMLHealth = vi.mocked(useMLHealth)

beforeEach(() => {
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
        medium: 0.65,
        high: 0.8,
      },
      macro_f1: 0.91,
      ece: 0.04,
      per_class_f1: {},
      calibration_bins: [],
      prediction_distribution: {
        baseline: {
          'SQL Injection': 2,
          Normal: 8,
        },
        current: {
          'SQL Injection': 3,
          Normal: 7,
        },
      },
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
    } as unknown as ReturnType<typeof useMLHealth>)
  })

describe('MLHealthPage', () => {
  it('passes prediction_distribution data through to the chart', async () => {
    render(<MLHealthPage />)

    await waitFor(() => {
      expect(mockPredictionDistribution).toHaveBeenCalled()
    })

    expect(mockPredictionDistribution.mock.calls[0]?.[0]).toMatchObject({
      countsByLabel: {
        baseline: {
          'SQL Injection': 2,
          Normal: 8,
        },
        current: {
          'SQL Injection': 3,
          Normal: 7,
        },
      },
    })
  })
})
