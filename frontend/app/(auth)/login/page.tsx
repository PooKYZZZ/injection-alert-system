'use client'

import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'

import { loginAction } from './actions'

const fieldClass =
  'min-h-11 w-full rounded-md border border-border-light bg-surface-inset px-3 text-sm text-text-primary outline-none transition-colors placeholder:text-text-muted focus:border-accent-action focus-visible:ring-2 focus-visible:ring-accent-action/35'

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
    <main className="grid min-h-screen place-items-center bg-surface-page px-4 py-6 text-text-primary" aria-labelledby="login-heading">
      <section className="w-full max-w-[520px] overflow-hidden rounded-xl border border-border-light bg-surface-panel shadow-2xl">
        <header className="flex items-center justify-between gap-4 border-b border-border-light px-5 py-4">
          <span className="text-sm font-semibold tracking-tight text-accent-action">CyberTrace</span>
          <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-text-muted">Sign in</span>
        </header>

        <div className="px-6 py-8 sm:px-10 sm:py-10">
          <h1 id="login-heading" className="text-2xl font-semibold tracking-tight text-text-primary">Sign in</h1>
          <p className="mt-2 max-w-md text-sm leading-6 text-text-secondary">Use your CyberTrace credentials to continue.</p>

          {errorMessage ? (
            <p id="login-error" className="mt-5 rounded-md border border-status-danger/35 bg-status-danger/5 px-3 py-2 text-sm leading-5 text-status-danger" role="alert">
              {errorMessage}
            </p>
          ) : null}

          <form
            aria-busy={pending || undefined}
            aria-describedby={errorMessage ? 'login-error' : undefined}
            aria-labelledby="login-heading"
            className="mt-7 grid gap-4"
            onSubmit={handleSubmit}
          >
            <div className="grid gap-1.5">
              <label htmlFor="identifier" className="text-xs font-medium text-text-secondary">Email or username</label>
              <input
                id="identifier"
                type="text"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                required
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
                className={fieldClass}
              />
            </div>

            <div className="grid gap-1.5">
              <label htmlFor="password" className="text-xs font-medium text-text-secondary">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className={fieldClass}
              />
            </div>

            <button
              type="submit"
              disabled={pending}
              className="mt-2 min-h-11 rounded-md bg-accent-action px-4 text-sm font-semibold text-surface-shell transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/60 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-panel disabled:cursor-not-allowed disabled:opacity-50"
            >
              {pending ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 border-t border-border-light pt-5 text-center">
            <a href="/forgot-password" className="text-sm text-text-secondary underline decoration-border-light underline-offset-4 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/60">
              Forgot password?
            </a>
          </div>
        </div>
      </section>
    </main>
  )
}
