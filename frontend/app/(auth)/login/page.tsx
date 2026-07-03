'use client'

import { useState } from 'react'
import Image from 'next/image'
import { Lock, UserRoundKey } from 'lucide-react'
import { loginAction } from './actions'

export default function LoginPage() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  const handleSubmit = async () => {
    setErrorMessage(null)
    setPending(true)

    try {
      const result = await loginAction(identifier, password)

      if (!result.ok) {
        setErrorMessage(
          result.code === 'INVALID_CREDENTIALS'
            ? 'Invalid username or password.'
            : 'Unable to sign in right now'
        )
      }
    } catch (e) {
      if (e instanceof Error && e.message === 'NEXT_REDIRECT') {
        throw e
      }
      setErrorMessage('Unable to sign in right now')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative">

      {/* BACKGROUND */}
      <div className="fixed inset-0 -z-10">
        <Image
          src="/w5.png"
          alt="background"
          fill
          sizes="100vw"
          priority
          className="object-cover blur-sm"
        />
      </div>

      {/* CARD */}
      <div className="relative w-full max-w-4xl h-[500px] rounded-xl overflow-hidden shadow-xl border border-white/10 flex">

        {/* LEFT PANEL */}
        <div className="hidden lg:flex w-1/2 relative overflow-hidden">

          <div className="absolute inset-0 bg-[#202020]" />
          <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" />

          {/* center context */}
          <div className="relative z-10 flex h-full w-full items-center justify-center text-white">
            <div className="flex flex-col items-center text-center max-w-sm gap-4">

              {/* LOGO */}
              <Image
                src="/logo.png"
                alt="CyberTrace Logo"
                width={100}
                height={100}
                className="object-contain"
                priority
              />

              <h1 className="text-4xl font-bold font-orbitron">
                CyberTrace
              </h1>

              <p className="text-sm text-gray-300">
                Advanced WAF + Machine Learning security dashboard.
              </p>

              <div className="flex flex-col gap-2 text-sm text-gray-400 text-left mt-6">
                <div>• Real-time attack monitoring</div>
                <div>• ML-powered attack classification</div>
                <div>• SOC workflow integration</div>
              </div>

            </div>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="w-full lg:w-1/2 flex items-center justify-center bg-black/20 backdrop-blur-lg px-8">

          <div className="w-full max-w-sm">

            {/* ICON */}
            <div className="mb-6 flex justify-center">
              <UserRoundKey size={64} className="text-white" />
            </div>

            <h2 className="text-xl font-semibold text-white mb-2 text-center">
              Sign in
            </h2>

            <p className="text-sm text-gray-400 mb-6 text-center">
              Enter your account credentials to continue
            </p>

            {errorMessage && (
              <div className="mb-4 flex items-center gap-2 text-red-400 text-sm">
                <Lock size={14} />
                {errorMessage}
              </div>
            )}

            <label htmlFor="identifier" className="sr-only">
              Email or username
            </label>
            <input
              id="identifier"
              type="text"
              autoComplete="username"
              placeholder="Email or username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-[#262626] text-white border border-gray-800 focus:border-white-500 focus:ring-2 focus:ring-white-500/30 outline-none mb-4"
            />

            <label htmlFor="password" className="sr-only">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !pending && handleSubmit()}
              className="w-full px-4 py-3 rounded-lg bg-[#262626] text-white border border-gray-800 focus:border-white-500 focus:ring-2 focus:ring-white-500/30 outline-none mb-4"
            />

            <button
              onClick={handleSubmit}
              disabled={pending}
              className="w-full py-3 rounded-lg bg-gradient-to-r from-green-500 to-green-500 text-white font-medium hover:opacity-90 transition"
            >
              {pending ? 'Signing in...' : 'Sign in'}
            </button>

            <p className="mt-5 text-xs text-center text-gray-400">
              Restricted access — authorized personnel only
            </p>

          </div>
        </div>

      </div>
    </div>
  )
}
