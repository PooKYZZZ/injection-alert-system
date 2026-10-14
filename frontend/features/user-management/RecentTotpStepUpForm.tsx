'use client'

import { useState } from 'react'

import { authFieldClass, authHeadingClass, authPrimaryButtonClass } from '@/components/auth/authStyles'

export function RecentTotpStepUpForm({ redirectTo }: { redirectTo: string }) {
  const [started, setStarted] = useState(false)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const errorId = 'step-up-error'

  async function begin() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/step-up', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.error?.message ?? 'Step-up is unavailable.')
      setStarted(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Step-up is unavailable.')
    } finally {
      setBusy(false)
    }
  }

  async function verify() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/step-up/verify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code, redirect_to: redirectTo }),
      })
      const payload = await response.json().catch(() => null)
      if (!response.ok) throw new Error(payload?.error?.message ?? 'The authenticator code is invalid.')
      window.location.assign(redirectTo)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The authenticator code is invalid.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="w-full max-w-[400px] space-y-5" aria-labelledby="step-up-heading">
      <div>
        <h1 id="step-up-heading" className={authHeadingClass}>Confirm sensitive action</h1>
        <p className="mt-2 text-sm text-text-secondary">Sensitive account changes require a fresh authenticator check. Sign-in MFA and this step-up are separate security events.</p>
        <p className="mt-2 text-xs leading-5 text-text-muted">After verification, return to User Management and deliberately submit the action again. The verification window is 10 minutes.</p>
      </div>
      {!started ? (
        <button type="button" onClick={begin} disabled={busy} className={authPrimaryButtonClass}>
          {busy ? 'Preparing…' : 'Start verification'}
        </button>
      ) : (
        <>
          <label className="block text-sm text-text-secondary" htmlFor="step-up-code">Authenticator code</label>
          <input
            id="step-up-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            value={code}
            aria-describedby={error ? errorId : undefined}
            aria-invalid={error ? 'true' : undefined}
            onChange={(event) => {
              setCode(event.target.value.replace(/\D/g, ''))
              if (error) setError(null)
            }}
            className={'max-w-xs font-mono ' + authFieldClass}
          />
          <button type="button" onClick={verify} disabled={busy || code.length !== 6} className={authPrimaryButtonClass}>
            {busy ? 'Verifying…' : 'Verify and continue'}
          </button>
        </>
      )}
      {error && <p id={errorId} role="alert" className="text-sm text-status-danger">{error}</p>}
    </section>
  )
}
