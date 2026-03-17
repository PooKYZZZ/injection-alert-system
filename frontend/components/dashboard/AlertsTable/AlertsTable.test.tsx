import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AlertsTable from './AlertsTable'
import { useAlerts } from 'features/alerts/queries'
import { useDashboardStore } from '@/store/dashboardStore'
import type { Alert } from 'features/alerts/types'

const mockReplace = vi.fn()

vi.mock('next/navigation', () => ({
  useSearchParams: vi.fn(),
  usePathname: vi.fn(),
  useRouter: vi.fn(),
}))

vi.mock('features/alerts/queries', () => ({
  useAlerts: vi.fn(),
}))

const { useSearchParams, usePathname, useRouter } = await import('next/navigation')
const mockedUseAlerts = vi.mocked(useAlerts)
const mockedUseSearchParams = vi.mocked(useSearchParams)
const mockedUsePathname = vi.mocked(usePathname)
const mockedUseRouter = vi.mocked(useRouter)
const sampleAlert: Alert = {
  alert_id: 'alert-1',
  timestamp: '2026-03-17T15:30:00Z',
  source_ip: '192.168.0.10',
  request_path: '/search',
  request_method: 'GET',
  payload_snippet: "' OR 1=1 --",
  prediction: 'SQL Injection',
  confidence: 0.91,
  confidence_level: 'HIGH',
  action_taken: 'BLOCKED',
  crs_score: 8.5,
  crs_rule_ids: ['942100'],
}

function buildQueryResult(overrides: Partial<ReturnType<typeof useAlerts>> = {}) {
  return {
    data: {
      items: [],
      total: 0,
      page: 1,
      pageSize: 25,
    },
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    dataUpdatedAt: Date.parse('2026-03-17T15:30:00Z'),
    ...overrides,
  } as ReturnType<typeof useAlerts>
}

beforeEach(() => {
  mockedUsePathname.mockReturnValue('/dashboard')
  mockedUseRouter.mockReturnValue({
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
    push: vi.fn(),
    replace: mockReplace,
    refresh: vi.fn(),
  } as unknown as ReturnType<typeof useRouter>)
  mockedUseSearchParams.mockReturnValue(
    new URLSearchParams() as unknown as ReturnType<typeof useSearchParams>
  )
  mockedUseAlerts.mockReturnValue(buildQueryResult())
  useDashboardStore.setState({
    selectedAlertIds: new Set(),
    activeIncidentId: null,
  })
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('AlertsTable', () => {
  it('renders exactly three skeleton rows while loading', async () => {
    mockedUseAlerts.mockReturnValue(
      buildQueryResult({
        isPending: true,
      })
    )

    const { container } = render(<AlertsTable />)

    await waitFor(() => {
      expect(container.querySelectorAll('tr[aria-hidden="true"]').length).toBe(3)
    })
  })

  it('renders the unfiltered empty state copy inside the table', async () => {
    render(<AlertsTable />)

    expect(await screen.findByText('No alerts in the selected range.')).toBeInTheDocument()
    expect(screen.getByText(/Last loaded/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument()
  })

  it('renders the filtered empty state with a clear-filters action', async () => {
    mockedUseSearchParams.mockReturnValue(
      new URLSearchParams({
        severity: 'HIGH',
        search: 'union select',
      }) as unknown as ReturnType<typeof useSearchParams>
    )

    render(<AlertsTable />)

    expect(await screen.findByText('No alerts match the current filters.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(mockReplace).toHaveBeenCalledWith('/dashboard')
  })

  it('renders the error state with a retry action', async () => {
    const refetch = vi.fn()
    mockedUseAlerts.mockReturnValue(
      buildQueryResult({
        data: undefined,
        isError: true,
        error: new Error('/api/alerts responded with 500'),
        refetch,
      })
    )

    render(<AlertsTable />)

    expect(await screen.findByText('Unable to load alerts.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(refetch).toHaveBeenCalled()
  })

  it('auto-saves triage edits and shows a brief confirmation', async () => {
    vi.useFakeTimers()
    mockedUseAlerts.mockReturnValue(
      buildQueryResult({
        data: {
          items: [sampleAlert],
          total: 1,
          page: 1,
          pageSize: 25,
        },
      })
    )

    render(<AlertsTable />)

    await vi.advanceTimersByTimeAsync(0)

    const triageSelect = screen.getByLabelText('Triage status for alert alert-1')
    fireEvent.change(triageSelect, { target: { value: 'In Progress' } })

    expect(screen.getByText('Saving...')).toBeInTheDocument()

    await vi.advanceTimersByTimeAsync(500)

    expect(screen.getByText('Saved')).toBeInTheDocument()
    expect(window.localStorage.getItem('cybertrace.localTriageStatus')).toContain('In Progress')
  })
})
