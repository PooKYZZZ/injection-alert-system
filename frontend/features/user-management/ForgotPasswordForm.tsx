'use client'

import { useState, type FormEvent } from 'react'

import { authFieldClass, authHeadingClass, authLinkClass, authPrimaryButtonClass } from '@/components/auth/authStyles'
export function ForgotPasswordForm() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setSent(false)
    setError(null)
    try {
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (!response.ok) throw new Error('request_failed')
      setSent(true)
    } catch {
      setError('Unable to send a reset link right now. Try again without leaving this page.')
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="w-full max-w-[400px] space-y-6" aria-labelledby="forgot-password-heading">
      <div>
        <h1 id="forgot-password-heading" className={authHeadingClass}>Forgot password</h1>
        <p className="mt-2 text-sm leading-6 text-text-secondary">Enter the email address associated with your account. If it matches an account, we’ll send a reset link.</p>
      </div>
      <form aria-busy={pending || undefined} aria-describedby={error ? 'forgot-password-error' : undefined} aria-labelledby="forgot-password-heading" onSubmit={submit} className="grid gap-4">
        <div className="grid gap-1.5">
          <label htmlFor="forgot-password-email" className="text-sm font-medium text-text-secondary">Email address</label>
          <input id="forgot-password-email" autoComplete="email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className={authFieldClass} />
        </div>
        <button type="submit" disabled={pending} className={authPrimaryButtonClass}>
          {pending ? 'Sending…' : 'Send reset link'}
        </button>
      </form>
      {error ? <p id="forgot-password-error" role="alert" className="text-sm leading-5 text-status-danger">{error}</p> : null}
      {sent ? <p role="status" className="text-sm leading-5 text-status-success">If the account is eligible, a reset link has been sent.</p> : null}
      <a href="/login" className={'inline-flex ' + authLinkClass}>Return to sign in</a>
    </section>
  )
}
