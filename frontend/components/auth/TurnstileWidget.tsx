'use client'

import { useEffect, useRef, useState } from 'react'

const TURNSTILE_SCRIPT_URL =
  'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
const TURNSTILE_SCRIPT_ID = 'cloudflare-turnstile-script'

type TurnstileOptions = {
  sitekey: string
  action: 'login'
  callback: (token: string) => void
  'expired-callback': () => void
  'error-callback': () => void
  'timeout-callback': () => void
}

type TurnstileApi = {
  render: (target: HTMLElement, options: TurnstileOptions) => string
  reset: (widgetId: string) => void
  remove: (widgetId: string) => void
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
  }
}

type TurnstileWidgetProps = {
  siteKey: string
  resetKey: number
  onToken: (token: string | null) => void
  onUnavailable: () => void
}

type WidgetStatus = 'expired' | 'unavailable' | 'verified' | null

export function TurnstileWidget({
  siteKey,
  resetKey,
  onToken,
  onUnavailable,
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const widgetIdRef = useRef<string | null>(null)
  const resetKeyRef = useRef(resetKey)
  const onTokenRef = useRef(onToken)
  const onUnavailableRef = useRef(onUnavailable)
  const currentResetKeyRef = useRef(resetKey)
  const [status, setStatus] = useState<{
    value: WidgetStatus
    resetKey: number
  }>({ value: null, resetKey })
  const visibleStatus = !siteKey
    ? 'unavailable'
    : status.resetKey === resetKey
      ? status.value
      : null

  function updateStatus(value: WidgetStatus) {
    setStatus({ value, resetKey: currentResetKeyRef.current })
  }

  useEffect(() => {
    onTokenRef.current = onToken
    onUnavailableRef.current = onUnavailable
  }, [onToken, onUnavailable])

  useEffect(() => {
    currentResetKeyRef.current = resetKey
  }, [resetKey])

  useEffect(() => {
    if (!siteKey) {
      onUnavailableRef.current()
      return
    }

    let disposed = false
    let script: HTMLScriptElement | null = null

    const reportUnavailable = () => {
      if (disposed) return
      updateStatus('unavailable')
      onTokenRef.current(null)
      onUnavailableRef.current()
    }

    const renderWidget = () => {
      if (disposed || !containerRef.current) return
      const api = window.turnstile
      if (!api) {
        reportUnavailable()
        return
      }
      try {
        widgetIdRef.current = api.render(containerRef.current, {
          sitekey: siteKey,
          action: 'login',
          callback: (token) => {
            updateStatus('verified')
            onTokenRef.current(token)
          },
          'expired-callback': () => {
            updateStatus('expired')
            onTokenRef.current(null)
          },
          'error-callback': reportUnavailable,
          'timeout-callback': reportUnavailable,
        })
      } catch {
        reportUnavailable()
      }
    }

    const handleLoad = () => {
      if (script) script.dataset.turnstileLoaded = 'true'
      renderWidget()
    }
    const handleError = () => reportUnavailable()

    if (window.turnstile) {
      renderWidget()
    } else {
      script = document.getElementById(
        TURNSTILE_SCRIPT_ID
      ) as HTMLScriptElement | null
      if (!script) {
        script = document.createElement('script')
        script.id = TURNSTILE_SCRIPT_ID
        script.dataset.turnstileScript = 'true'
        script.src = TURNSTILE_SCRIPT_URL
        script.async = true
        script.defer = true
      }
      script.addEventListener('load', handleLoad)
      script.addEventListener('error', handleError)
      if (script.dataset.turnstileLoaded === 'true') {
        handleLoad()
      } else if (!script.isConnected) {
        document.head.appendChild(script)
      }
    }

    return () => {
      disposed = true
      script?.removeEventListener('load', handleLoad)
      script?.removeEventListener('error', handleError)
      if (widgetIdRef.current) {
        window.turnstile?.remove(widgetIdRef.current)
        widgetIdRef.current = null
      }
    }
  }, [siteKey])

  useEffect(() => {
    if (resetKeyRef.current === resetKey) return
    resetKeyRef.current = resetKey
    const widgetId = widgetIdRef.current
    if (widgetId) window.turnstile?.reset(widgetId)
  }, [resetKey])

  return (
    <div
      role="group"
      aria-labelledby="security-verification-label"
      className="min-h-[65px]"
    >
      <div ref={containerRef} />
      {visibleStatus ? (
        <p className="text-sm text-text-secondary" role="status" aria-live="polite">
          {visibleStatus === 'expired'
            ? 'Security verification expired. Complete it again.'
            : visibleStatus === 'verified'
              ? 'Security verification complete.'
              : 'Security verification could not load. Refresh the page and try again.'}
        </p>
      ) : null}
    </div>
  )
}
