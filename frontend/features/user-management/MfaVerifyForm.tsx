'use client'

import { useEffect, useRef, useState, type FormEvent } from 'react'

import styles from './MfaVerifyForm.module.css'

type VerificationError = Error & { code?: string }

type TerminalError = {
  code: 'MFA_CHALLENGE_EXPIRED' | 'MFA_CHALLENGE_LOCKED'
  message: string
}

function isTerminalCode(code: string | undefined): code is TerminalError['code'] {
  return code === 'MFA_CHALLENGE_EXPIRED' || code === 'MFA_CHALLENGE_LOCKED'
}

export function MfaVerifyForm() {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [terminalError, setTerminalError] = useState<TerminalError | null>(null)
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const submittingRef = useRef(false)

  useEffect(() => {
    if (!error) return
    const input = inputRef.current
    if (!input) return
    input.focus({ preventScroll: true })
    input.select()
  }, [error])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (code.length !== 6 || submittingRef.current) return
    submittingRef.current = true
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/verify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        const reason = new Error(payload?.error?.message ?? 'Unable to verify authenticator code.') as VerificationError
        if (typeof payload?.error?.code === 'string') reason.code = payload.error.code
        throw reason
      }
      window.location.assign('/dashboard')
    } catch (reason) {
      const verificationError = reason instanceof Error ? reason as VerificationError : null
      const message = verificationError?.message ?? 'Unable to verify authenticator code.'
      if (isTerminalCode(verificationError?.code)) {
        setError(null)
        setTerminalError({ code: verificationError.code, message })
      } else {
        setTerminalError(null)
        setError(message)
      }
    } finally {
      submittingRef.current = false
      setBusy(false)
    }
  }

  return (
    <main className={styles.shell} aria-labelledby="mfa-verify-heading">
      <div className={styles.frame}>
        <aside className={styles.context} aria-label="Sign-in context">
          <div>
            <p className={styles.wordmark}>CYBERTRACE</p>
            <p className={styles.contextTitle}>A quiet checkpoint for a protected workspace.</p>
            <p className={styles.contextCopy}>Your password was accepted. Confirm the current authenticator code to complete this sign-in.</p>
          </div>
          <p className={styles.contextFoot}>Challenge is bound to this sign-in session</p>
        </aside>

        <section className={styles.formRegion}>
          {terminalError ? (
            <div className={styles.terminal} role="alert" aria-labelledby="mfa-verify-heading">
              <p className={styles.eyebrow}>Sign-in challenge ended</p>
              <h1 id="mfa-verify-heading" className={styles.heading}>Start sign-in again</h1>
              <p className={styles.description}>{terminalError.message}</p>
              <a href="/login" className={styles.terminalAction}>Return to sign in</a>
            </div>
          ) : (
            <>
              <div className={styles.progress}>
                <p className={styles.eyebrow}>Second factor required</p>
                <span className={styles.step}>Step 2 of 2</span>
              </div>
              <h1 id="mfa-verify-heading" className={styles.heading}>Verify your authenticator</h1>
              <p className={styles.description}>Enter the current six-digit code from your authenticator app to finish signing in.</p>

              <form aria-labelledby="mfa-verify-heading" onSubmit={submit} className={styles.form}>
                <label htmlFor="mfa-code" className={styles.label}>Authenticator code</label>
                <p id="mfa-code-help" className={styles.help}>The code is accepted as one value. Paste or type all six digits.</p>
                <input
                  ref={inputRef}
                  id="mfa-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  autoFocus
                  required
                  pattern={'\\d{6}'}
                  maxLength={6}
                  value={code}
                  aria-describedby={error ? 'mfa-code-help mfa-code-error' : 'mfa-code-help'}
                  aria-invalid={error ? 'true' : undefined}
                  onChange={(event) => {
                    setCode(event.target.value.replace(/\D/g, ''))
                    if (error) setError(null)
                  }}
                  className={styles.codeInput}
                />
                <button type="submit" disabled={busy || code.length !== 6} className={styles.submit}>
                  {busy ? 'Verifying…' : 'Continue'}
                </button>
                {error && <p id="mfa-code-error" role="alert" className={styles.error}>{error}</p>}
              </form>
            </>
          )}
        </section>
      </div>
    </main>
  )
}
