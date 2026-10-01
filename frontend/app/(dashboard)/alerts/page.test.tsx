import { beforeEach, describe, expect, it, vi } from 'vitest'

const { redirectMock } = vi.hoisted(() => ({ redirectMock: vi.fn() }))

vi.mock('next/navigation', () => ({ redirect: redirectMock }))

import LegacyAlertsPage from './page'

describe('LegacyAlertsPage', () => {
  beforeEach(() => {
    redirectMock.mockClear()
  })

  it('redirects old alert deep links and filters to Traffic History', async () => {
    await LegacyAlertsPage({
      searchParams: Promise.resolve({
        alert_id: '42',
        include_normal: 'true',
        page: '3',
        search: 'SQL Injection',
      }),
    })

    expect(redirectMock).toHaveBeenCalledWith(
      '/traffic-history?alert_id=42&include_normal=true&page=3&search=SQL+Injection'
    )
  })
})
