'use client'

import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'

import {
  authDescriptionClass,
  authEyebrowClass,
  authFieldClass,
  authFieldGroupClass,
  authFieldLabelClass,
  authFormClass,
  authHeadingClass,
  authLinkClass,
  authPageClass,
  authPrimaryButtonClass,
} from '@/components/auth/authStyles'
import { loginAction } from './actions'

export default function LoginPage() {
  const router = useRouter()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
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
      } else {
        router.replace('/dashboard')
      }
    } catch {
      setErrorMessage('Unable to sign in right now')
    } finally {
      setPending(false)
    }
  }

  return (
    <section className={authPageClass} aria-labelledby="login-heading">
      <div className="space-y-3">
        <p className={authEyebrowClass}>Secure workspace</p>
        <h1 id="login-heading" className={authHeadingClass}>Sign in</h1>
        <p className={authDescriptionClass}>Use your CyberTrace credentials to continue.</p>
      </div>

      {errorMessage ? (
        <p id="login-error" className="mt-6 rounded-md border border-status-danger/35 bg-status-danger/5 px-3 py-2 text-sm leading-5 text-status-danger" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <form
        aria-busy={pending || undefined}
        aria-describedby={errorMessage ? 'login-error' : undefined}
        aria-labelledby="login-heading"
        className={authFormClass}
        onSubmit={handleSubmit}
      >
        <div className={authFieldGroupClass}>
          <label htmlFor="identifier" className={authFieldLabelClass}>Email or username</label>
          <input
            id="identifier"
            type="text"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            className={authFieldClass}
          />
        </div>

        <div className={authFieldGroupClass}>
          <div className="flex items-center justify-between gap-4">
            <label htmlFor="password" className={authFieldLabelClass}>Password</label>
            <a href="/forgot-password" className={authLinkClass}>Forgot password?</a>
          </div>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={authFieldClass}
          />
        </div>

        <button
          type="submit"
          disabled={pending}
          className={authPrimaryButtonClass + ' mt-2'}
        >
          {pending ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}
