import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { UserManagementWorkspace } from './UserManagementWorkspace'

const account = {
  id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
  display_name: 'SOC Analyst',
  email: 'analyst@example.test',
  pending_email: null,
  role: 'ANALYST' as const,
  enabled: true,
  email_verified: true,
  mfa_status: 'enrollment_required' as const,
  created_at: '2026-07-01T00:00:00Z',
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('UserManagementWorkspace', () => {
  it('renders a dense safe account workspace without a password input', () => {
    render(<UserManagementWorkspace initialAccounts={[account]} />)

    expect(screen.getByRole('heading', { name: 'User Management' })).toBeInTheDocument()
    expect(screen.getByText('SOC Analyst')).toBeInTheDocument()
    expect(screen.getByText('Enrollment required')).toBeInTheDocument()
    expect(screen.getByText('Jul 1, 2026, 12:00 AM UTC')).toBeInTheDocument()
    expect(screen.getByLabelText('Account email')).toBeInTheDocument()
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Request email verification for SOC Analyst' })).toBeInTheDocument()
  })

  it('submits only email, display name, and role for account creation', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ account_id: account.id }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<UserManagementWorkspace initialAccounts={[]} />)

    fireEvent.change(screen.getByLabelText('Account email'), {
      target: { value: 'new@example.test' },
    })
    fireEvent.change(screen.getByLabelText('Display name'), {
      target: { value: 'New Viewer' },
    })
    fireEvent.change(screen.getByLabelText('Role'), {
      target: { value: 'VIEWER' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const request = fetchMock.mock.calls[0][1]
    expect(JSON.parse(request.body)).toEqual({
      email: 'new@example.test',
      display_name: 'New Viewer',
      role: 'VIEWER',
    })
  })

  it('shows a refresh failure instead of silently retaining stale account state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
    render(<UserManagementWorkspace initialAccounts={[account]} />)

    fireEvent.click(screen.getByRole('button', { name: 'Refresh accounts' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/unable to refresh account list/i)
    })
    expect(screen.getByText('SOC Analyst')).toBeInTheDocument()
  })

  it('tracks a pending row action independently from other actions', async () => {
    let resolveFetch: ((value: unknown) => void) | undefined
    const pendingResponse = new Promise((resolve) => {
      resolveFetch = resolve
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pendingResponse))
    render(<UserManagementWorkspace initialAccounts={[account]} />)

    const disableButton = screen.getByRole('button', { name: 'Disable SOC Analyst' })
    fireEvent.click(disableButton)

    await waitFor(() => expect(disableButton).toBeDisabled())
    expect(screen.getByRole('button', { name: 'Resend setup for SOC Analyst' })).not.toBeDisabled()

    resolveFetch?.({ ok: true, json: async () => ({ accounts: [account] }) })
  })
})
