'use client'

import { useState } from 'react'

export function ResetPasswordForm({ token }: { token: string }) {
  const [password, setPassword] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    setError(null)
    const response = await fetch('/api/auth/reset-password', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ token, password }),
    })
    if (!response.ok) {
      setError('This reset link is invalid or expired.')
      return
    }
    setDone(true)
  }

  if (done) return <p role="status" className="text-sm text-status-success">Password reset complete. Sign in again.</p>
  return (
    <section className="max-w-md space-y-5" aria-labelledby="reset-password-heading">
      <h1 id="reset-password-heading" className="text-2xl font-semibold text-text-primary">Set a new password</h1>
      <p className="text-sm text-text-secondary">Use at least 15 characters. You will not be signed in automatically.</p>
      <input aria-label="New password" type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-md border border-border-subtle bg-surface-raised px-3 py-2 text-text-primary" />
      <button type="button" onClick={() => void submit()} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base">Reset password</button>
      {error && <p role="alert" className="text-sm text-status-danger">{error}</p>}
    </section>
  )
}
