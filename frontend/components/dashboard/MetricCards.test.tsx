import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MetricCards from './MetricCards'
import type { Alert } from 'features/alerts/types'

const sampleAlerts: Alert[] = [
  {
    alert_id: 'a-1',
    timestamp: '2026-03-17T00:00:00Z',
    source_ip: '127.0.0.1',
    request_path: '/login',
    request_method: 'POST',
    payload_snippet: 'SELECT 1',
    prediction: 'SQL Injection',
    confidence: 0.91,
    confidence_level: 'HIGH',
    action_taken: 'BLOCKED',
  },
  {
    alert_id: 'a-2',
    timestamp: '2026-03-17T00:01:00Z',
    source_ip: '127.0.0.2',
    request_path: '/health',
    request_method: 'GET',
    payload_snippet: 'ok',
    prediction: 'Normal',
    confidence: 0.25,
    confidence_level: 'LOW',
    action_taken: 'ALLOWED',
  },
]

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
      <MetricCards alerts={[]} alertsPending={true} alertsError={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.queryByText('Total Requests')).not.toBeInTheDocument()
    expect(container.querySelectorAll('[aria-hidden="true"]').length).toBeGreaterThan(0)
  })

  it('renders the required five summary cards with live alert counts', () => {
    const Wrapper = createWrapper()
    render(
      <MetricCards alerts={sampleAlerts} alertsPending={false} alertsError={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.getByText('High Alerts')).toBeInTheDocument()
    expect(screen.getByText('Total Requests')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getAllByText('Loaded records').length).toBe(5)
    expect(screen.getByText('Blocked')).toBeInTheDocument()
    expect(screen.getByText('Allowed')).toBeInTheDocument()
    expect(screen.getByText('Avg ML Confidence')).toBeInTheDocument()
  })

  it('renders alert-derived metrics from the loaded alerts dataset safely', () => {
    const Wrapper = createWrapper()
    const expectedAvgConfidence = `${(
      (sampleAlerts.reduce((sum, alert) => sum + alert.confidence, 0) / sampleAlerts.length) *
      100
    ).toFixed(1)}%`

    render(
      <MetricCards alerts={sampleAlerts} alertsPending={false} alertsError={null} />,
      { wrapper: Wrapper }
    )

    expect(screen.getByText('High Alerts')).toBeInTheDocument()
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(3)
    expect(screen.getByText(expectedAvgConfidence)).toBeInTheDocument()
  })

  it('renders empty alert datasets without NaN output', () => {
    const Wrapper = createWrapper()
    render(<MetricCards alerts={[]} alertsPending={false} alertsError={null} />, {
      wrapper: Wrapper,
    })

    expect(screen.getByText('High Alerts')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.queryByText('NaN%')).not.toBeInTheDocument()
    expect(screen.queryByText('Infinity')).not.toBeInTheDocument()
  })
})
