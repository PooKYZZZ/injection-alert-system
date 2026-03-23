import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AlertsTable } from './AlertsTable'
import { useAlertsFromFilters } from '@/features/alerts/queries'

const mockReplace = vi.fn()

vi.mock('next/navigation', () => ({
  useSearchParams: vi.fn(),
  usePathname: vi.fn(),
  useRouter: vi.fn(),
}))

vi.mock('@/features/alerts/queries', () => ({
  useAlertsFromFilters: vi.fn(),
}))

const { useSearchParams, usePathname, useRouter } = await import('next/navigation')
const mockedUseAlertsFromFilters = vi.mocked(useAlertsFromFilters)
const mockedUseSearchParams = vi.mocked(useSearchParams)
const mockedUsePathname = vi.mocked(usePathname)
const mockedUseRouter = vi.mocked(useRouter)

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
})

afterEach(() => {
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
        severity: 'HIGH',
        page: 3,
        sort_by: 'confidence',
        sort_dir: 'asc',
        confidence_level: ['HIGH', 'MEDIUM'],
      })
    )
  })
})
