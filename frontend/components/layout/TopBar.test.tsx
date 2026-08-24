import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DashboardTopBar, TopBar } from './TopBar'

const mockPush = vi.fn()

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: mockPush }),
}))

vi.mock('@/app/providers', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
}))

vi.mock('@/features/alerts/queries', () => ({
  useAlertsFromFilters: () => ({ data: undefined }),
}))

describe('TopBar', () => {
  afterEach(() => {
    cleanup()
    mockPush.mockReset()
    vi.useRealTimers()
  })

  it('allows the title and search control to shrink within the shell', () => {
    render(<TopBar title="Dashboard" showSearch showLiveStatus />)

    expect(screen.getByRole('banner')).toHaveClass('min-w-0')
    expect(screen.getByRole('textbox')).toHaveClass('w-full', 'max-w-64', 'min-w-0')
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-label', 'Search path, attack type...')
  })

  it('uses a compact theme control label that cannot overlap search on narrow screens', () => {
    render(<TopBar title="Dashboard" showSearch />)

    expect(screen.getByText('Theme')).toHaveClass('hidden', 'sm:inline')
  })

  it('does not show the snapshot status pill on the dashboard', () => {
    render(<DashboardTopBar />)

    expect(screen.queryByText('Snapshot')).not.toBeInTheDocument()
  })

  it('routes Dashboard searches to the Alerts page', () => {
    vi.useFakeTimers()
    render(<DashboardTopBar />)

    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'SQL Injection' },
    })
    vi.advanceTimersByTime(300)

    expect(mockPush).toHaveBeenCalledWith('/alerts?search=SQL+Injection', {
      scroll: false,
    })
  })

  it('wraps alert counts into a narrow layout without clipping them', () => {
    render(
      <TopBar
        title="Alerts"
        showSearch
        showConfidenceTierControls={false}
        showNewIndicator
      />
    )

    const header = screen.getByRole('banner')
    expect(header).toHaveClass('min-h-16', 'flex-wrap')
    expect(screen.getByText('NEW:')).toBeVisible()
    expect(screen.getByText('IN REVIEW:')).toBeVisible()
  })
})
