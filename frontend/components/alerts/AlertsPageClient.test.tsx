import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AlertsPageClient } from './AlertsPageClient'
import { useAlert } from '@/features/alerts/queries'

const mockReplace = vi.fn()
const mockedUseSearchParams = vi.fn()
const mockedUseAlert = vi.mocked(useAlert)

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockedUseSearchParams(),
  usePathname: () => '/alerts',
  useRouter: () => ({ replace: mockReplace }),
}))

vi.mock('@/features/alerts/queries', () => ({
  useAlert: vi.fn(),
  useAlertsFromFilters: vi.fn(() => ({
    data: { items: [], total: 0, page: 1, pageSize: 20 },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  })),
  useTriageMutation: vi.fn(() => ({ mutate: vi.fn() })),
  useActionMutation: vi.fn(() => ({ mutate: vi.fn() })),
}))

vi.mock('./AlertsTable', () => ({
  AlertsTable: ({ activeAlertId }: { activeAlertId?: string }) => (
    <div data-testid="alerts-table">active:{activeAlertId ?? 'none'}</div>
  ),
}))

vi.mock('./BulkActionBar', () => ({ BulkActionBar: () => <div data-testid="bulk-actions" /> }))
vi.mock('./AlertDrawer', () => ({
  AlertDrawer: ({
    alert,
    onTriageUpdated,
    onActionUpdated,
    onReviewUpdated,
  }: {
    alert: {
      alert_id: string
      action_taken?: string | null
      triage_status?: string | null
      label_review?: { verified_label: string } | null
    } | null
    onTriageUpdated?: (updatedAlert: { alert_id: string; triage_status: string }) => void
    onActionUpdated?: (updatedAlert: { alert_id: string; action_taken: string; triage_status?: string | null }) => void
    onReviewUpdated?: (alertId: string, review: { verified_label: string }) => void
  }) => (
    <div data-testid="alert-drawer">
      {alert ? `drawer:${alert.alert_id}:${alert.label_review?.verified_label ?? 'none'}` : 'closed'}
      {alert && <span data-testid="drawer-triage">{alert.triage_status ?? 'new'}</span>}
      {alert && <span data-testid="drawer-action">{alert.action_taken ?? 'none'}</span>}
      {alert && (
        <>
          <button
            type="button"
            data-testid="apply-review"
            onClick={() => onReviewUpdated?.(alert.alert_id, { verified_label: 'Normal' })}
          >
            apply review
          </button>
          <button
            type="button"
            data-testid="apply-triage"
            onClick={() => onTriageUpdated?.({ ...alert, triage_status: 'in_review' })}
          >
            apply triage
          </button>
          <button
            type="button"
            data-testid="apply-action"
            onClick={() => onActionUpdated?.({ ...alert, action_taken: 'ALLOWED' })}
          >
            apply action
          </button>
          <button
            type="button"
            data-testid="apply-action-stale"
            onClick={() => onActionUpdated?.({ ...alert, triage_status: 'new', action_taken: 'ALLOWED' })}
          >
            apply stale action
          </button>
        </>
      )}
    </div>
  ),
}))

const alert = { alert_id: '10591' } as never

beforeEach(() => {
  mockedUseSearchParams.mockReturnValue(new URLSearchParams('alert_id=10591'))
  mockedUseAlert.mockReturnValue({ data: alert, isPending: false, isError: false, error: null } as never)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('AlertsPageClient deep links', () => {
  it('opens a valid alert deep link without invoking triage', async () => {
    render(<AlertsPageClient role="ANALYST" />)

    await waitFor(() => expect(screen.getByTestId('alert-drawer')).toHaveTextContent('drawer:10591'))
    expect(screen.getByTestId('alerts-table')).toHaveTextContent('active:10591')
  })

  it('updates the selected drawer snapshot after a review succeeds', async () => {
    render(<AlertsPageClient role="ANALYST" />)

    await waitFor(() => expect(screen.getByTestId('alert-drawer')).toHaveTextContent('drawer:10591:none'))
    screen.getByTestId('apply-review').click()

    await waitFor(() => expect(screen.getByTestId('alert-drawer')).toHaveTextContent('drawer:10591:Normal'))
  })

  it('updates the selected drawer snapshot after an explicit triage action succeeds', async () => {
    render(<AlertsPageClient role="ANALYST" />)

    await waitFor(() => expect(screen.getByTestId('alert-drawer')).toHaveTextContent('drawer:10591'))
    expect(screen.getByTestId('drawer-triage')).toHaveTextContent('new')
    screen.getByTestId('apply-triage').click()

    await waitFor(() => expect(screen.getByTestId('drawer-triage')).toHaveTextContent('in_review'))
  })

  it('merges concurrent triage and action updates instead of restoring a stale field', async () => {
    render(<AlertsPageClient role="ADMIN" />)

    await waitFor(() => expect(screen.getByTestId('alert-drawer')).toHaveTextContent('drawer:10591'))
    screen.getByTestId('apply-triage').click()
    await waitFor(() => expect(screen.getByTestId('drawer-triage')).toHaveTextContent('in_review'))

    screen.getByTestId('apply-action-stale').click()

    await waitFor(() => {
      expect(screen.getByTestId('drawer-triage')).toHaveTextContent('in_review')
      expect(screen.getByTestId('drawer-action')).toHaveTextContent('ALLOWED')
    })
  })

  it('updates the selected drawer snapshot after a recorded outcome succeeds', async () => {
    render(<AlertsPageClient role="ADMIN" />)

    await waitFor(() => expect(screen.getByTestId('alert-drawer')).toHaveTextContent('drawer:10591'))
    screen.getByTestId('apply-action').click()

    await waitFor(() => expect(screen.getByTestId('drawer-action')).toHaveTextContent('ALLOWED'))
  })

  it('shows a safe message and does not fetch malformed deep links', () => {
    mockedUseSearchParams.mockReturnValue(new URLSearchParams('alert_id=0&alert_id=2'))
    render(<AlertsPageClient role="ANALYST" />)

    expect(screen.getByRole('status')).toHaveTextContent('The requested alert link is invalid.')
    expect(mockedUseAlert).toHaveBeenCalledWith(null)
  })
})
