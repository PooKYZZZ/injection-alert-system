'use client'

import { useState, type FormEvent } from 'react'

export function MfaVerifyForm() {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (code.length !== 6) return
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
      <form aria-labelledby="mfa-verify-heading" onSubmit={submit} className="space-y-5">
        <label htmlFor="mfa-code" className="block text-sm text-text-secondary">Authenticator code</label>
        <p id="mfa-code-help" className="text-xs text-text-muted">Use the current six-digit code from your authenticator app.</p>
        <input
          id="mfa-code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          autoFocus
          required
          pattern={'\\d{6}'}
          maxLength={6}
          value={code}
          aria-describedby={error ? 'mfa-code-help mfa-code-error' : 'mfa-code-help'}
          aria-invalid={error ? 'true' : undefined}
          onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
          className="w-full rounded-md border border-border-subtle bg-surface-raised px-3 py-2 font-mono text-text-primary"
        />
        <button type="submit" disabled={busy || code.length !== 6} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base disabled:opacity-60">
          {busy ? 'Verifying…' : 'Continue'}
        </button>
        {error && <p id="mfa-code-error" role="alert" className="text-sm text-status-danger">{error}</p>}
      </form>
    </section>
  )
}
