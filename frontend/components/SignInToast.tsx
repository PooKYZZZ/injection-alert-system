"use client"

import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

type SignInToastContextValue = {
  visible: boolean
  showSignInToast: () => void
  hideSignInToast: () => void
}

const SignInToastContext = createContext<SignInToastContextValue | null>(null)

export function SignInToastProvider({ children }: { children: ReactNode }) {
  const [visible, setVisible] = useState(false)

  return (
    <SignInToastContext.Provider
      value={{
        visible,
        showSignInToast: () => setVisible(true),
        hideSignInToast: () => setVisible(false),
      }}
    >
      {children}
    </SignInToastContext.Provider>
  )
}

export function useSignInToast() {
  const context = useContext(SignInToastContext)
  if (!context) {
    throw new Error('useSignInToast must be used within SignInToastProvider')
  }
  return context
}

export default function SignInToast() {
  const { visible, hideSignInToast } = useSignInToast()

  if (!visible) return null

  function handleClose() {
    hideSignInToast()
  }

  function handleSignIn() {
    const loginUrl = '/login'

    try {
      const popup = window.open(loginUrl, '_blank')
      if (!popup) {
        window.location.assign(loginUrl)
      }
    } catch {
      window.location.assign(loginUrl)
    }

    hideSignInToast()
  }

  return (
    <div style={{ position: 'fixed', left: 20, bottom: 20, zIndex: 9999 }}>
      <div style={{ background: 'linear-gradient(90deg,#111827,#1f2937)', color: 'white', padding: '12px 16px', borderRadius: 8, boxShadow: '0 8px 32px rgba(0,0,0,0.35)', minWidth: 260 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Sign in required</div>
            <div style={{ fontSize: 13, opacity: 0.9 }}>Please sign in, then retry the action from the alert panel.</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleSignIn} style={{ background: '#2563EB', color: 'white', border: 'none', padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>Sign in</button>
            <button onClick={handleClose} aria-label="close" style={{ background: 'transparent', border: 'none', color: 'white', fontSize: 18, lineHeight: 1, cursor: 'pointer' }}>×</button>
          </div>
        </div>
      </div>
    </div>
  )
}
