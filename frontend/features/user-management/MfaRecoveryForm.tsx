'use client'

import { useState, type FormEvent } from 'react'

import {
  authFieldClass,
  authHeadingClass,
  authLinkClass,
  authPrimaryButtonClass,
  authSecondaryButtonClass,
} from '@/components/auth/authStyles'

const errorId = 'mfa-recovery-error'

export function MfaRecoveryForm() {
  const [mode, setMode] = useState<'backup' | 'email'>('backup')
  const [code, setCode] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submitBackup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/recovery/backup', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.error?.message ?? 'Recovery failed.')
      }
      window.location.assign('/mfa/enroll')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Recovery failed.')
    } finally {
      setBusy(false)
    }
  }

  async function requestEmail() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/recovery/email/request', { method: 'POST' })
      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.error?.message ?? 'Recovery email unavailable.')
      }
      setMode('email')
      setCode('')
      setMessage('If recovery is available, a code has been sent to your verified email.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Recovery email unavailable.')
    } finally {
      setBusy(false)
    }
  }

  async function verifyEmail(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/recovery/email/verify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.error?.message ?? 'Recovery failed.')
      }
      window.location.assign('/mfa/enroll')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Recovery failed.')
    } finally {
      setBusy(false)
    }
  }

  function switchToBackup() {
    setMode('backup')
    setCode('')
    setMessage(null)
    setError(null)
  }

  return (
    <section className="w-full max-w-[400px] space-y-6" aria-labelledby="mfa-recovery-heading">
      <div>
        <h1 id="mfa-recovery-heading" className={authHeadingClass}>Recover authenticator access</h1>
        <p className="mt-2 text-sm leading-6 text-text-secondary">Recovery is temporary. You must enroll a new authenticator before entering the dashboard.</p>
      </div>

      {mode === 'backup' ? (
        <>
          <form
            aria-label="Backup code recovery"
            aria-busy={busy || undefined}
            aria-describedby={error ? errorId : 'backup-code-help'}
            onSubmit={submitBackup}
            className="grid gap-3"
          >
            <div className="grid gap-1.5">
              <label htmlFor="backup-code" className="text-sm font-medium text-text-secondary">Backup code</label>
              <p id="backup-code-help" className="text-xs leading-5 text-text-muted">Use one unused code from your saved recovery codes.</p>
              <input
                id="backup-code"
                type="text"
                autoComplete="off"
                required
                value={code}
                aria-describedby={error ? 'backup-code-help mfa-recovery-error' : 'backup-code-help'}
                aria-invalid={error ? 'true' : undefined}
                onChange={(event) => {
                  setCode(event.target.value.toUpperCase())
                  if (error) setError(null)
                }}
                className={`font-mono ${authFieldClass}`}
              />
            </div>
            <button type="submit" disabled={busy || !code.trim()} className={authPrimaryButtonClass}>
              {busy ? 'Checking…' : 'Use backup code'}
            </button>
          </form>
          <div className="grid gap-3 border-t border-border-light pt-5">
            <p className="text-xs leading-5 text-text-muted">No backup code available?</p>
            <button type="button" onClick={() => void requestEmail()} disabled={busy} className={authSecondaryButtonClass}>
              {busy ? 'Requesting…' : 'Email me a recovery code'}
            </button>
          </div>
        </>
      ) : (
        <>
          {message ? <p role="status" aria-live="polite" className="text-sm leading-5 text-text-secondary">{message}</p> : null}
          <form
            aria-label="Email recovery code verification"
            aria-busy={busy || undefined}
            aria-describedby={error ? `${errorId} email-recovery-code-help` : 'email-recovery-code-help'}
            onSubmit={verifyEmail}
            className="grid gap-3"
          >
            <div className="grid gap-1.5">
              <label htmlFor="email-recovery-code" className="text-sm font-medium text-text-secondary">Six-digit recovery code</label>
              <p id="email-recovery-code-help" className="text-xs leading-5 text-text-muted">Enter the code from your verified email.</p>
              <input
                id="email-recovery-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                required
                pattern={'\\d{6}'}
                maxLength={6}
                value={code}
                aria-describedby={error ? 'email-recovery-code-help mfa-recovery-error' : 'email-recovery-code-help'}
                aria-invalid={error ? 'true' : undefined}
                onChange={(event) => {
                  setCode(event.target.value.replace(/\D/g, ''))
                  if (error) setError(null)
                }}
                className={`font-mono ${authFieldClass}`}
              />
            </div>
            <button type="submit" disabled={busy || code.length !== 6} className={authPrimaryButtonClass}>
              {busy ? 'Verifying…' : 'Verify recovery code'}
            </button>
          </form>
          <div className="grid gap-3 border-t border-border-light pt-5">
            <button type="button" onClick={() => void requestEmail()} disabled={busy} className={authSecondaryButtonClass}>
              {busy ? 'Requesting…' : 'Email me a new recovery code'}
            </button>
            <button type="button" onClick={switchToBackup} className={authLinkClass}>Use a backup code</button>
          </div>
        </>
      )}

      {error ? <p id={errorId} role="alert" className="text-sm leading-5 text-status-danger">{error}</p> : null}
      <a href="/mfa/verify" className={'inline-flex ' + authLinkClass}>Back to authenticator verification</a>
    </section>
  )
}
