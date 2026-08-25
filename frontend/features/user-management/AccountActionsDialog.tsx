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

function roleLabel(role: Role): string {
  if (role === 'ADMIN') return 'Admin'
  if (role === 'ANALYST') return 'Analyst'
  return 'Viewer'
}

function mfaLabel(status: SafeManagedAccount['mfa_status']): string {
  if (status === 'active') return 'Enrolled'
  if (status === 'not_required') return 'Not required'
  return 'Enrollment required'
}

const fieldClass =
  'h-10 rounded-md border border-border-light bg-surface-inset px-3 text-sm text-text-primary outline-none transition-colors focus:border-accent-action'
const secondaryButton =
  'rounded-md border border-border-light px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50'
const disclosureButton =
  'inline-flex min-h-9 items-center rounded-md border border-border-light px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-action focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50'

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
  const [editingRole, setEditingRole] = useState(false)
  const [confirmingDisable, setConfirmingDisable] = useState(false)
  const [confirmingRole, setConfirmingRole] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)
  const [emailOpen, setEmailOpen] = useState(false)
  const [dangerOpen, setDangerOpen] = useState(false)
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
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/30" />
        <Dialog.Content className="fixed inset-y-0 right-0 z-50 flex w-[min(100vw,520px)] flex-col overflow-y-auto border-l border-border-light bg-surface-panel shadow-2xl outline-none max-sm:inset-x-0 max-sm:inset-y-auto max-sm:max-h-[92vh] max-sm:w-full max-sm:rounded-t-2xl max-sm:border-l-0 max-sm:border-t">
          <div className="flex items-start justify-between gap-5 border-b border-border-light px-6 py-5">
            <div className="min-w-0">
              <Dialog.Title className="truncate text-xl font-semibold tracking-tight text-text-primary">
                {account.display_name}
              </Dialog.Title>
              <Dialog.Description className="mt-1 break-all text-sm text-text-secondary">
                {account.email}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border-light text-text-secondary transition-colors hover:bg-surface-inset hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-action focus-visible:outline-offset-2"
                aria-label="Close account details"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          {notice ? <p className="border-b border-border-light px-6 py-3 text-sm text-text-secondary" role="status">{notice}</p> : null}

          <div className="flex flex-1 flex-col gap-8 px-6 py-6">
            <section aria-labelledby="account-overview-heading">
              <h2 id="account-overview-heading" className="text-sm font-semibold text-text-primary">Account overview</h2>
              <dl className="mt-3 divide-y divide-border-light border-y border-border-light text-sm">
                <div className="flex items-center justify-between gap-4 py-3">
                  <dt className="text-text-secondary">Role</dt>
                  <dd className="flex items-center gap-3 text-right text-text-primary">
                    <span>{roleLabel(account.role)}</span>
                    {!isSelf ? (
                      <button
                        type="button"
                        className={disclosureButton}
                        aria-label={editingRole ? `Close role editor for ${account.display_name}` : `Edit role for ${account.display_name}`}
                        aria-expanded={editingRole}
                        onClick={() => {
                          setEditingRole((current) => !current)
                          setConfirmingRole(false)
                          setDraftRole(account.role)
                        }}
                      >
                        {editingRole ? 'Close editor' : 'Edit role'}
                      </button>
                    ) : null}
                  </dd>
                </div>
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
                <div className="flex items-center justify-between gap-4 py-3">
                  <dt className="text-text-secondary">Password setup</dt>
                  <dd className="text-right text-text-primary">{account.setup_status === 'pending' ? 'Pending' : 'Complete'}</dd>
                </div>
              </dl>

              {isSelf ? (
                <p className="mt-3 text-xs leading-5 text-text-muted">Your own role cannot be changed here.</p>
              ) : null}

              {editingRole && !isSelf ? (
                <div className="mt-4 border-l-2 border-accent-action pl-4">
                  <label className="flex flex-col gap-1.5 text-xs font-medium text-text-secondary" htmlFor={`role-${account.id}`}>
                    New access role
                    <select
                      id={`role-${account.id}`}
                      aria-label={`Role for ${account.display_name}`}
                      className={fieldClass}
                      value={draftRole}
                      disabled={rolePending}
                      onChange={(event) => {
                        setDraftRole(event.target.value as Role)
                        setConfirmingRole(false)
                      }}
                    >
                      <option value="VIEWER">Viewer</option>
                      <option value="ANALYST">Analyst</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  </label>
                  {roleDirty ? (
                    <p className="mt-2 text-xs leading-5 text-text-secondary">
                      {draftRole === 'VIEWER' && account.role !== 'VIEWER'
                        ? 'MFA will no longer be required by this role.'
                        : draftRole !== 'VIEWER' && account.role === 'VIEWER'
                          ? 'This role requires MFA enrollment before protected work.'
                          : 'This changes the account’s access role.'}
                    </p>
                  ) : null}
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
                      <button type="button" className={secondaryButton} disabled={!roleDirty} onClick={() => setConfirmingRole(true)}>
                        Save role change
                      </button>
                      <button type="button" className={secondaryButton} onClick={() => { setDraftRole(account.role); setEditingRole(false) }}>
                        Cancel role change
                      </button>
                    </div>
                  )}
                </div>
              ) : null}
            </section>

            <section aria-labelledby="administrative-actions-heading">
              <h2 id="administrative-actions-heading" className="text-sm font-semibold text-text-primary">Administrative actions</h2>
              <p className="mt-1 text-xs leading-5 text-text-secondary">Less frequent account changes stay closed until they are needed.</p>
              <div className="mt-4 divide-y divide-border-light border-y border-border-light">
                {account.setup_status === 'pending' && account.enabled ? (
                  <div className="flex items-start justify-between gap-4 py-4">
                    <div>
                      <h3 className="text-sm font-medium text-text-primary">Password setup</h3>
                      <p className="mt-1 text-xs leading-5 text-text-muted">Password setup is pending. Send a new short-lived link.</p>
                    </div>
                    <button type="button" className={secondaryButton} aria-label={`Resend setup for ${account.display_name}`} disabled={setupPending} onClick={onResendSetup}>
                      {setupPending ? 'Queueing…' : 'Resend email'}
                    </button>
                  </div>
                ) : null}

                {!isSelf && account.mfa_status !== 'not_required' ? (
                  <div className="py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-sm font-medium text-text-primary">Authenticator</h3>
                        <p className="mt-1 text-xs leading-5 text-text-muted">Reset only when the user has lost access to their authenticator.</p>
                      </div>
                      <button
                        type="button"
                        className={disclosureButton}
                        aria-label={resetOpen ? `Close authenticator reset for ${account.display_name}` : `Reset authenticator for ${account.display_name}`}
                        aria-expanded={resetOpen}
                        onClick={() => setResetOpen((current) => !current)}
                      >
                        {resetOpen ? 'Close reset' : 'Reset authenticator'}
                      </button>
                    </div>
                    {resetOpen ? (
                      <div className="mt-4 border-l-2 border-border-light pl-4">
                        <label className="flex flex-col gap-1.5 text-xs font-medium text-text-secondary" htmlFor={`mfa-reset-${account.id}`}>
                          Reason for reset
                          <span className="font-normal text-text-muted">This reason is recorded with the request.</span>
                          <input id={`mfa-reset-${account.id}`} className={fieldClass} value={resetReason} onChange={(event) => setResetReason(event.target.value)} placeholder="Explain why a reset is needed" maxLength={240} />
                        </label>
                        <button
                          type="button"
                          className={`${secondaryButton} mt-3`}
                          aria-label={`Reset MFA for ${account.display_name}`}
                          disabled={mfaPending || !resetReason.trim()}
                          onClick={() => {
                            onResetMfa(resetReason.trim())
                            setResetReason('')
                            setResetOpen(false)
                          }}
                        >
                          {mfaPending ? 'Resetting…' : 'Reset MFA'}
                        </button>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {!account.enabled && !isSelf ? (
                  <div className="flex items-start justify-between gap-4 py-4">
                    <div>
                      <h3 className="text-sm font-medium text-text-primary">Account access</h3>
                      <p className="mt-1 text-xs leading-5 text-text-muted">Re-enable this account to allow sign-in.</p>
                    </div>
                    <button type="button" className={secondaryButton} aria-label={`Enable ${account.display_name}`} disabled={statusPending} onClick={onToggleStatus}>
                      {statusPending ? 'Enabling…' : 'Enable account'}
                    </button>
                  </div>
                ) : null}
              </div>
              {isSelf ? <p className="mt-3 text-xs leading-5 text-text-muted">Your own account cannot be disabled here.</p> : null}
            </section>

            <section aria-labelledby="account-email-heading" className="border-t border-border-light pt-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 id="account-email-heading" className="text-sm font-semibold text-text-primary">Account email</h2>
                  <p className="mt-1 text-xs leading-5 text-text-secondary">The current address stays active until a new address completes verification.</p>
                </div>
                <button
                  type="button"
                  className={disclosureButton}
                  aria-label={emailOpen ? `Close email editor for ${account.display_name}` : `Change email address for ${account.display_name}`}
                  aria-expanded={emailOpen}
                  onClick={() => setEmailOpen((current) => !current)}
                >
                  {emailOpen ? 'Close editor' : 'Change email'}
                </button>
              </div>
              {emailOpen ? (
                <div className="mt-4 border-l-2 border-border-light pl-4">
                  {account.pending_email ? <p className="mb-3 text-xs leading-5 text-text-muted">Submitting another address replaces the pending request.</p> : null}
                  <label className="flex flex-col gap-1.5 text-xs font-medium text-text-secondary" htmlFor={`new-email-${account.id}`}>
                    New email address
                    <input id={`new-email-${account.id}`} className={fieldClass} type="email" value={pendingEmail} onChange={(event) => onPendingEmailChange(event.target.value)} placeholder="name@example.test" />
                  </label>
                  <button
                    type="button"
                    className={`${secondaryButton} mt-3`}
                    aria-label={`Request email verification for ${account.display_name}`}
                    disabled={emailPending || !pendingEmail.trim()}
                    onClick={onRequestEmail}
                  >
                    {emailPending ? 'Queueing…' : 'Request verification'}
                  </button>
                </div>
              ) : null}
            </section>

            {!isSelf ? (
              <section className="border-t border-status-danger/30 pt-5" aria-labelledby="danger-zone-heading">
                <button
                  id="danger-zone-heading"
                  type="button"
                  className="text-sm font-medium text-status-danger underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-action focus-visible:outline-offset-2"
                  aria-expanded={dangerOpen}
                  onClick={() => setDangerOpen((current) => !current)}
                >
                  Danger zone
                </button>
                {dangerOpen ? <div className="mt-3 border-l-2 border-status-danger/40 pl-4">
                  <p className="text-xs leading-5 text-text-secondary">Disabling blocks sign-in until the account is enabled again. This does not delete the account.</p>
                  {account.enabled ? (
                    <>
                      <button
                        type="button"
                        className="mt-3 text-sm font-semibold text-status-danger hover:underline disabled:opacity-50"
                        aria-label={`Disable ${account.display_name}`}
                        disabled={statusPending}
                        onClick={() => setConfirmingDisable(true)}
                      >
                        {statusPending ? 'Disabling…' : 'Disable account'}
                      </button>
                      {confirmingDisable ? (
                        <div className="mt-3 border-t border-status-danger/20 pt-3">
                          <p className="text-xs leading-5 text-text-secondary">Confirm only if this user should lose sign-in access now.</p>
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
                    </>
                  ) : null}
                </div> : null}
              </section>
            ) : null}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
