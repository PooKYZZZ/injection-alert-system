import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { useAlerts, useAlertsFromFilters } from '@/features/alerts/queries'
import { DEFAULT_ALERT_FILTERS } from '@/lib/searchParams'
import { AlertsNavItem } from './AlertsNavItem'

vi.mock('@/features/alerts/queries', () => ({
  useAlerts: vi.fn(),
  useAlertsFromFilters: vi.fn(),
}))

vi.mock('./SidebarNavItem', () => ({
  SidebarNavItem: ({ label, badge }: { label: string; badge?: number }) => (
    <div>{`${label}:${badge ?? 'none'}`}</div>
  ),
}))

const mockedUseAlerts = vi.mocked(useAlerts)
const mockedUseAlertsFromFilters = vi.mocked(useAlertsFromFilters)

describe('AlertsNavItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses alerts page default filters for sidebar badge count', () => {
    mockedUseAlerts.mockReturnValue({
      data: {
        items: [],
        total: 0,
        page: 1,
        pageSize: 20,
      },
    } as unknown as ReturnType<typeof useAlerts>)

    mockedUseAlertsFromFilters.mockReturnValue({
      data: {
        items: [],
        total: 17,
        page: 1,
        pageSize: 20,
      },
    } as unknown as ReturnType<typeof useAlertsFromFilters>)

    render(<AlertsNavItem href="/alerts" icon="notifications" label="Alerts" />)

    expect(mockedUseAlertsFromFilters).toHaveBeenCalledWith(DEFAULT_ALERT_FILTERS)
    expect(screen.getByText('Alerts:17')).toBeInTheDocument()
  })
})
