'use client'

import { useState } from 'react'

import { authFieldClass, authHeadingClass, authLinkClass, authPrimaryButtonClass } from '@/components/auth/authStyles'

export function MfaRecoveryForm() {
  const [mode, setMode] = useState<'backup' | 'email'>('backup')
  const [code, setCode] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submitBackup() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/recovery/backup', {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ code }),
      })
      if (!response.ok) throw new Error((await response.json()).error?.message ?? 'Recovery failed.')
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
      if (!response.ok) throw new Error((await response.json()).error?.message ?? 'Recovery email unavailable.')
      setMode('email')
      setMessage('If recovery is available, a code has been sent to your verified email.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Recovery email unavailable.')
    } finally {
      setBusy(false)
    }
  }

  async function verifyEmail() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/recovery/email/verify', {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ code }),
      })
      if (!response.ok) throw new Error((await response.json()).error?.message ?? 'Recovery failed.')
      window.location.assign('/mfa/enroll')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Recovery failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="w-full max-w-[400px] space-y-5" aria-labelledby="mfa-recovery-heading">
      <div>
        <h1 id="mfa-recovery-heading" className={authHeadingClass}>Recover authenticator access</h1>
        <p className="mt-2 text-sm text-text-secondary">Recovery is temporary. You must enroll a new authenticator before entering the dashboard.</p>
      </div>
      {mode === 'backup' ? (
        <>
          <label htmlFor="backup-code" className="block text-sm text-text-secondary">Backup code</label>
          <input id="backup-code" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} className={'font-mono ' + authFieldClass} />
          <button type="button" onClick={submitBackup} disabled={busy || !code} className={authPrimaryButtonClass}>Use backup code</button>
          <button type="button" onClick={requestEmail} disabled={busy} className={authLinkClass}>Send a recovery code to verified email</button>
        </>
      ) : (
        <>
          <p className="text-sm text-text-secondary">{message}</p>
          <label htmlFor="email-recovery-code" className="block text-sm text-text-secondary">Six-digit recovery code</label>
          <input id="email-recovery-code" inputMode="numeric" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))} className={'font-mono ' + authFieldClass} />
          <button type="button" onClick={verifyEmail} disabled={busy || code.length !== 6} className={authPrimaryButtonClass}>Verify recovery code</button>
        </>
      )}
      {error && <p role="alert" className="text-sm text-status-danger">{error}</p>}
    </section>
  )
}
