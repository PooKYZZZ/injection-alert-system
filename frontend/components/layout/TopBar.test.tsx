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

    expect(screen.getByRole('banner')).toHaveClass('min-h-14')
    expect(screen.getByRole('textbox')).toHaveClass('w-full', 'min-w-0')
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-label', 'Search alerts, paths, or attack types')
  })

  it('uses a compact theme control label that cannot overlap search on narrow screens', () => {
    render(<TopBar title="Dashboard" showSearch />)

    expect(screen.getByText('Theme')).toHaveClass('hidden', 'sm:inline')
  })

  it('uses one neutral utility context instead of repeating the page title', () => {
    render(<DashboardTopBar />)

    expect(screen.queryByText('Snapshot')).not.toBeInTheDocument()
    expect(screen.getByText('Security operations')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
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

  it('removes static alert counts from the global utility bar', () => {
    render(
      <TopBar
        title="Alerts"
        showSearch
        showConfidenceTierControls={false}
        showNewIndicator
      />
    )

    const header = screen.getByRole('banner')
    expect(header).toHaveClass('min-h-14')
    expect(screen.queryByText('NEW:')).not.toBeInTheDocument()
    expect(screen.queryByText('IN REVIEW:')).not.toBeInTheDocument()
  })
})
