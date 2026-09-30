'use client'

import { useState, type FormEvent } from 'react'

import {
  authDescriptionClass,
  authEyebrowClass,
  authFieldClass,
  authFieldGroupClass,
  authFieldLabelClass,
  authFooterClass,
  authFormClass,
  authHeadingClass,
  authLinkClass,
  authPageClass,
  authPrimaryButtonClass,
} from '@/components/auth/authStyles'
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
      const result = await response.json().catch(() => null) as {
        status?: string
        message?: string
      } | null
      if (response.status === 404 && result?.status === 'not_found') {
        setError(result.message ?? 'No eligible account was found for this email address.')
        return
      }
      if (response.status === 400 && result?.status === 'invalid_request') {
        setError(result.message ?? 'Enter a valid email address.')
        return
      }
      if (!response.ok || result?.status !== 'sent') throw new Error('request_failed')
      setSent(true)
    } catch {
      setError('Unable to send a reset link right now. Try again without leaving this page.')
    } finally {
      setPending(false)
    }
  }

  return (
    <section className={authPageClass} aria-labelledby="forgot-password-heading">
      <div className="space-y-3">
        <p className={authEyebrowClass}>Account recovery</p>
        <h1 id="forgot-password-heading" className={authHeadingClass}>Forgot password</h1>
        <p className={authDescriptionClass}>Enter your email address to request password reset instructions.</p>
      </div>
      <form aria-busy={pending || undefined} aria-describedby={error ? 'forgot-password-error' : undefined} aria-labelledby="forgot-password-heading" onSubmit={submit} className={authFormClass}>
        <div className={authFieldGroupClass}>
          <label htmlFor="forgot-password-email" className={authFieldLabelClass}>Email address</label>
          <input
            id="forgot-password-email"
            autoComplete="email"
            required
            type="email"
            value={email}
            aria-invalid={error ? 'true' : undefined}
            aria-describedby={error ? 'forgot-password-error' : undefined}
            onChange={(event) => {
              setEmail(event.target.value)
              setSent(false)
              if (error) setError(null)
            }}
            className={`${authFieldClass}${error ? ' border-status-danger focus:border-status-danger focus-visible:ring-status-danger/35' : ''}`}
          />
          {error ? <p id="forgot-password-error" role="alert" className="mt-2 text-sm leading-5 text-status-danger">{error}</p> : null}
        </div>
        <button type="submit" disabled={pending} className={authPrimaryButtonClass + ' mt-2'}>
          {pending ? 'Sending…' : 'Send reset link'}
        </button>
      </form>
      {sent ? <p role="status" className="mt-4 text-sm leading-5 text-status-success">Reset instructions were queued for this account. Check your inbox.</p> : null}
      <div className={authFooterClass}>
        <a href="/login" className={'inline-flex ' + authLinkClass}>Return to sign in</a>
      </div>
    </section>
  )
}
