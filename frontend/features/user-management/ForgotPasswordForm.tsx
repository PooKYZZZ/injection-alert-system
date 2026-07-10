'use client'

import { useState } from 'react'

export function ForgotPasswordForm() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  async function submit() {
    await fetch('/api/auth/forgot-password', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email }),
    })
    setSent(true)
  }

  return (
    <section className="max-w-md space-y-5" aria-labelledby="forgot-password-heading">
      <h1 id="forgot-password-heading" className="text-2xl font-semibold text-text-primary">Forgot password</h1>
      <p className="text-sm text-text-secondary">Enter your email. If the account is eligible, a reset link will be sent.</p>
      <input aria-label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-md border border-border-subtle bg-surface-raised px-3 py-2 text-text-primary" />
      <button type="button" onClick={() => void submit()} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base">Send reset link</button>
      {sent && <p role="status" className="text-sm text-status-success">If the account is eligible, a reset link has been sent.</p>}
    </section>
  )
}
