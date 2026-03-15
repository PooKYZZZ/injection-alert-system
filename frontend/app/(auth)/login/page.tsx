'use client'

import { useState } from 'react'
import { AuthError } from 'next-auth'
import { loginAction } from './actions'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [pending, setPending] = useState(false)

  const handleSubmit = async () => {
    setError(false)
    setPending(true)

    try {
      await loginAction(password)
    } catch (e) {
      if (e instanceof Error && e.message === 'NEXT_REDIRECT') {
        throw e
      }

      if (e instanceof AuthError) {
        setError(true)
        return
      }
      throw e
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="min-h-screen bg-black flex">

      <div className="w-1/2 flex items-center justify-center">
        <div className="bg-background-main rounded-xl shadow-xl p-12 w-[520px] text-text-main">

          <h1 className="text-4xl font-semibold mb-10 text-center">
            Login
          </h1>

          {error && (
            <p className="mb-6 text-sm text-red-400 text-center">
              Invalid password. Please try again.
            </p>
          )}

          <label htmlFor="password" className="sr-only">
            Password
          </label>
          <input
            id="password"
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !pending && handleSubmit()}
            className="w-full mb-6 px-4 py-3 bg-surface-light border border-border-light rounded-md text-lg text-text-main outline-none focus:border-text-muted"
          />

          <button
            type="button"
            onClick={handleSubmit}
            disabled={pending}
            className="w-full bg-sidebar-active hover:bg-sidebar-bg py-3 rounded-md text-lg font-medium text-white transition-colors"
          >
            {pending ? 'Signing in...' : 'Login'}
          </button>

        </div>
      </div>

      <div className="w-1/2 flex flex-col items-center justify-center text-text-main">
        <img
          src="/logo.png"
          alt="Team 13"
          className="w-[520px] mb-4"
        />

        <h2 className="text-6xl font-bold font-[Orbitron] tracking-wide">
          CyberTrace
        </h2>

        <p className="text-text-muted mt-2 text-lg">
          WAF-ML Security Dashboard
        </p>

        <p className="text-text-muted text-sm">
          by Team 13
        </p>

      </div>
    </div>
  )
}
