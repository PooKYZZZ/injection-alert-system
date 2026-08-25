'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { useState } from 'react'

import type { SafeManagedAccount } from './contract'

type Role = 'ADMIN' | 'ANALYST' | 'VIEWER'
type AccountAction = 'role' | 'status' | 'setup' | 'mfa' | 'email'

type Props = {
  account: SafeManagedAccount | null
  currentAccountId?: string
  notice?: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  pendingActions: Record<string, boolean>
  pendingEmail: string
  onPendingEmailChange: (value: string) => void
  onRoleChange: (role: Role) => void
  onToggleStatus: () => void
  onResendSetup: () => void
  onResetMfa: (reason: string) => void
  onRequestEmail: () => void
}

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

export function AccountActionsDialog({
  account,
  currentAccountId,
  notice,
  open,
  onOpenChange,
  pendingActions,
  pendingEmail,
  onPendingEmailChange,
  onRoleChange,
  onToggleStatus,
  onResendSetup,
  onResetMfa,
  onRequestEmail,
}: Props) {
  const [confirmingDisable, setConfirmingDisable] = useState(false)
  const [confirmingRole, setConfirmingRole] = useState(false)
  const [draftRole, setDraftRole] = useState<Role>(account?.role ?? 'VIEWER')
  const [resetReason, setResetReason] = useState('')

  if (!account) return null

  const isSelf = currentAccountId === account.id
  const roleDirty = draftRole !== account.role
  const rolePending = Boolean(pendingActions[actionKey(account.id, 'role')])
  const statusPending = Boolean(pendingActions[actionKey(account.id, 'status')])
  const setupPending = Boolean(pendingActions[actionKey(account.id, 'setup')])
  const mfaPending = Boolean(pendingActions[actionKey(account.id, 'mfa')])
  const emailPending = Boolean(pendingActions[actionKey(account.id, 'email')])

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/45" />
        <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-[min(100vw,480px)] flex-col overflow-y-auto border-l border-border-light bg-surface-shell shadow-2xl outline-none max-sm:inset-x-0 max-sm:inset-y-auto max-sm:max-h-[92vh] max-sm:w-full max-sm:rounded-t-2xl max-sm:border-l-0 max-sm:border-t">
          <div className="flex items-start justify-between gap-5 border-b border-border-light px-6 py-5">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent-action">Account details</p>
              <Dialog.Title className="mt-2 truncate text-xl font-semibold tracking-tight text-text-primary">
                {account.display_name}
              </Dialog.Title>
              <Dialog.Description className="mt-1 break-all text-sm text-text-secondary">
                {account.email}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button type="button" className={secondaryButton} aria-label="Close account details">
                <X size={16} aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          {notice ? <p className="border-b border-border-light px-6 py-3 text-sm text-text-secondary" role="status">{notice}</p> : null}

          <div className="flex flex-1 flex-col gap-7 px-6 py-6">
            <section aria-labelledby="account-access-heading">
              <h2 id="account-access-heading" className="text-sm font-semibold text-text-primary">Account access</h2>
              <dl className="mt-3 divide-y divide-border-light border-y border-border-light text-sm">
                <div className="flex items-center justify-between gap-4 py-3">
                  <dt className="text-text-secondary">Role</dt>
                  <dd>
                    <label className="sr-only" htmlFor={`role-${account.id}`}>Role for {account.display_name}</label>
                    <select
                      id={`role-${account.id}`}
                      className={`${fieldClass} h-9 py-1 text-xs`}
                      value={draftRole}
                      disabled={rolePending || isSelf}
                      onChange={(event) => {
                        setDraftRole(event.target.value as Role)
                        setConfirmingRole(false)
                      }}
                    >
                      <option value="VIEWER">VIEWER</option>
                      <option value="ANALYST">ANALYST</option>
                      <option value="ADMIN">ADMIN</option>
                    </select>
                  </dd>
                </div>
                {isSelf ? (
                  <p className="py-3 text-xs leading-5 text-text-muted">Your own role cannot be changed here.</p>
                ) : roleDirty ? (
                  <div className="border-t border-border-light py-3">
                    <p className="text-xs leading-5 text-text-secondary">
                      {draftRole === 'VIEWER' && account.role !== 'VIEWER'
                        ? 'MFA will no longer be required by this role.'
                        : draftRole !== 'VIEWER' && account.role === 'VIEWER'
                          ? 'This role requires MFA enrollment before protected work.'
                          : 'This changes the account’s access role.'}
                    </p>
                    {confirmingRole ? (
                      <div className="mt-3 border-t border-border-light pt-3">
                        <p className="text-xs leading-5 text-text-secondary">Review this role change before saving. Active sessions are rechecked against the updated account authorization.</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="rounded-md bg-accent-action px-3 py-2 text-xs font-semibold text-surface-shell disabled:opacity-50"
                            aria-label="Confirm role change"
                            disabled={rolePending}
                            onClick={() => {
                              onRoleChange(draftRole)
                              setConfirmingRole(false)
                            }}
                          >
                            {rolePending ? 'Saving…' : 'Confirm role change'}
                          </button>
                          <button type="button" className={secondaryButton} onClick={() => setConfirmingRole(false)}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button type="button" className={secondaryButton} onClick={() => setConfirmingRole(true)}>
                          Save role change
                        </button>
                        <button type="button" className={secondaryButton} onClick={() => setDraftRole(account.role)}>
                          Cancel role change
                        </button>
                      </div>
                    )}
                  </div>
                ) : null}
                <div className="flex items-center justify-between gap-4 py-3">
                  <dt className="text-text-secondary">Account status</dt>
                  <dd className={account.enabled ? 'font-medium text-status-success' : 'font-medium text-status-danger'}>
                    {account.enabled ? 'Enabled' : 'Disabled'}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4 py-3">
                  <dt className="text-text-secondary">MFA</dt>
                  <dd className="text-right text-text-primary">{mfaLabel(account.mfa_status)}</dd>
                </div>
                <div className="flex items-center justify-between gap-4 py-3">
                  <dt className="text-text-secondary">Email</dt>
                    <dd className="text-right text-text-primary">
                      {account.email_verified ? 'Verified' : 'Unverified'}
                    {account.pending_email ? <span className="block text-xs text-status-warning">Change pending: {account.pending_email}</span> : null}
                  </dd>
                </div>
              </dl>
            </section>

            <section aria-labelledby="account-security-heading">
              <h2 id="account-security-heading" className="text-sm font-semibold text-text-primary">Account security</h2>
              <p className="mt-1 text-xs leading-5 text-text-secondary">Use these actions only when the account state needs administrative intervention.</p>
              <div className="mt-4 flex flex-col gap-3">
                {isSelf ? (
                  <p className="text-xs leading-5 text-text-muted">Your own account cannot be disabled here.</p>
                ) : account.enabled ? (
                  <div className="rounded-md border border-status-danger/35 bg-status-danger/5 p-3">
                    <button
                      type="button"
                      className="text-sm font-semibold text-status-danger hover:underline disabled:opacity-50"
                      aria-label={`Disable ${account.display_name}`}
                      disabled={statusPending}
                      onClick={() => setConfirmingDisable(true)}
                    >
                      {statusPending ? 'Disabling…' : 'Disable account'}
                    </button>
                    {confirmingDisable ? (
                      <div className="mt-3 border-t border-status-danger/20 pt-3">
                        <p className="text-xs leading-5 text-text-secondary">Disabling an account blocks sign-in until it is enabled again.</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="rounded-md bg-status-danger px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                            aria-label={`Confirm disable ${account.display_name}`}
                            disabled={statusPending}
                            onClick={() => {
                              setConfirmingDisable(false)
                              onToggleStatus()
                            }}
                          >
                            {statusPending ? 'Disabling…' : 'Confirm disable'}
                          </button>
                          <button type="button" className={secondaryButton} onClick={() => setConfirmingDisable(false)}>
                            Keep enabled
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <button
                    type="button"
                    className={secondaryButton}
                    aria-label={`Enable ${account.display_name}`}
                    disabled={statusPending}
                    onClick={onToggleStatus}
                  >
                    {statusPending ? 'Enabling…' : 'Enable account'}
                  </button>
                )}

                <div className="border-t border-border-light pt-4">
                  <p className="text-xs leading-5 text-text-secondary">
                    {account.setup_status === 'pending' ? 'Password setup is pending.' : 'Password setup is complete.'}
                  </p>
                  {account.setup_status === 'pending' && account.enabled ? (
                    <>
                      <button type="button" className={`${secondaryButton} mt-3`} aria-label={`Resend setup for ${account.display_name}`} disabled={setupPending} onClick={onResendSetup}>
                        {setupPending ? 'Queueing…' : 'Resend setup email'}
                      </button>
                      <p className="mt-2 text-xs text-text-muted">Sends a new short-lived password setup link.</p>
                    </>
                  ) : null}
                </div>

                {!isSelf && account.mfa_status !== 'not_required' ? (
                  <div className="border-t border-border-light pt-4">
                    <label className="flex flex-col gap-1.5 text-xs font-medium text-text-secondary" htmlFor={`mfa-reset-${account.id}`}>
                      Reset MFA
                      <span className="font-normal text-text-muted">A reason is recorded with the reset request.</span>
                      <input id={`mfa-reset-${account.id}`} className={fieldClass} value={resetReason} onChange={(event) => setResetReason(event.target.value)} placeholder="Reason for MFA reset" maxLength={240} />
                    </label>
                    <button
                      type="button"
                      className={`${secondaryButton} mt-2`}
                      aria-label={`Reset MFA for ${account.display_name}`}
                      disabled={mfaPending || !resetReason.trim()}
                      onClick={() => {
                        onResetMfa(resetReason.trim())
                        setResetReason('')
                      }}
                    >
                      {mfaPending ? 'Resetting…' : 'Reset MFA'}
                    </button>
                  </div>
                ) : null}
              </div>
            </section>

            <section aria-labelledby="account-email-heading" className="border-t border-border-light pt-6">
              <h2 id="account-email-heading" className="text-sm font-semibold text-text-primary">Email verification</h2>
              <p className="mt-1 text-xs leading-5 text-text-secondary">Request a verification message for a proposed address. The current address remains in place until the flow completes.</p>
              {account.pending_email ? <p className="mt-2 text-xs leading-5 text-text-muted">Submitting another address replaces the pending request.</p> : null}
              <label className="mt-4 flex flex-col gap-1.5 text-xs font-medium text-text-secondary" htmlFor={`new-email-${account.id}`}>
                Proposed email
                <input id={`new-email-${account.id}`} className={fieldClass} type="email" value={pendingEmail} onChange={(event) => onPendingEmailChange(event.target.value)} placeholder="name@example.test" />
              </label>
              <button
                type="button"
                className={`${secondaryButton} mt-2`}
                aria-label={`Request email verification for ${account.display_name}`}
                disabled={emailPending || !pendingEmail.trim()}
                onClick={onRequestEmail}
              >
                {emailPending ? 'Queueing…' : 'Request verification'}
              </button>
            </section>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
