'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { signIn } from '@/auth'

export default function LoginPage() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [pending, setPending] = useState(false)

  const handleSubmit = async () => {
    setError(false)
    setPending(true)
    try {
      await signIn('credentials', {
        password,
        redirectTo: '/dashboard',
      })
    } catch (e) {
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

        <div className="mb-4">
          <label className="block text-sm font-medium text-text-muted mb-1">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !pending && handleSubmit()}
            placeholder="Enter password"
            className="w-full border border-border-light rounded px-3 py-2 text-sm text-text-main focus:outline-none focus:border-primary"
          />
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={pending}
          className="w-full bg-primary hover:bg-primary-dark text-white text-sm font-medium rounded px-4 py-2 cursor-pointer text-center transition-colors"
        >
          {pending ? 'Signing in…' : 'Sign in'}
        </button>
      </div>
    </div>
  )
}
