import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { TurnstileWidget } from './TurnstileWidget'

type RenderOptions = {
  sitekey: string
  action: string
  callback: (token: string) => void
  'expired-callback': () => void
  'error-callback': () => void
  'timeout-callback': () => void
}

const turnstile = vi.hoisted(() => ({
  render: vi.fn(),
  reset: vi.fn(),
  remove: vi.fn(),
}))

function installTurnstile(): void {
  turnstile.render.mockReturnValue('widget-id')
  Object.defineProperty(window, 'turnstile', {
    configurable: true,
    value: turnstile,
  })
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  delete (window as Window & { turnstile?: unknown }).turnstile
  document.querySelectorAll('script[data-turnstile-script]').forEach((script) =>
    script.remove()
  )
})

describe('conditional Turnstile widget', () => {
  it('explicitly renders a login widget and reports one-use token lifecycle', async () => {
    const onToken = vi.fn()
    const onUnavailable = vi.fn()
    const view = render(
      <TurnstileWidget
        siteKey="public-site-key"
        resetKey={0}
        onToken={onToken}
        onUnavailable={onUnavailable}
      />
    )
    const script = document.querySelector<HTMLScriptElement>(
      'script[data-turnstile-script]'
    )
    expect(script?.src).toBe(
      'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    )
    installTurnstile()
    fireEvent.load(script!)

    await waitFor(() => expect(turnstile.render).toHaveBeenCalledOnce())
    const options = turnstile.render.mock.calls[0][1] as RenderOptions
    expect(options).toMatchObject({ sitekey: 'public-site-key', action: 'login' })
    options.callback('one-use-token')
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(
        'Security verification complete.'
      )
    )
    options['expired-callback']()
    options['error-callback']()
    options['timeout-callback']()
    expect(onToken).toHaveBeenNthCalledWith(1, 'one-use-token')
    expect(onToken).toHaveBeenCalledWith(null)
    expect(onUnavailable).toHaveBeenCalledTimes(2)

    view.rerender(
      <TurnstileWidget
        siteKey="public-site-key"
        resetKey={1}
        onToken={onToken}
        onUnavailable={onUnavailable}
      />
    )
    await waitFor(() => expect(turnstile.reset).toHaveBeenCalledWith('widget-id'))

    view.unmount()
    expect(turnstile.remove).toHaveBeenCalledWith('widget-id')
  })

  it('reports unavailable when no public site key is configured', () => {
    const onUnavailable = vi.fn()
    render(
      <TurnstileWidget
        siteKey=""
        resetKey={0}
        onToken={vi.fn()}
        onUnavailable={onUnavailable}
      />
    )
    expect(onUnavailable).toHaveBeenCalledOnce()
    expect(screen.getByRole('status')).toHaveTextContent(/could not load/i)
  })
})
