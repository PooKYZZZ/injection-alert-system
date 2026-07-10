'use client'

import { useState, type FormEvent } from 'react'

import type { SafeManagedAccount } from './contract'

type Role = 'ADMIN' | 'ANALYST' | 'VIEWER'

const fieldClass =
  'h-10 rounded-md border border-border-light bg-surface-inset px-3 text-sm text-text-primary outline-none transition-colors focus:border-accent-action'
const secondaryButton =
  'rounded-md border border-border-light px-3 py-1.5 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary disabled:opacity-50'

function mfaLabel(status: SafeManagedAccount['mfa_status']): string {
  if (status === 'active') return 'Active'
  if (status === 'not_required') return 'Not required'
  return 'Enrollment required'
}

export function UserManagementWorkspace({
  initialAccounts,
}: {
  initialAccounts: SafeManagedAccount[]
}) {
  const [accounts, setAccounts] = useState(initialAccounts)
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [role, setRole] = useState<Role>('VIEWER')
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [pendingEmails, setPendingEmails] = useState<Record<string, string>>({})

  async function refreshAccounts() {
    const response = await fetch('/api/admin/users', { cache: 'no-store' })
    if (!response.ok) return
    const payload = (await response.json()) as { accounts: SafeManagedAccount[] }
    setAccounts(payload.accounts)
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
      await refreshAccounts()
    } catch {
      setNotice('Unable to create the account. Confirm recent TOTP authentication and try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-[1500px] flex-col gap-8">
      <header className="flex flex-col gap-2 border-b border-border-light pb-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent-action">
          Access administration
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-text-primary">
          User Management
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-text-secondary">
          Create named accounts and manage verified identity state. Users choose their own password from a short-lived setup link.
        </p>
      </header>

      <section aria-labelledby="create-account-title" className="grid gap-5 border-b border-border-light pb-8 lg:grid-cols-[260px_1fr]">
        <div>
          <h2 id="create-account-title" className="text-base font-semibold text-text-primary">
            Create account
          </h2>
          <p className="mt-2 text-sm leading-5 text-text-secondary">
            ADMIN and ANALYST accounts require TOTP. VIEWER accounts remain password-only for this thesis scope.
          </p>
        </div>
        <form onSubmit={createAccount} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[1.3fr_1fr_180px_auto]">
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
          <button disabled={pending} className="mt-auto h-10 rounded-md bg-accent-action px-4 text-sm font-semibold text-surface-shell transition-opacity hover:opacity-90 disabled:opacity-50" type="submit">
            {pending ? 'Creating…' : 'Create account'}
          </button>
        </form>
        {notice ? <p className="lg:col-start-2 text-sm text-text-secondary" role="status">{notice}</p> : null}
      </section>

      <section aria-labelledby="accounts-title" className="min-w-0">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 id="accounts-title" className="text-base font-semibold text-text-primary">Accounts</h2>
            <p className="mt-1 text-xs text-text-secondary">{accounts.length} named account{accounts.length === 1 ? '' : 's'}</p>
          </div>
          <button type="button" className={secondaryButton} onClick={() => void refreshAccounts()}>Refresh</button>
        </div>
        <div className="overflow-x-auto border-y border-border-light">
          <table className="w-full min-w-[1050px] border-collapse text-left text-sm">
            <thead className="bg-surface-panel text-[10px] uppercase tracking-[0.14em] text-text-muted">
              <tr>
                {['Account', 'Role', 'Email', 'MFA', 'Status', 'Created', 'Actions'].map((heading) => (
                  <th key={heading} className="px-4 py-3 font-semibold">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light">
              {accounts.map((account) => (
                <tr key={account.id} className="bg-surface-page transition-colors hover:bg-surface-panel/60">
                  <td className="px-4 py-4 font-medium text-text-primary">{account.display_name}</td>
                  <td className="px-4 py-4">
                    <select
                      aria-label={`Role for ${account.display_name}`}
                      className="rounded border border-border-light bg-surface-inset px-2 py-1 text-xs text-text-primary"
                      value={account.role}
                      onChange={(event) => void mutate(`/api/admin/users/${account.id}/role`, 'PATCH', { role: event.target.value }).then(refreshAccounts).catch(() => setNotice('Role change failed. Recent TOTP authentication is required.'))}
                    >
                      <option value="VIEWER">VIEWER</option><option value="ANALYST">ANALYST</option><option value="ADMIN">ADMIN</option>
                    </select>
                  </td>
                  <td className="px-4 py-4 text-text-secondary">
                    <div>{account.email}</div>
                    <div className="mt-1 text-[11px] text-text-muted">{account.email_verified ? 'Verified' : 'Unverified'}{account.pending_email ? ` · Pending ${account.pending_email}` : ''}</div>
                  </td>
                  <td className="px-4 py-4 text-text-secondary">{mfaLabel(account.mfa_status)}</td>
                  <td className="px-4 py-4"><span className={account.enabled ? 'text-status-success' : 'text-status-danger'}>{account.enabled ? 'Enabled' : 'Disabled'}</span></td>
                  <td className="px-4 py-4 text-text-secondary">{new Date(account.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap gap-2">
                      <button className={secondaryButton} type="button" onClick={() => void mutate(`/api/admin/users/${account.id}/status`, 'PATCH', { enabled: !account.enabled }).then(refreshAccounts).catch(() => setNotice('Status change failed.'))}>{account.enabled ? 'Disable' : 'Enable'}</button>
                      <button className={secondaryButton} type="button" onClick={() => void mutate(`/api/admin/users/${account.id}/resend-setup`, 'POST').then(() => setNotice('Setup email queued.')).catch(() => setNotice('Setup email could not be queued.'))}>Resend setup</button>
                      <input aria-label={`New email for ${account.display_name}`} className="w-48 rounded border border-border-light bg-surface-inset px-2 py-1 text-xs text-text-primary" type="email" placeholder="New verified email" value={pendingEmails[account.id] ?? ''} onChange={(event) => setPendingEmails((current) => ({ ...current, [account.id]: event.target.value }))} />
                      <button className={secondaryButton} type="button" onClick={() => void mutate(`/api/admin/users/${account.id}/email`, 'POST', { email: pendingEmails[account.id] ?? '' }).then(() => setNotice('Verification email queued to the proposed address.')).catch(() => setNotice('Email change request failed.'))}>Verify new email</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
