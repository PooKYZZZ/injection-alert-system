import React from 'react'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Sidebar } from './Sidebar'
import { signOut } from 'next-auth/react'

vi.mock('next-auth/react', () => ({
  signOut: vi.fn(),
}))

vi.mock('./SidebarNavItem', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./SidebarNavItem')>()
  return {
    ...actual,
    SidebarNavItem: ({ children, label }: { children?: React.ReactNode; label?: string }) => (
      <div data-testid="sidebar-nav-item">{label}{children}</div>
    ),
  }
})

vi.mock('./AlertsNavItem', () => ({
  AlertsNavItem: ({ label }: { label: string }) => <div>{label}</div>,
}))

vi.mock('./MLHealthWidget', () => ({
  MLHealthWidget: () => <div>ML Health</div>,
}))

afterEach(() => {
  cleanup()
})

describe('Sidebar', () => {
  it('renders without crashing', () => {
    render(<Sidebar />)
    expect(screen.getByText('CyberTrace')).toBeInTheDocument()
    expect(screen.getByText('WAF-ML Security Dashboard')).toBeInTheDocument()
    expect(screen.getByText('SOC Analyst')).toBeInTheDocument()
  })

  it('renders provided identity values', () => {
    render(<Sidebar displayName="SOC Analyst" secondaryLabel="soc@example.com" />)
    expect(screen.getByText('SOC Analyst')).toBeInTheDocument()
    expect(screen.queryByText('soc@example.com')).not.toBeInTheDocument()
  })

  it('shows User Management only for ADMIN', () => {
    const { rerender } = render(<Sidebar role="ADMIN" />)
    expect(screen.getByText('User Management')).toBeInTheDocument()

    rerender(<Sidebar role="ANALYST" />)
    expect(screen.queryByText('User Management')).not.toBeInTheDocument()
  })

  it('uses set1 shell styling for the analyst identity badge', () => {
    render(<Sidebar displayName="SOC Analyst" />)

    const initials = screen.getByText('SA')
    const initialsContainer = initials.closest('div')

    expect(initialsContainer).toHaveClass('bg-surface-card')
    expect(initials).toHaveClass('text-accent-action')
  })

  it('uses semantic shell surfaces on sidebar chrome', () => {
    render(<Sidebar />)

    const sidebar = screen.getByRole('complementary')
    expect(sidebar).toHaveClass('bg-surface-shell')
  })

  it('logout button has aria-label="Log out"', () => {
    render(<Sidebar />)
    expect(screen.getByRole('button', { name: 'Log out' })).toHaveAttribute('aria-label', 'Log out')
  })

  it('opens confirmation dialog and signs out only after confirm', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)

    await user.click(screen.getByRole('button', { name: 'Log out' }))
    expect(signOut).not.toHaveBeenCalled()

    const dialog = await screen.findByRole('dialog')
    const confirmLogoutButton = within(dialog).getByRole('button', { name: 'Log out' })

    await user.click(confirmLogoutButton)

    expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' })
  })
})
