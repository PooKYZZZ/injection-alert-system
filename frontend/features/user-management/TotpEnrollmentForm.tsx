'use client'

import { useState } from 'react'
import { useEffect } from 'react'
import Image from 'next/image'
import QRCode from 'qrcode'

type Enrollment = {
  factor_id: string
  manual_key: string
  provisioning_uri: string
  expires_at: string
}

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

  async function verify() {
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
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base disabled:opacity-60"
        >
          {busy ? 'Finishing…' : 'I saved my backup codes'}
        </button>
        {error && <p role="alert" className="text-sm text-status-danger">{error}</p>}
      </section>
    )
  }

  return (
    <section className="max-w-xl space-y-5" aria-labelledby="totp-heading">
      <div>
        <h1 id="totp-heading" className="text-2xl font-semibold text-text-primary">Secure your account</h1>
        <p className="mt-2 text-sm text-text-secondary">Use an authenticator app to scan the QR payload or enter the manual setup key.</p>
      </div>
      {!enrollment ? (
        <button type="button" onClick={begin} disabled={busy} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base disabled:opacity-60">
          {busy ? 'Preparing…' : 'Start authenticator setup'}
        </button>
      ) : (
        <>
          <div className="rounded-lg border border-border-subtle bg-surface-raised p-4">
            {qrCode && <Image src={qrCode} alt="Authenticator setup QR code" width={224} height={224} unoptimized className="mb-4 rounded bg-white p-2" />}
            <p className="text-xs uppercase tracking-wide text-text-muted">Manual setup key</p>
            <code className="mt-2 block break-all text-sm text-text-primary">{enrollment.manual_key}</code>
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-accent">Show QR payload</summary>
              <code className="mt-2 block break-all text-xs text-text-secondary" data-qr-value={enrollment.provisioning_uri}>{enrollment.provisioning_uri}</code>
            </details>
          </div>
          <label className="block text-sm text-text-secondary" htmlFor="totp-code">Enter the six-digit code</label>
          <input id="totp-code" inputMode="numeric" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))} className="w-full rounded-md border border-border-subtle bg-surface-raised px-3 py-2 font-mono text-text-primary" />
          <button type="button" onClick={verify} disabled={busy || code.length !== 6} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface-base disabled:opacity-60">
            {busy ? 'Verifying…' : 'Verify authenticator'}
          </button>
        </>
      )}
      {error && <p role="alert" className="text-sm text-status-danger">{error}</p>}
    </section>
  )
}
