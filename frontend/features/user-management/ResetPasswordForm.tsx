'use client'

import { useState, type FormEvent } from 'react'

import { authFieldClass, authHeadingClass, authLinkClass, authPrimaryButtonClass } from '@/components/auth/authStyles'
export function ResetPasswordForm({ token }: { token: string }) {
  const [password, setPassword] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ token, password }),
      })
      if (!response.ok) {
        setError('This reset link is invalid or expired.')
        return
      }
      setDone(true)
    } catch {
      setError('Password reset is temporarily unavailable. Try again without leaving this page.')
    } finally {
      setPending(false)
    }
  }

  if (done) {
    return (
      <section className="w-full max-w-[400px] space-y-5" aria-labelledby="reset-password-heading">
        <h1 id="reset-password-heading" className={authHeadingClass}>Password reset complete</h1>
        <p role="status" className="text-sm leading-6 text-status-success">Your password was changed. Sign in again to continue.</p>
        <a href="/login" className={'inline-flex ' + authLinkClass}>Return to sign in</a>
      </section>
    )
  }

  return (
    <section className="w-full max-w-[400px] space-y-6" aria-labelledby="reset-password-heading">
      <div>
        <h1 id="reset-password-heading" className={authHeadingClass}>Set a new password</h1>
        <p className="mt-2 text-sm leading-6 text-text-secondary">Use at least 15 characters. You will not be signed in automatically.</p>
      </div>
      <form aria-busy={pending || undefined} aria-describedby={error ? 'reset-password-error' : undefined} aria-labelledby="reset-password-heading" onSubmit={submit} className="grid gap-4">
        <div className="grid gap-1.5">
          <label htmlFor="reset-password-value" className="text-sm font-medium text-text-secondary">New password</label>
          <input id="reset-password-value" required minLength={15} type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className={authFieldClass} />
        </div>
        <button type="submit" disabled={pending || !token} className={authPrimaryButtonClass}>
          {pending ? 'Resetting…' : 'Reset password'}
        </button>
      </form>
      {error ? <p id="reset-password-error" role="alert" className="text-sm leading-5 text-status-danger">{error}</p> : null}
      <a href="/login" className={'inline-flex ' + authLinkClass}>Return to sign in</a>
    </section>
  )
}
