'use client'

import { useState } from 'react'

export function MfaVerifyForm() {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/verify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.error?.message ?? 'Unable to verify authenticator code.')
      }
      window.location.assign('/dashboard')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to verify authenticator code.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="max-w-md space-y-5" aria-labelledby="mfa-verify-heading">
      <div>
        <h1 id="mfa-verify-heading" className="text-2xl font-semibold text-text-primary">Verify your authenticator</h1>
        <p className="mt-2 text-sm text-text-secondary">Enter the current six-digit code to finish signing in.</p>
      </div>
      <label htmlFor="mfa-code" className="block text-sm text-text-secondary">Authenticator code</label>
      <input id="mfa-code" inputMode="numeric" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))} className="w-full rounded-md border border-border-subtle bg-surface-raised px-3 py-2 font-mono text-text-primary" />
      <button type="button" onClick={submit} disabled={busy || code.length !== 6} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base disabled:opacity-60">
        {busy ? 'Verifying…' : 'Continue'}
      </button>
      {error && <p role="alert" className="text-sm text-status-danger">{error}</p>}
    </section>
  )
}
