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
      if (e instanceof AuthError) {
        setError(true)
        setPending(false)
        return
      }
      throw e
    }
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="bg-[#111] rounded-lg shadow-md p-8 w-full max-w-sm text-white">

        <h1 className="text-2xl font-semibold mb-6 text-center">
          Login
        </h1>

        {error && (
          <p className="mb-4 text-sm text-red-400 text-center">
            Invalid password. Please try again.
          </p>
        )}

        {/* Password Input */}
        <input
          type="password"
          placeholder="Enter password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !pending && handleSubmit()}
          className="w-full mb-4 px-3 py-2 bg-black border border-gray-600 rounded"
        />

        {/* Login Button */}
        <button
          onClick={handleSubmit}
          disabled={pending}
          className="w-full bg-gray-700 hover:bg-gray-600 py-2 rounded"
        >
          {pending ? 'Signing in...' : 'Login'}
        </button>

      </div>
    </div>
  )
}