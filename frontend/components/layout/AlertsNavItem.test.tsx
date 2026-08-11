import type { ReactNode } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { useAlertsFromFilters } from '@/features/alerts/queries'
import { DEFAULT_ALERT_FILTERS } from '@/lib/searchParams'
import { AlertsNavItem } from './AlertsNavItem'

vi.mock('@/features/alerts/queries', () => ({
  useAlertsFromFilters: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  usePathname: () => '/alerts',
}))

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    className,
    onClick,
    'aria-current': ariaCurrent,
  }: {
    href: string
    children: ReactNode
    className?: string
    onClick?: () => void
    'aria-current'?: 'page'
  }) => (
    <a href={href} className={className} onClick={onClick} aria-current={ariaCurrent}>
      {children}
    </a>
  ),
}))

vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    span: ({ children, ...rest }: React.HTMLAttributes<HTMLSpanElement>) => <span {...rest}>{children}</span>,
  },
}))

const mockedUseAlertsFromFilters = vi.mocked(useAlertsFromFilters)

describe('AlertsNavItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses alerts page default filters and preserves semantic alert badge styling', () => {
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

    const link = screen.getByRole('link', { name: /alerts/i })
    expect(link).toHaveClass('border-accent-action')
    expect(link).toHaveAttribute('aria-current', 'page')

    const badge = screen.getByText('17')
    expect(badge).toHaveClass('bg-severity-high-accent')
    expect(badge).not.toHaveClass('bg-accent-action')
  })
})
