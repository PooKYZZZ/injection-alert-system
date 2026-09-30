import React from 'react'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
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
    SidebarNavItem: ({ label, onNavigate }: { label?: string; onNavigate?: () => void }) => (
      <button type="button" onClick={onNavigate}>{label}</button>
    ),
  }
})

vi.mock('./AlertsNavItem', () => ({
  AlertsNavItem: ({ label, onNavigate }: { label: string; onNavigate?: () => void }) => (
    <button type="button" onClick={onNavigate}>{label}</button>
  ),
}))

vi.mock('./MLHealthWidget', () => ({
  MLHealthWidget: () => <div>ML Health</div>,
}))

const COLLAPSE_KEY = 'cybertrace.sidebar-collapsed'

afterEach(() => {
  cleanup()
  window.localStorage.removeItem(COLLAPSE_KEY)
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

  it('shows User Management for ADMIN and OWNER', () => {
    const { rerender } = render(<Sidebar role="ADMIN" />)
    expect(screen.getByText('User Management')).toBeInTheDocument()

    rerender(<Sidebar role="ANALYST" />)
    expect(screen.queryByText('User Management')).not.toBeInTheDocument()

    rerender(<Sidebar role="OWNER" />)
    expect(screen.getByText('User Management')).toBeInTheDocument()
  })

  it.each(['ADMIN', 'ANALYST', 'VIEWER'] as const)(
    'hides Model Health and Model Lifecycle from %s',
    (role) => {
      render(<Sidebar role={role} />)

      expect(screen.queryByText('Model Health')).not.toBeInTheDocument()
      expect(screen.queryByText('Model Lifecycle')).not.toBeInTheDocument()
    }
  )

  it('shows both protected ML navigation entries and health widget for OWNER', () => {
    render(<Sidebar role="OWNER" />)

    expect(screen.getAllByText('ML Health').length).toBeGreaterThan(0)
    expect(screen.getByText('Model Health')).toBeInTheDocument()
    expect(screen.getByText('Model Lifecycle')).toBeInTheDocument()
  })

  it('uses set1 shell styling for the analyst identity badge', () => {
    render(<Sidebar displayName="SOC Analyst" />)

    const initials = screen.getByText('SA')
    expect(initials).toHaveClass('bg-surface-card')
    expect(initials).toHaveClass('text-accent-action')
  })

  it('uses semantic shell surfaces on sidebar chrome', () => {
    render(<Sidebar />)

    const sidebar = screen.getByRole('complementary')
    expect(sidebar).toHaveClass('bg-surface-shell')
  })

  it('opens an account flyout with the current identity and role', async () => {
    const user = userEvent.setup()
    render(<Sidebar displayName="SOC Analyst" secondaryLabel="soc@example.com" role="ANALYST" />)

    await user.click(screen.getByRole('button', { name: 'Account menu for SOC Analyst' }))

    const account = screen.getByRole('dialog', { name: 'Account' })
    expect(within(account).getByText('soc@example.com')).toBeInTheDocument()
    expect(within(account).getByText('Role: ANALYST')).toBeInTheDocument()
    expect(within(account).getByRole('button', { name: 'Log out' })).toHaveFocus()
  })

  it('closes the account flyout on Escape and returns focus to its trigger', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)
    const trigger = screen.getByRole('button', { name: 'Account menu for SOC Analyst' })

    await user.click(trigger)
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog', { name: 'Account' })).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('closes the account flyout when the user clicks outside it', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)

    await user.click(screen.getByRole('button', { name: 'Account menu for SOC Analyst' }))
    await user.click(screen.getByRole('button', { name: 'Open navigation' }))

    expect(screen.queryByRole('dialog', { name: 'Account' })).not.toBeInTheDocument()
  })

  it('provides a responsive mobile navigation dialog', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)

    await user.click(screen.getByRole('button', { name: 'Open navigation' }))

    const dialog = await screen.findByRole('dialog', { name: 'Dashboard navigation' })
    expect(within(dialog).getByRole('navigation', { name: 'Dashboard navigation' })).toBeInTheDocument()
    expect(within(dialog).getByText('CyberTrace')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Help & Guide' })).toBeInTheDocument()
  })

  it('keeps the mobile navigation open when Escape closes the account flyout', async () => {
    const user = userEvent.setup()
    render(<Sidebar displayName="SOC Analyst" secondaryLabel="soc@example.com" role="ANALYST" />)

    await user.click(screen.getByRole('button', { name: 'Open navigation' }))
    const navigation = await screen.findByRole('dialog', { name: 'Dashboard navigation' })
    const accountTrigger = within(navigation).getByRole('button', { name: 'Account menu for SOC Analyst' })
    await user.click(accountTrigger)

    const account = await screen.findByRole('dialog', { name: 'Account' })
    expect(within(account).getByText('soc@example.com')).toBeInTheDocument()
    await user.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Account' })).not.toBeInTheDocument())
    expect(screen.getByRole('dialog', { name: 'Dashboard navigation' })).toBeInTheDocument()
    expect(accountTrigger).toHaveFocus()
  })

  it('closes the mobile navigation after selecting a route', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)

    await user.click(screen.getByRole('button', { name: 'Open navigation' }))
    const dialog = await screen.findByRole('dialog', { name: 'Dashboard navigation' })

    await user.click(within(dialog).getByRole('button', { name: 'Dashboard' }))

    expect(screen.queryByRole('dialog', { name: 'Dashboard navigation' })).not.toBeInTheDocument()
  })

  it('opens confirmation dialog and signs out only after confirm', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)

    await user.click(screen.getByRole('button', { name: 'Account menu for SOC Analyst' }))
    await user.click(within(screen.getByRole('dialog', { name: 'Account' })).getByRole('button', { name: 'Log out' }))
    expect(signOut).not.toHaveBeenCalled()

    const dialog = await screen.findByRole('dialog')
    const confirmLogoutButton = within(dialog).getByRole('button', { name: 'Log out' })

    await user.click(confirmLogoutButton)

    expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' })
  })

  it('opens the global Help & Guide and restores focus to the entry on close', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)
    const trigger = screen.getByRole('button', { name: 'Help & Guide' })

    await user.click(trigger)

    const dialog = await screen.findByRole('dialog', { name: 'Help & Guide' })
    expect(within(dialog).getByRole('heading', { name: 'Getting started' })).toBeInTheDocument()
    expect(within(dialog).getByText(/Confidence indicates how strongly the model supports/i)).toBeInTheDocument()
    await user.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Help & Guide' })).not.toBeInTheDocument())
    expect(trigger).toHaveFocus()
  })

  it('returns focus to the mobile navigation control after closing Help', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)
    const navigationTrigger = screen.getByRole('button', { name: 'Open navigation' })

    await user.click(navigationTrigger)
    const navigation = await screen.findByRole('dialog', { name: 'Dashboard navigation' })
    await user.click(within(navigation).getByRole('button', { name: 'Help & Guide' }))

    expect(await screen.findByRole('dialog', { name: 'Help & Guide' })).toBeInTheDocument()
    await user.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Help & Guide' })).not.toBeInTheDocument())
    expect(navigationTrigger).toHaveFocus()
  })

  it('collapses the desktop navigation and persists the preference', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)
    const desktopAside = screen.getByRole('complementary', { name: 'Primary sidebar' })
    const collapseButton = screen.getByRole('button', { name: 'Collapse navigation' })

    await user.click(collapseButton)

    expect(desktopAside).toHaveClass('w-[72px]')
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveAttribute('aria-expanded', 'false')
    await waitFor(() => expect(window.localStorage.getItem(COLLAPSE_KEY)).toBe('true'))
  })

  it('restores a persisted collapsed sidebar on the next render', async () => {
    window.localStorage.setItem(COLLAPSE_KEY, 'true')
    render(<Sidebar />)

    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Primary sidebar' })).toHaveClass('w-[72px]'))
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveAttribute('aria-expanded', 'false')
  })
})
