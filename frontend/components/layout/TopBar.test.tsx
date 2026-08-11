import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TopBar } from './TopBar'

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/app/providers', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
}))

vi.mock('@/features/alerts/queries', () => ({
  useAlertsFromFilters: () => ({ data: undefined }),
}))

describe('TopBar', () => {
  it('allows the title and search control to shrink within the shell', () => {
    render(<TopBar title="Dashboard" showSearch showLiveStatus />)

    expect(screen.getByRole('banner')).toHaveClass('min-w-0')
    expect(screen.getByRole('textbox')).toHaveClass('w-full', 'max-w-64', 'min-w-0')
  })
})
