import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
  setup_status: 'complete' as const,
  created_at: '2026-07-01T00:00:00Z',
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('UserManagementWorkspace', () => {
  it('renders a scan-first account list and keeps account actions in a detail panel', () => {
    render(<UserManagementWorkspace initialAccounts={[account]} />)

    expect(screen.getByRole('heading', { name: 'User Management' })).toBeInTheDocument()
    expect(screen.getByText('SOC Analyst')).toBeInTheDocument()
    expect(screen.getByText('Enrollment required')).toBeInTheDocument()
    expect(screen.getByText('Setup complete')).toBeInTheDocument()
    expect(screen.getByText('Jul 1, 2026, 12:00 AM UTC')).toBeInTheDocument()
    expect(screen.getByLabelText('Search accounts')).toBeInTheDocument()
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'View details for SOC Analyst' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Disable SOC Analyst' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'View details for SOC Analyst' }))

    expect(screen.getByRole('dialog', { name: 'SOC Analyst' })).toBeInTheDocument()
    expect(screen.getByText('Account security')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Disable SOC Analyst' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Resend setup for SOC Analyst' })).not.toBeInTheDocument()
  })

  it('keeps role edits as a draft until the administrator saves or cancels', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ accounts: [{ ...account, role: 'VIEWER', mfa_status: 'not_required' }] }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<UserManagementWorkspace initialAccounts={[account]} />)

    fireEvent.click(screen.getByRole('button', { name: 'View details for SOC Analyst' }))
    const dialog = screen.getByRole('dialog', { name: 'SOC Analyst' })
    const roleSelect = within(dialog).getByLabelText('Role for SOC Analyst')

    fireEvent.change(roleSelect, { target: { value: 'VIEWER' } })

    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.getByText('MFA will no longer be required by this role.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save role change' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel role change' }))
    expect(roleSelect).toHaveValue('ANALYST')
    expect(screen.queryByText('MFA will no longer be required by this role.')).not.toBeInTheDocument()

    fireEvent.change(roleSelect, { target: { value: 'VIEWER' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save role change' }))
    expect(screen.getByText(/review this role change/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm role change' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      `/api/admin/users/${account.id}/role`,
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ role: 'VIEWER' }) }),
    ))
    expect(await screen.findByRole('status')).toHaveTextContent('Role for SOC Analyst changed to VIEWER.')
  })

  it('shows setup resend only when the account is still waiting to set a password', () => {
    const pendingAccount = {
      ...account,
      id: 'c3d3d9e7-7a8d-40ed-b4b4-4d7f2b4cb23d',
      display_name: 'Pending Analyst',
      email: 'pending@example.test',
      email_verified: false,
      setup_status: 'pending' as const,
    }
    render(<UserManagementWorkspace initialAccounts={[pendingAccount]} />)

    fireEvent.click(screen.getByRole('button', { name: 'View details for Pending Analyst' }))

    expect(screen.getByRole('button', { name: 'Resend setup for Pending Analyst' })).toBeInTheDocument()
    expect(screen.getByText('Password setup is pending.')).toBeInTheDocument()
  })

  it('does not expose self role or status mutations when the current account is known', () => {
    render(<UserManagementWorkspace initialAccounts={[account]} currentAccountId={account.id} />)

    fireEvent.click(screen.getByRole('button', { name: 'View details for SOC Analyst' }))

    expect(screen.getByText('Your own role cannot be changed here.')).toBeInTheDocument()
    expect(screen.getByText('Your own account cannot be disabled here.')).toBeInTheDocument()
    expect(screen.getByLabelText('Role for SOC Analyst')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Disable SOC Analyst' })).not.toBeInTheDocument()
  })

  it('distinguishes an empty tenant from a filtered-empty result', () => {
    render(<UserManagementWorkspace initialAccounts={[]} />)
    expect(screen.getByText('No managed accounts yet. Create an account to begin.')).toBeInTheDocument()

    cleanup()
    render(<UserManagementWorkspace initialAccounts={[account]} />)
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search accounts' }), { target: { value: 'nobody' } })

    expect(screen.getByText('No accounts match “nobody”.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear account search' }))
    expect(screen.getByText('1 of 1 account shown')).toBeInTheDocument()
  })

  it('labels a pending managed-email change as pending and replaceable', () => {
    const pendingEmailAccount = {
      ...account,
      pending_email: 'new-analyst@example.test',
    }
    render(<UserManagementWorkspace initialAccounts={[pendingEmailAccount]} />)

    fireEvent.click(screen.getByRole('button', { name: 'View details for SOC Analyst' }))

    expect(screen.getByText('Change pending: new-analyst@example.test')).toBeInTheDocument()
    expect(screen.getByText(/Submitting another address replaces the pending request/i)).toBeInTheDocument()
  })

  it('submits only email, display name, and role for account creation', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ account_id: account.id }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<UserManagementWorkspace initialAccounts={[]} />)

    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    const dialog = screen.getByRole('dialog', { name: 'Create account' })

    fireEvent.change(within(dialog).getByLabelText('Account email'), {
      target: { value: 'new@example.test' },
    })
    fireEvent.change(within(dialog).getByLabelText('Display name'), {
      target: { value: 'New Viewer' },
    })
    fireEvent.change(within(dialog).getByLabelText('Role'), {
      target: { value: 'VIEWER' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Create account' }))

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
    render(<UserManagementWorkspace initialAccounts={[{ ...account, setup_status: 'pending' }]} />)

    fireEvent.click(screen.getByRole('button', { name: 'View details for SOC Analyst' }))

    const disableButton = screen.getByRole('button', { name: 'Disable SOC Analyst' })
    fireEvent.click(disableButton)

    expect(screen.getByText('Disabling an account blocks sign-in until it is enabled again.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm disable SOC Analyst' })).not.toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: 'Confirm disable SOC Analyst' }))

    await waitFor(() => expect(disableButton).toBeDisabled())
    expect(screen.getByRole('button', { name: 'Resend setup for SOC Analyst' })).not.toBeDisabled()

    resolveFetch?.({ ok: true, json: async () => ({ accounts: [account] }) })
  })
})
