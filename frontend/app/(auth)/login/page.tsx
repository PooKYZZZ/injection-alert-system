'use client'

import { useState, type FormEvent } from 'react'
import { signIn } from 'next-auth/react'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [pending, setPending] = useState(false)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (pending) return
    setError(false)
    setPending(true)
    try {
      const result = await signIn('credentials', {
        password,
        redirect: false,
      })
      if (result?.error) {
        setError(true)
        setPending(false)
      } else {
        window.location.href = '/dashboard'
      }
    } catch (err) {
      if (process.env.NODE_ENV === 'development') console.error(err)
      setError(true)
      setPending(false)
    }
  }

  return (
    <div className="min-h-screen bg-background-main flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-md p-8 w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-text-main mb-6">SOC Dashboard</h1>

        {error && (
          <p className="mb-4 text-sm text-status-high bg-red-50 border border-red-200 rounded px-3 py-2">
            Invalid password. Please try again.
          </p>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="password" className="block text-sm font-medium text-text-muted mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full border border-border-light rounded px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary"
            />
          </div>

          <button
            type="submit"
            disabled={pending}
            className="w-full bg-primary hover:bg-primary-dark disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium rounded px-4 py-2 cursor-pointer text-center transition-colors"
          >
            {pending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
