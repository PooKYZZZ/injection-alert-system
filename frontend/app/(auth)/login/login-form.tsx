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
import { TurnstileWidget } from '@/components/auth/TurnstileWidget'
import { loginAction } from './actions'

type LoginFormProps = {
  turnstileSiteKey: string
}

export default function LoginForm({ turnstileSiteKey }: LoginFormProps) {
  const router = useRouter()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [challengeRequired, setChallengeRequired] = useState(false)
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null)
  const [widgetResetKey, setWidgetResetKey] = useState(0)
  const [pending, setPending] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage(null)
    setPending(true)
    const submittedToken = turnstileToken
    if (submittedToken) {
      setTurnstileToken(null)
      setWidgetResetKey((key) => key + 1)
    }

    try {
      const result = await loginAction(
        identifier,
        password,
        submittedToken ?? undefined
      )

      if (!result.ok) {
        if (result.code === 'VERIFICATION_REQUIRED') {
          setChallengeRequired(true)
          setErrorMessage(
            'Please complete the security verification, then try again.'
          )
        } else if (result.code === 'INVALID_CREDENTIALS') {
          setChallengeRequired(false)
          setErrorMessage('Invalid username or password.')
        } else {
          setErrorMessage(
            'Sign-in service is temporarily unavailable. Please try again shortly.'
          )
        }
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

        {challengeRequired ? (
          <div className="grid gap-2" aria-live="polite">
            <p className={authFieldLabelClass} id="security-verification-label">
              Additional security verification
            </p>
            <TurnstileWidget
              siteKey={turnstileSiteKey}
              resetKey={widgetResetKey}
              onToken={(token) => {
                setTurnstileToken(token)
              }}
              onUnavailable={() => {
                setTurnstileToken(null)
              }}
            />
          </div>
        ) : null}

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
