'use client'

import { useState } from 'react'

export function RecentTotpStepUpForm({ redirectTo }: { redirectTo: string }) {
  const [started, setStarted] = useState(false)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    <section className="max-w-md space-y-5" aria-labelledby="step-up-heading">
      <div>
        <h1 id="step-up-heading" className="text-2xl font-semibold text-text-primary">Confirm sensitive action</h1>
        <p className="mt-2 text-sm text-text-secondary">Enter a current authenticator code to continue.</p>
      </div>
      {!started ? (
        <button type="button" onClick={begin} disabled={busy} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base disabled:opacity-60">
          {busy ? 'Preparing…' : 'Start verification'}
        </button>
      ) : (
        <>
          <label className="block text-sm text-text-secondary" htmlFor="step-up-code">Authenticator code</label>
          <input id="step-up-code" inputMode="numeric" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))} className="w-full rounded-md border border-border-subtle bg-surface-raised px-3 py-2 font-mono text-text-primary" />
          <button type="button" onClick={verify} disabled={busy || code.length !== 6} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base disabled:opacity-60">
            {busy ? 'Verifying…' : 'Verify and continue'}
          </button>
        </>
      )}
      {error && <p role="alert" className="text-sm text-status-danger">{error}</p>}
    </section>
  )
}
