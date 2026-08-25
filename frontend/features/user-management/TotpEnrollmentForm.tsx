'use client'

import { useEffect, useState, type FormEvent } from 'react'
import Image from 'next/image'
import QRCode from 'qrcode'

import { authFieldClass, authHeadingClass, authPrimaryButtonClass } from '@/components/auth/authStyles'

type Enrollment = {
  factor_id: string
  manual_key: string
  provisioning_uri: string
  expires_at: string
}

const totpErrorId = 'totp-error'

export function TotpEnrollmentForm() {
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null)
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!enrollment) {
      setQrCode(null)
      return
    }
    let active = true
    void QRCode.toDataURL(enrollment.provisioning_uri, {
      errorCorrectionLevel: 'M',
      margin: 1,
      width: 220,
    }).then((dataUrl) => {
      if (active) setQrCode(dataUrl)
    }).catch(() => {
      if (active) setQrCode(null)
    })
    return () => {
      active = false
    }
  }, [enrollment])

  async function begin() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/enroll', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.error?.message ?? 'Unable to begin enrollment.')
      setEnrollment(payload)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to begin enrollment.')
    } finally {
      setBusy(false)
    }
  }

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!enrollment) return
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/enroll/verify', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ factor_id: enrollment.factor_id, code }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.error?.message ?? 'Unable to verify code.')
      setBackupCodes(payload.backup_codes)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to verify code.')
    } finally {
      setBusy(false)
    }
  }

  async function finalize() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/auth/mfa/enroll/finalize', {
        method: 'POST',
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => null)
        throw new Error(payload?.error?.message ?? 'Unable to finish enrollment.')
      }
      window.location.assign('/dashboard')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to finish enrollment.')
    } finally {
      setBusy(false)
    }
  }

  if (backupCodes) {
    return (
      <section className="space-y-4" aria-labelledby="backup-code-heading">
        <h2 id="backup-code-heading" className="text-lg font-semibold text-text-primary">Save your backup codes</h2>
        <p className="text-sm text-text-secondary">These codes are shown once. Store them in a password manager or secure offline location.</p>
        <output className="grid grid-cols-2 gap-2 rounded-lg border border-border-subtle bg-surface-raised p-4 font-mono text-sm text-text-primary" aria-label="Backup codes">
          {backupCodes.map((backupCode) => <span key={backupCode}>{backupCode}</span>)}
        </output>
        <p className="text-sm text-status-success">Authenticator enrollment complete.</p>
        <button
          type="button"
          onClick={finalize}
          disabled={busy}
          className={authPrimaryButtonClass}
        >
          {busy ? 'Finishing…' : 'I saved my backup codes'}
        </button>
        {error && <p role="alert" className="text-sm text-status-danger">{error}</p>}
      </section>
    )
  }

  return (
    <section className="w-full max-w-[400px] space-y-5" aria-labelledby="totp-heading">
      <div>
        <h1 id="totp-heading" className={authHeadingClass}>Secure your account</h1>
        <p className="mt-2 text-sm text-text-secondary">Use an authenticator app to scan the QR payload or enter the manual setup key.</p>
      </div>
      {!enrollment ? (
        <button type="button" onClick={begin} disabled={busy} className={authPrimaryButtonClass}>
          {busy ? 'Preparing…' : 'Start authenticator setup'}
        </button>
      ) : (
        <>
          <div className="rounded-lg border border-border-subtle bg-surface-raised p-4">
            {qrCode && <Image src={qrCode} alt="Authenticator setup QR code" width={224} height={224} unoptimized className="mb-4 rounded bg-white p-2" />}
            <p className="text-xs font-medium text-text-secondary">Manual setup key</p>
            <code className="mt-2 block break-all text-sm text-text-primary">{enrollment.manual_key}</code>
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-accent">Show QR payload</summary>
              <code className="mt-2 block break-all text-xs text-text-secondary" data-qr-value={enrollment.provisioning_uri}>{enrollment.provisioning_uri}</code>
            </details>
          </div>
          <form
            aria-label="Verify authenticator"
            aria-busy={busy || undefined}
            aria-describedby={error ? totpErrorId : 'totp-code-help'}
            onSubmit={verify}
            className="grid gap-3"
          >
            <div className="grid gap-1.5">
              <label className="text-sm font-medium text-text-secondary" htmlFor="totp-code">Enter the six-digit code</label>
              <p id="totp-code-help" className="text-xs leading-5 text-text-muted">Paste or type the code shown in your authenticator app.</p>
              <input
                id="totp-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                required
                pattern={'\\d{6}'}
                maxLength={6}
                value={code}
                aria-describedby={error ? 'totp-code-help totp-error' : 'totp-code-help'}
                aria-invalid={error ? 'true' : undefined}
                onChange={(event) => {
                  setCode(event.target.value.replace(/\D/g, ''))
                  if (error) setError(null)
                }}
                className={'font-mono ' + authFieldClass}
              />
            </div>
            <button type="submit" disabled={busy || code.length !== 6} className={authPrimaryButtonClass}>
              {busy ? 'Verifying…' : 'Verify authenticator'}
            </button>
          </form>
        </>
      )}
      {error && <p id={totpErrorId} role="alert" className="text-sm text-status-danger">{error}</p>}
    </section>
  )
}
