'use client'

import { useState } from 'react'
import { AuthError } from 'next-auth'
import { Shield, Lock, Activity } from 'lucide-react'
import { loginAction } from './actions'

export default function LoginPage() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(false)
  const [pending, setPending] = useState(false)
  const [isFocused, setIsFocused] = useState(false)

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
    <div className="min-h-screen flex" style={{ background: 'linear-gradient(135deg, var(--color-bg-base) 0%, var(--color-bg-page) 50%, var(--color-bg-base) 100%)' }}>

      {/* Left — Branding panel */}
      <div className="hidden lg:flex w-1/2 flex-col items-center justify-center px-12 relative border-r border-[var(--color-text-ghost)]">
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'linear-gradient(var(--color-text-primary) 1px, transparent 1px), linear-gradient(90deg, var(--color-text-primary) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        <div className="relative flex flex-col items-center gap-6 text-center">
          <div className="w-20 h-20 rounded-2xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--color-accent-purple-bg) 0%, var(--color-accent-purple-bg) 100%)', border: '1px solid rgba(124,58,237,0.4)', boxShadow: '0 0 40px rgba(124,58,237,0.2)' }}>
            <Shield size={36} className="text-violet-300" />
          </div>
          <div>
            <h1 className="text-5xl font-bold tracking-tight" style={{ color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>CyberTrace</h1>
            <p className="mt-2 text-[15px]" style={{ color: 'var(--color-text-secondary)' }}>WAF-ML Security Dashboard</p>
            <p className="mt-1 text-[12px]" style={{ color: 'var(--color-text-muted)' }}>by Team 13</p>
          </div>
          <div className="flex flex-col gap-2 mt-4 w-full max-w-xs">
            {[
              { icon: <Shield size={12} />, text: 'Real-time WAF threat monitoring' },
              { icon: <Activity size={12} />, text: 'ML-powered attack classification' },
              { icon: <Lock size={12} />, text: 'SOC analyst triage workflow' },
            ].map((item) => (
              <div key={item.text} className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-transparent" style={{ border: '1px solid var(--color-text-ghost)' }}>
                <span className="text-violet-400">{item.icon}</span>
                <span className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>{item.text}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="absolute bottom-6 flex items-center gap-1.5 text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          DistilBERT v3 — Stable
        </div>
      </div>

      {/* Right — Login form */}
      <div className="w-full lg:w-1/2 flex flex-col items-center justify-center px-6 py-12 lg:px-12">
        <div className="flex lg:hidden flex-col items-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, var(--color-accent-purple-bg) 0%, var(--color-accent-purple-bg) 100%)', border: '1px solid rgba(124,58,237,0.4)' }}>
            <Shield size={22} className="text-violet-300" />
          </div>
          <span className="text-xl font-semibold" style={{ color: 'var(--color-text-primary)' }}>CyberTrace</span>
        </div>
        <div className="w-full max-w-sm rounded-xl p-8" style={{ background: 'var(--color-bg-panel)', border: '1px solid var(--color-text-ghost)' }}>
          <div className="mb-7">
            <h2 className="text-[22px] font-semibold" style={{ color: 'var(--color-text-primary)' }}>Sign in</h2>
            <p className="mt-1 text-[13px]" style={{ color: 'var(--color-text-secondary)' }}>Enter your access password to continue</p>
          </div>
          {error && (
            <div className="mb-5 px-3 py-2.5 rounded-lg flex items-center gap-2 text-[12px]" style={{ background: 'rgba(45,27,27,0.8)', border: '1px solid var(--color-severity-high-border)', color: 'var(--color-severity-high-text)' }}>
              <Lock size={12} />
              Invalid password. Please try again.
            </div>
          )}
          <div className="mb-4">
            <label htmlFor="password" className="block text-[11px] font-medium mb-1.5 uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>Password</label>
            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !pending && handleSubmit()}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              className={`w-full px-3 py-2.5 rounded-lg text-[13px] outline-none transition-all ${isFocused ? 'border border-[var(--color-accent-purple)] shadow-[0_0_0_3px_rgba(124,58,237,0.1)]' : 'border border-[var(--color-text-ghost)]'}`}
              style={{ background: 'var(--color-bg-page)', color: 'var(--color-text-primary)' }}
            />
          </div>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={pending}
            className="w-full py-2.5 rounded-lg text-[13px] font-medium transition-all"
            style={{ background: pending ? 'var(--color-accent-purple-bg)' : 'linear-gradient(135deg, var(--color-accent-purple) 0%, var(--color-accent-purple) 100%)', color: 'var(--color-text-primary)', border: '1px solid rgba(124,58,237,0.5)', opacity: pending ? 0.7 : 1, cursor: pending ? 'not-allowed' : 'pointer' }}
          >
            {pending ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Signing in...
              </span>
            ) : 'Sign in'}
          </button>
        </div>
        <p className="mt-5 text-[11px] text-center" style={{ color: 'var(--color-text-muted)' }}>Restricted access — authorized personnel only</p>
      </div>
    </div>
  )
}


