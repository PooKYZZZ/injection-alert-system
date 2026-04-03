"use client"

import { useEffect, useState } from 'react'

type ToastState = {
  visible: boolean
  retryArgs?: unknown
}

export default function SignInToast() {
  const [state, setState] = useState<ToastState>({ visible: false })

  useEffect(() => {
    function onShow(e: any) {
      setState({ visible: true, retryArgs: e?.detail?.retryArgs })
    }
    window.addEventListener('show-signin-toast', onShow as EventListener)
    return () => window.removeEventListener('show-signin-toast', onShow as EventListener)
  }, [])

  if (!state.visible) return null

  function handleRetry() {
    ;(async () => {
      try {
        const ra: any = state.retryArgs
        if (!ra?.id) {
          // nothing to retry
          setState({ visible: false })
          return
        }
        const res = await fetch(`/api/alerts/${ra.id}/action`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action_taken: ra.action }),
        })
        if (res.ok) {
          try { window.dispatchEvent(new CustomEvent('action-retry-success', { detail: { id: ra.id } })) } catch {}
        } else {
          if (res.status === 401) {
            const callback = encodeURIComponent(window.location.href)
            try { window.open(`/login?callbackUrl=${callback}`, '_blank') } catch { window.location.assign(`/login?callbackUrl=${callback}`) }
          }
        }
      } catch {}
      setState({ visible: false })
    })()
  }

  function handleClose() {
    setState({ visible: false })
  }

  function handleSignIn() {
    try {
      const callback = encodeURIComponent(window.location.href)
      window.open(`/login?callbackUrl=${callback}`, '_blank')
    } catch {
      window.location.assign(`/login?callbackUrl=${encodeURIComponent(window.location.href)}`)
    }
    setState({ visible: false })
  }

  return (
    <div style={{ position: 'fixed', left: 20, bottom: 20, zIndex: 9999 }}>
      <div style={{ background: 'linear-gradient(90deg,#111827,#1f2937)', color: 'white', padding: '12px 16px', borderRadius: 8, boxShadow: '0 8px 32px rgba(0,0,0,0.35)', minWidth: 260 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Sign in required</div>
            <div style={{ fontSize: 13, opacity: 0.9 }}>A login tab was opened so you can sign in without losing context.</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleSignIn} style={{ background: '#2563EB', color: 'white', border: 'none', padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>Sign in</button>
            <button onClick={handleRetry} style={{ background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.12)', padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>Retry</button>
            <button onClick={handleClose} aria-label="close" style={{ background: 'transparent', border: 'none', color: 'white', fontSize: 18, lineHeight: 1, cursor: 'pointer' }}>×</button>
          </div>
        </div>
      </div>
    </div>
  )
}
