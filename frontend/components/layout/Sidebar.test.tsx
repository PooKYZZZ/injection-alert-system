import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Sidebar } from './Sidebar'
import { signOut } from 'next-auth/react'

vi.mock('next-auth/react', () => ({
  signOut: vi.fn(),
}))

vi.mock('./SidebarNavItem', () => ({
  SidebarNavItem: ({ label }: { label: string }) => <div>{label}</div>,
}))

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
    expect(screen.getByText('Authenticated User')).toBeInTheDocument()
    expect(screen.getByText('Signed in')).toBeInTheDocument()
  })

  it('renders provided identity values', () => {
    render(<Sidebar displayName="SOC Analyst" secondaryLabel="soc@example.com" />)
    expect(screen.getByText('SOC Analyst')).toBeInTheDocument()
    expect(screen.getByText('soc@example.com')).toBeInTheDocument()
  })

  it('logout button has aria-label="Logout"', () => {
    render(<Sidebar />)
    expect(screen.getByRole('button', { name: 'Logout' })).toHaveAttribute('aria-label', 'Logout')
  })

  it('clicking logout calls signOut with correct callbackUrl', async () => {
    const user = userEvent.setup()
    render(<Sidebar />)

    await user.click(screen.getByRole('button', { name: 'Logout' }))

    expect(signOut).toHaveBeenCalledWith({ callbackUrl: '/login' })
  })
})
