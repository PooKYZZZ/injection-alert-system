'use client'

import { useState, type FormEvent } from 'react'

import { authFieldClass, authPrimaryButtonClass } from '@/components/auth/authStyles'

export function SetupPasswordForm({ token }: { token: string }) {
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password !== confirmation) {
      setMessage('Passwords do not match.')
      return
    }
    setPending(true)
    setMessage(null)
    try {
      const response = await fetch('/api/auth/setup-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      })
      setMessage(
        response.ok
          ? 'Password set. Return to sign in and complete any required authenticator enrollment.'
          : 'This setup link is invalid or expired.'
      )
      if (response.ok) {
        setPassword('')
        setConfirmation('')
      }
    } catch {
      setMessage('Password setup is temporarily unavailable.')
    } finally {
      setPending(false)
    }
  }

  return (
    <form onSubmit={submit} className="mt-8 flex flex-col gap-4">
      <label className="flex flex-col gap-2 text-sm font-medium text-text-secondary">
        New password
        <input
          aria-label="New password"
          autoComplete="new-password"
          className={authFieldClass}
          minLength={15}
          maxLength={256}
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-text-secondary">
        Confirm password
        <input
          aria-label="Confirm password"
          autoComplete="new-password"
          className={authFieldClass}
          minLength={15}
          maxLength={256}
          type="password"
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
          required
        />
      </label>
      <p className="text-xs leading-5 text-text-muted">
        Use at least 15 characters. Spaces and password-manager paste are supported.
      </p>
      <button className={authPrimaryButtonClass} disabled={pending || !token} type="submit">
        {pending ? 'Setting password…' : 'Set password'}
      </button>
      {message ? <p role="status" className="text-sm leading-5 text-text-secondary">{message}</p> : null}
    </form>
  )
}
