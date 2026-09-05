import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AlertsTable } from './AlertsTable'
import { useAlertsFromFilters, useTriageMutation } from '@/features/alerts/queries'

const mockReplace = vi.fn()

vi.mock('next/navigation', () => ({
  useSearchParams: vi.fn(),
  usePathname: vi.fn(),
  useRouter: vi.fn(),
}))

vi.mock('@/features/alerts/queries', () => ({
  useAlertsFromFilters: vi.fn(),
  useTriageMutation: vi.fn(),
}))

const { useSearchParams, usePathname, useRouter } = await import('next/navigation')
const mockedUseAlertsFromFilters = vi.mocked(useAlertsFromFilters)
const mockedUseTriageMutation = vi.mocked(useTriageMutation)
const mockedUseSearchParams = vi.mocked(useSearchParams)
const mockedUsePathname = vi.mocked(usePathname)
const mockedUseRouter = vi.mocked(useRouter)
const mockTriageMutate = vi.fn()

function buildQueryResult() {
  return {
    data: {
      items: [],
      total: 0,
      page: 1,
      pageSize: 20,
    },
    isPending: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAlertsFromFilters>
}

beforeEach(() => {
  mockedUsePathname.mockReturnValue('/alerts')
  mockedUseRouter.mockReturnValue({
    back: vi.fn(),
    forward: vi.fn(),
    prefetch: vi.fn(),
    push: vi.fn(),
    replace: mockReplace,
    refresh: vi.fn(),
  } as unknown as ReturnType<typeof useRouter>)
  mockedUseSearchParams.mockReturnValue(new URLSearchParams() as unknown as ReturnType<typeof useSearchParams>)
  mockedUseAlertsFromFilters.mockReturnValue(buildQueryResult())
  mockedUseTriageMutation.mockReturnValue({
    mutate: mockTriageMutate,
  } as unknown as ReturnType<typeof useTriageMutation>)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('AlertsTable', () => {
  it('shows pagination controls after hydration without a mount-only effect', async () => {
    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Page 1 of 0')).toBeInTheDocument()
    })
  })

  it('does not render an impossible range when the result set is empty', async () => {
    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Showing 0 alerts')).toBeInTheDocument()
    })
    expect(screen.queryByText('Showing 1–0 of 0 alerts')).not.toBeInTheDocument()
  })

  it('normalizes ReadonlyURLSearchParams before requesting alerts', async () => {
    const searchParams = new URLSearchParams()
    searchParams.set('severity', 'HIGH')
    searchParams.set('page', '3')
    searchParams.set('sort_by', 'confidence')
    searchParams.set('sort_dir', 'asc')
    searchParams.set('prediction', 'SQL Injection')
    searchParams.append('confidence_level', 'HIGH')
    searchParams.append('confidence_level', 'MEDIUM')
    mockedUseSearchParams.mockReturnValue(
      searchParams as unknown as ReturnType<typeof useSearchParams>
    )

    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    await waitFor(() => {
      expect(mockedUseAlertsFromFilters).toHaveBeenCalled()
    })

    expect(mockedUseAlertsFromFilters).toHaveBeenCalledWith(
      expect.objectContaining({
        confidence_tier: 'HIGH',
        severity: 'HIGH',
        page: 3,
        sort_by: 'confidence',
        sort_dir: 'asc',
        prediction: 'SQL Injection',
        confidence_level: ['HIGH', 'MEDIUM'],
      })
    )
  })

  it('renders a visible confidence column label', async () => {
    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    const confidenceHeaders = await screen.findAllByText('Confidence')
    expect(confidenceHeaders.length).toBeGreaterThan(0)
  })

  it('explains how to reach the horizontally scrollable fields on mobile', async () => {
    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    expect(await screen.findByText('Swipe horizontally to view all alert fields.')).toBeInTheDocument()
  })

  it('does not expose triage sorting when the API does not support it', async () => {
    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    await screen.findByText('Triage')
    expect(screen.queryByRole('button', { name: 'Triage' })).not.toBeInTheDocument()
  })

  it('renders CRITICAL confidence tiers in the confidence column', async () => {
    mockedUseAlertsFromFilters.mockReturnValue({
      ...buildQueryResult(),
      data: {
        items: [
          {
            alert_id: '91',
            timestamp: '2026-04-03T10:00:00.000Z',
            source_ip: '10.0.0.4',
            request_path: '/critical',
            request_method: 'POST',
            payload_snippet: 'payload',
            prediction: 'SQL Injection',
            confidence: 0.95,
            confidence_level: 'CRITICAL',
            action_taken: 'BLOCKED',
            triage_status: 'in_review',
            crs_score: 10,
          },
        ],
        total: 1,
        page: 1,
        pageSize: 20,
      },
    } as unknown as ReturnType<typeof useAlertsFromFilters>)

    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    expect(await screen.findByText('95% (Critical confidence)')).toBeInTheDocument()
  })

  it.each([
    [0.8, 'MEDIUM', '80% (Medium confidence)', 'text-severity-blocked-text'],
    [0.95, 'MEDIUM', '95% (Medium confidence)', 'text-severity-blocked-text'],
    [0.7, 'CRITICAL', '70% (Critical confidence)', 'text-severity-high-text'],
  ] as const)(
    'styles confidence %s from canonical tier %s',
    async (confidence, confidenceLevel, expectedText, expectedClass) => {
      mockedUseAlertsFromFilters.mockReturnValue({
        ...buildQueryResult(),
        data: {
          items: [
            {
              alert_id: 'tier-style',
              timestamp: '2026-04-03T10:00:00.000Z',
              source_ip: '10.0.0.4',
              request_path: '/tier-style',
              request_method: 'POST',
              payload_snippet: 'payload',
              prediction: 'SQL Injection',
              confidence,
              confidence_level: confidenceLevel,
              action_taken: 'THROTTLED',
              triage_status: 'in_review',
              crs_score: 7,
            },
          ],
          total: 1,
          page: 1,
          pageSize: 20,
        },
      } as unknown as ReturnType<typeof useAlertsFromFilters>)

      render(
        <AlertsTable
          selectedIds={[]}
          onSelectionChange={vi.fn()}
          onAlertClick={vi.fn()}
        />
      )

      expect(await screen.findByText(expectedText)).toHaveClass(expectedClass)
    }
  )

  it('opens a new alert without changing its triage status', async () => {
    const onAlertClick = vi.fn()
    mockedUseAlertsFromFilters.mockReturnValue({
      ...buildQueryResult(),
      data: {
        items: [
          {
            alert_id: '42',
            timestamp: '2026-04-03T10:00:00.000Z',
            source_ip: '10.0.0.1',
            request_path: '/login',
            request_method: 'POST',
            payload_snippet: 'payload',
            prediction: 'SQL Injection',
            confidence: 0.92,
            confidence_level: 'HIGH',
            action_taken: 'BLOCKED',
            triage_status: 'new',
            crs_score: 9,
          },
        ],
        total: 1,
        page: 1,
        pageSize: 20,
      },
    } as unknown as ReturnType<typeof useAlertsFromFilters>)

    render(
      <AlertsTable
        role="ANALYST"
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={onAlertClick}
      />
    )

    const rowLabel = await screen.findByLabelText('Select alert 42')
    rowLabel.closest('tr')?.click()

    expect(mockTriageMutate).not.toHaveBeenCalled()
    expect(onAlertClick).toHaveBeenCalledWith(
      expect.objectContaining({
        alert_id: '42',
        triage_status: 'new',
      })
    )
  })

  it('opens an alert with no triage status without changing it', async () => {
    const onAlertClick = vi.fn()
    mockedUseAlertsFromFilters.mockReturnValue({
      ...buildQueryResult(),
      data: {
        items: [
          {
            alert_id: '77',
            timestamp: '2026-04-03T10:00:00.000Z',
            source_ip: '10.0.0.2',
            request_path: '/search',
            request_method: 'GET',
            payload_snippet: 'payload',
            prediction: 'SQL Injection',
            confidence: 0.67,
            confidence_level: 'MEDIUM',
            action_taken: 'THROTTLED',
            triage_status: null,
            crs_score: 7,
          },
        ],
        total: 1,
        page: 1,
        pageSize: 20,
      },
    } as unknown as ReturnType<typeof useAlertsFromFilters>)

    render(
      <AlertsTable
        role="ANALYST"
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={onAlertClick}
      />
    )

    const rowLabel = await screen.findByLabelText('Select alert 77')
    rowLabel.closest('tr')?.click()

    expect(mockTriageMutate).not.toHaveBeenCalled()
    expect(onAlertClick).toHaveBeenCalledWith(
      expect.objectContaining({
        alert_id: '77',
        triage_status: null,
      })
    )
  })

  it('opens a second alert without creating an implicit triage race', async () => {
    const onAlertClick = vi.fn()
    const firstAlert = {
      alert_id: 'first',
      timestamp: '2026-04-03T10:00:00.000Z',
      source_ip: '10.0.0.10',
      request_path: '/first',
      request_method: 'POST',
      payload_snippet: 'first payload',
      prediction: 'SQL Injection',
      confidence: 0.92,
      confidence_level: 'HIGH' as const,
      action_taken: 'BLOCKED' as const,
      triage_status: 'new' as const,
      crs_score: 9,
    }
    const secondAlert = {
      ...firstAlert,
      alert_id: 'second',
      request_path: '/second',
      triage_status: 'in_review' as const,
    }
    mockedUseAlertsFromFilters.mockReturnValue({
      ...buildQueryResult(),
      data: {
        items: [firstAlert, secondAlert],
        total: 2,
        page: 1,
        pageSize: 20,
      },
    } as unknown as ReturnType<typeof useAlertsFromFilters>)

    render(
      <AlertsTable
        role="ANALYST"
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={onAlertClick}
      />
    )

    ;(await screen.findByLabelText('Select alert first')).closest('tr')?.click()
    screen.getByLabelText('Select alert second').closest('tr')?.click()

    expect(onAlertClick).toHaveBeenCalledTimes(2)
    expect(onAlertClick).toHaveBeenLastCalledWith(
      expect.objectContaining({ alert_id: 'second' })
    )
  })

  it('renders the request column with readable two-line request evidence', async () => {
    mockedUseAlertsFromFilters.mockReturnValue({
      ...buildQueryResult(),
      data: {
        items: [
          {
            alert_id: '99',
            timestamp: '2026-04-03T10:00:00.000Z',
            source_ip: '10.0.0.3',
            request_path: '/api/v1/auth/login?redirect=%2Fadmin%2Fusers',
            request_method: 'POST',
            payload_snippet: "username=admin' OR '1'='1",
            prediction: 'SQL Injection',
            confidence: 0.88,
            confidence_level: 'HIGH',
            action_taken: 'BLOCKED',
            triage_status: 'in_review',
            crs_score: 10,
          },
        ],
        total: 1,
        page: 1,
        pageSize: 20,
      },
    } as unknown as ReturnType<typeof useAlertsFromFilters>)

    render(
      <AlertsTable
        selectedIds={[]}
        onSelectionChange={vi.fn()}
        onAlertClick={vi.fn()}
      />
    )

    const requestLine = await screen.findByText('POST /api/v1/auth/login?redirect=%2Fadmin%2Fusers')
    expect(requestLine).toHaveClass('text-[var(--color-accent-analytic)]')
    expect(screen.getByText("username=admin' OR '1'='1")).toBeInTheDocument()
  })

  it.each([
    ['VIEWER', false],
    ['ANALYST', true],
    ['ADMIN', true],
    [undefined, false],
    ['OWNER', true],
  ] as const)(
    'shows selection affordances without implicit row triage for role %s: %s',
    async (role, canTriage) => {
      const onAlertClick = vi.fn()
      mockedUseAlertsFromFilters.mockReturnValue({
        ...buildQueryResult(),
        data: {
          items: [
            {
              alert_id: 'role-check',
              timestamp: '2026-04-03T10:00:00.000Z',
              source_ip: '10.0.0.8',
              request_path: '/role-check',
              request_method: 'POST',
              payload_snippet: 'payload',
              prediction: 'SQL Injection',
              confidence: 0.9,
              confidence_level: 'HIGH',
              action_taken: 'BLOCKED',
              triage_status: 'new',
              crs_score: 9,
            },
          ],
          total: 1,
          page: 1,
          pageSize: 20,
        },
      } as unknown as ReturnType<typeof useAlertsFromFilters>)

      render(
        <AlertsTable
          role={role}
          selectedIds={[]}
          onSelectionChange={vi.fn()}
          onAlertClick={onAlertClick}
        />
      )

      const detailsButton = await screen.findByRole('button', {
        name: 'View details for alert role-check',
      })
      expect(detailsButton).toHaveClass('focus-visible:opacity-100')
      expect(detailsButton.closest('td')).not.toHaveClass('opacity-0')
      const selectionControl = screen.queryByRole('checkbox', {
        name: 'Select alert role-check',
      })

      expect(Boolean(selectionControl)).toBe(canTriage)
      detailsButton.closest('tr')?.click()

      expect(onAlertClick).toHaveBeenCalled()
      expect(mockTriageMutate).not.toHaveBeenCalled()
    }
  )
})
