'use client'

import { useState } from 'react'

export function VerifyEmailForm({ token }: { token: string }) {
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function verify() {
    setPending(true)
    setMessage(null)
    try {
      const response = await fetch('/api/auth/verify-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      })
      setMessage(
        response.ok
          ? 'Email verified. Existing sessions for the account have been invalidated.'
          : 'This verification link is invalid or expired.'
      )
    } catch {
      setMessage('Email verification is temporarily unavailable.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mt-8 flex flex-col gap-4">
      <button className="h-11 rounded-md bg-accent-action px-4 text-sm font-semibold text-surface-shell disabled:opacity-50" disabled={pending || !token} onClick={() => void verify()} type="button">
        {pending ? 'Verifying…' : 'Verify email'}
      </button>
      {message ? <p role="status" className="text-sm leading-5 text-text-secondary">{message}</p> : null}
    </div>
  )
}
