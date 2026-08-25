'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { useMemo, useState, type FormEvent } from 'react'

import { formatStableDateTime } from '@/lib/date-time'

import { AccountActionsDialog } from './AccountActionsDialog'
import {
  managedAccountsResponseSchema,
  type SafeManagedAccount,
} from './contract'

type Role = 'ADMIN' | 'ANALYST' | 'VIEWER'
type AccountAction = 'role' | 'status' | 'setup' | 'mfa' | 'email'

function actionKey(accountId: string, action: AccountAction): string {
  return `${accountId}:${action}`
}

function mfaLabel(status: SafeManagedAccount['mfa_status']): string {
  if (status === 'active') return 'Active'
  if (status === 'not_required') return 'Not required'
  return 'Enrollment required'
}

const fieldClass =
  'h-10 rounded-md border border-border-light bg-surface-inset px-3 text-sm text-text-primary outline-none transition-colors focus:border-accent-action'
const secondaryButton =
  'rounded-md border border-border-light px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50'

export function UserManagementWorkspace({
  initialAccounts,
  currentAccountId,
}: {
  initialAccounts: SafeManagedAccount[]
  currentAccountId?: string
}) {
  const [accounts, setAccounts] = useState(initialAccounts)
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [role, setRole] = useState<Role>('VIEWER')
  const [createOpen, setCreateOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [pendingEmails, setPendingEmails] = useState<Record<string, string>>({})
  const [refreshPending, setRefreshPending] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [pendingActions, setPendingActions] = useState<Record<string, boolean>>({})
  const [search, setSearch] = useState('')
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null)

  const selectedAccount = accounts.find((account) => account.id === selectedAccountId) ?? null
  const filteredAccounts = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return accounts
    return accounts.filter((account) => [
      account.display_name,
      account.email,
      account.pending_email ?? '',
      account.role,
      account.enabled ? 'enabled' : 'disabled',
      mfaLabel(account.mfa_status),
      account.setup_status === 'pending' ? 'setup pending' : 'setup complete',
    ].some((value) => value.toLowerCase().includes(query)))
  }, [accounts, search])

  const enabledCount = accounts.filter((account) => account.enabled).length
  const mfaRequiredCount = accounts.filter((account) => account.mfa_status !== 'not_required').length

  async function refreshAccounts() {
    setRefreshPending(true)
    setRefreshError(null)
    try {
      const response = await fetch('/api/admin/users', { cache: 'no-store' })
      if (!response.ok) throw new Error('refresh_failed')
      const payload = managedAccountsResponseSchema.parse(await response.json())
      setAccounts(payload.accounts)
    } catch {
      setRefreshError('Unable to refresh account list. The last loaded data is still shown.')
    } finally {
      setRefreshPending(false)
    }
  }

  async function mutate(url: string, method: 'POST' | 'PATCH', body?: object) {
    setNotice(null)
    const response = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
    if (!response.ok) throw new Error('request_failed')
  }

  async function runAction(
    accountId: string,
    action: AccountAction,
    operation: () => Promise<void>,
    successMessage: string,
    failureMessage: string,
  ) {
    const key = actionKey(accountId, action)
    setPendingActions((current) => ({ ...current, [key]: true }))
    setNotice(null)
    try {
      await operation()
      setNotice(successMessage)
    } catch {
      setNotice(failureMessage)
    } finally {
      setPendingActions((current) => {
        const next = { ...current }
        delete next[key]
        return next
      })
    }
  }

  async function createAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    try {
      await mutate('/api/admin/users', 'POST', {
        email,
        display_name: displayName,
        role,
      })
      setEmail('')
      setDisplayName('')
      setRole('VIEWER')
      setNotice('Account created. A password setup email is queued.')
      setCreateOpen(false)
      await refreshAccounts()
    } catch {
      setNotice('Unable to create the account. Confirm recent TOTP authentication and try again.')
    } finally {
      setPending(false)
    }
  }

  function runAccountAction(
    account: SafeManagedAccount,
    action: AccountAction,
    operation: () => Promise<void>,
    successMessage: string,
    failureMessage: string,
  ) {
    void runAction(account.id, action, operation, successMessage, failureMessage)
  }

  return (
    <div className="mx-auto flex w-full max-w-[1500px] flex-col gap-8">
      <header className="flex flex-col gap-4 border-b border-border-light pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent-action">Access administration</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-text-primary">User Management</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
            Review account access and verified identity state. Detailed actions open only for the account you select.
          </p>
        </div>
        <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
          <Dialog.Trigger asChild>
            <button type="button" className="h-10 rounded-md bg-accent-action px-4 text-sm font-semibold text-surface-shell transition-opacity hover:opacity-90">
              Create account
            </button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-40 bg-black/45" />
            <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,560px)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border-light bg-surface-shell p-6 shadow-2xl outline-none">
              <Dialog.Title className="text-xl font-semibold tracking-tight text-text-primary">Create account</Dialog.Title>
              <Dialog.Description className="mt-2 text-sm leading-5 text-text-secondary">
                Create a named account. The user chooses their password from a short-lived setup link.
              </Dialog.Description>
              <form onSubmit={createAccount} className="mt-6 grid gap-4">
                <label className="flex flex-col gap-1.5 text-xs font-medium text-text-secondary">
                  Account email
                  <input className={fieldClass} type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
                </label>
                <label className="flex flex-col gap-1.5 text-xs font-medium text-text-secondary">
                  Display name
                  <input className={fieldClass} value={displayName} onChange={(event) => setDisplayName(event.target.value)} required maxLength={120} />
                </label>
                <label className="flex flex-col gap-1.5 text-xs font-medium text-text-secondary">
                  Role
                  <select className={fieldClass} value={role} onChange={(event) => setRole(event.target.value as Role)}>
                    <option value="VIEWER">Viewer</option>
                    <option value="ANALYST">Analyst</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </label>
                <div className="mt-2 flex justify-end gap-2">
                  <Dialog.Close asChild>
                    <button type="button" className={secondaryButton}>Cancel</button>
                  </Dialog.Close>
                  <button disabled={pending} className="rounded-md bg-accent-action px-4 py-2 text-sm font-semibold text-surface-shell disabled:opacity-50" type="submit">
                    {pending ? 'Creating…' : 'Create account'}
                  </button>
                </div>
              </form>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      </header>

      <section aria-label="Account summary" className="grid grid-cols-2 gap-4 border-b border-border-light pb-6 sm:grid-cols-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-text-muted">Accounts</p>
          <p className="mt-1 font-mono text-xl font-semibold text-text-primary">{accounts.length}</p>
          <p className="mt-1 text-xs text-text-secondary">Named accounts</p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-text-muted">Enabled</p>
          <p className="mt-1 font-mono text-xl font-semibold text-text-primary">{enabledCount}</p>
          <p className="mt-1 text-xs text-text-secondary">Can sign in</p>
        </div>
        <div className="col-span-2 sm:col-span-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-text-muted">MFA scope</p>
          <p className="mt-1 font-mono text-xl font-semibold text-text-primary">{mfaRequiredCount}</p>
          <p className="mt-1 text-xs text-text-secondary">Accounts requiring MFA</p>
        </div>
      </section>

      {notice && !selectedAccount ? <p className="-mb-4 text-sm text-text-secondary" role="status">{notice}</p> : null}

      <section aria-labelledby="accounts-title" className="min-w-0">
        <div className="mb-4 flex flex-col gap-4 border-b border-border-light pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 id="accounts-title" className="text-base font-semibold text-text-primary">Accounts</h2>
            <p className="mt-1 text-xs text-text-secondary">{filteredAccounts.length} of {accounts.length} account{accounts.length === 1 ? '' : 's'} shown</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="sr-only" htmlFor="account-search">Search accounts</label>
            <input id="account-search" className={`${fieldClass} min-w-0 sm:w-72`} type="search" placeholder="Search by name, email, role, or status" value={search} onChange={(event) => setSearch(event.target.value)} />
            <button type="button" className={secondaryButton} aria-label="Refresh accounts" disabled={refreshPending} onClick={() => void refreshAccounts()}>
              {refreshPending ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
        </div>
        {refreshError ? <p className="mb-3 text-sm text-status-danger" role="alert">{refreshError}</p> : null}
        <p className="mb-2 text-xs text-text-muted">Select an account to review administrative actions. On narrow screens, scroll horizontally to view all fields.</p>
        <div className="overflow-x-auto border-y border-border-light">
          <table className="w-full min-w-[930px] border-collapse text-left text-sm">
            <caption className="sr-only">Managed accounts and their current access state.</caption>
            <thead className="bg-surface-panel text-[10px] uppercase tracking-[0.14em] text-text-muted">
              <tr>
                {['Account', 'Role', 'Access', 'Security', 'Created', 'Actions'].map((heading) => (
                  <th key={heading} scope="col" className="px-4 py-3 font-semibold">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light">
              {filteredAccounts.map((account) => (
                <tr key={account.id} className="bg-surface-page transition-colors hover:bg-surface-panel/60">
                  <td className="px-4 py-4">
                    <div className="font-medium text-text-primary">{account.display_name}</div>
                    <div className="mt-1 text-xs text-text-secondary">{account.email}</div>
                    {account.pending_email ? <div className="mt-1 text-xs text-status-warning">Email change pending: {account.pending_email}</div> : null}
                  </td>
                  <td className="px-4 py-4 font-mono text-xs text-text-secondary">{account.role}</td>
                  <td className="px-4 py-4">
                    <span className={account.enabled ? 'font-medium text-status-success' : 'font-medium text-status-danger'}>
                      {account.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <span className="mt-1 block text-xs text-text-muted">{account.email_verified ? 'Email verified' : 'Email unverified'}</span>
                    <span className="mt-1 block text-xs text-text-muted">{account.setup_status === 'pending' ? 'Setup pending' : 'Setup complete'}</span>
                  </td>
                  <td className="px-4 py-4 text-text-secondary">{mfaLabel(account.mfa_status)}</td>
                  <td className="px-4 py-4 text-text-secondary">{formatStableDateTime(account.created_at, 'Unknown date')}</td>
                  <td className="px-4 py-4">
                    <button type="button" className={secondaryButton} aria-label={`View details for ${account.display_name}`} onClick={() => setSelectedAccountId(account.id)}>
                      View details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredAccounts.length === 0 ? (
          accounts.length === 0 ? (
            <p className="border-b border-border-light px-4 py-8 text-sm text-text-secondary">No managed accounts yet. Create an account to begin.</p>
          ) : search.trim() ? (
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-light px-4 py-8">
              <p className="text-sm text-text-secondary">No accounts match “{search.trim()}”.</p>
              <button type="button" className={secondaryButton} onClick={() => setSearch('')}>Clear account search</button>
            </div>
          ) : (
            <p className="border-b border-border-light px-4 py-8 text-sm text-text-secondary">No managed accounts are available.</p>
          )
        ) : null}
      </section>

      <AccountActionsDialog
        key={`${selectedAccountId ?? 'closed'}-${selectedAccount?.role ?? 'closed'}-${selectedAccount ? 'open' : 'closed'}`}
        account={selectedAccount}
        currentAccountId={currentAccountId}
        notice={notice}
        open={selectedAccount !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedAccountId(null)
        }}
        pendingActions={pendingActions}
        pendingEmail={selectedAccount ? pendingEmails[selectedAccount.id] ?? '' : ''}
        onPendingEmailChange={(value) => {
          if (selectedAccount) setPendingEmails((current) => ({ ...current, [selectedAccount.id]: value }))
        }}
        onRoleChange={(nextRole) => {
          if (!selectedAccount) return
          runAccountAction(
            selectedAccount,
            'role',
            async () => {
              await mutate(`/api/admin/users/${selectedAccount.id}/role`, 'PATCH', { role: nextRole })
              await refreshAccounts()
            },
            `Role for ${selectedAccount.display_name} changed to ${nextRole}.`,
            `Role change for ${selectedAccount.display_name} failed. Recent TOTP authentication is required.`,
          )
        }}
        onToggleStatus={() => {
          if (!selectedAccount) return
          runAccountAction(
            selectedAccount,
            'status',
            async () => {
              await mutate(`/api/admin/users/${selectedAccount.id}/status`, 'PATCH', { enabled: !selectedAccount.enabled })
              await refreshAccounts()
            },
            selectedAccount.enabled
              ? `${selectedAccount.display_name} was disabled.`
              : `${selectedAccount.display_name} was enabled.`,
            `Status change for ${selectedAccount.display_name} failed.`,
          )
        }}
        onResendSetup={() => {
          if (!selectedAccount) return
          runAccountAction(
            selectedAccount,
            'setup',
            () => mutate(`/api/admin/users/${selectedAccount.id}/resend-setup`, 'POST'),
            `Password setup email queued for ${selectedAccount.display_name}.`,
            `Password setup email for ${selectedAccount.display_name} could not be queued.`,
          )
        }}
        onResetMfa={(reason) => {
          if (!selectedAccount) return
          runAccountAction(
            selectedAccount,
            'mfa',
            () => mutate(`/api/admin/users/${selectedAccount.id}/mfa-reset`, 'POST', { reason }),
            `MFA reset for ${selectedAccount.display_name} completed. The account must enroll a new authenticator.`,
            `MFA reset for ${selectedAccount.display_name} failed. Recent TOTP authentication is required.`,
          )
        }}
        onRequestEmail={() => {
          if (!selectedAccount) return
          runAccountAction(
            selectedAccount,
            'email',
            async () => {
              await mutate(`/api/admin/users/${selectedAccount.id}/email`, 'POST', { email: pendingEmails[selectedAccount.id] ?? '' })
              setPendingEmails((current) => ({ ...current, [selectedAccount.id]: '' }))
              await refreshAccounts()
            },
            `Verification email queued for ${selectedAccount.display_name}.`,
            `Email change request for ${selectedAccount.display_name} failed.`,
          )
        }}
      />
    </div>
  )
}
