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

    expect(await screen.findByText('95% (CRITICAL)')).toBeInTheDocument()
  })

  it.each([
    [0.8, 'MEDIUM', '80% (MEDIUM)', 'text-severity-blocked-text'],
    [0.95, 'MEDIUM', '95% (MEDIUM)', 'text-severity-blocked-text'],
    [0.7, 'CRITICAL', '70% (CRITICAL)', 'text-severity-high-text'],
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

  it('marks new alerts as in review when clicked', async () => {
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

    expect(mockTriageMutate).toHaveBeenCalledWith({ id: '42', status: 'in_review' })
    expect(onAlertClick).toHaveBeenCalledWith(
      expect.objectContaining({
        alert_id: '42',
        triage_status: 'in_review',
      })
    )
  })

  it('marks null triage alerts as in review when clicked', async () => {
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

    expect(mockTriageMutate).toHaveBeenCalledWith({ id: '77', status: 'in_review' })
    expect(onAlertClick).toHaveBeenCalledWith(
      expect.objectContaining({
        alert_id: '77',
        triage_status: 'in_review',
      })
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
    ['OWNER', false],
  ] as const)(
    'shows row triage affordances for role %s: %s',
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
      const selectionControl = screen.queryByRole('checkbox', {
        name: 'Select alert role-check',
      })

      expect(Boolean(selectionControl)).toBe(canTriage)
      detailsButton.closest('tr')?.click()

      expect(onAlertClick).toHaveBeenCalled()
      expect(mockTriageMutate).toHaveBeenCalledTimes(canTriage ? 1 : 0)
    }
  )
})
