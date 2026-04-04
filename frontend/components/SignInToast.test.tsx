import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import SignInToast, { SignInToastProvider, useSignInToast } from './SignInToast'

function TriggerSignInToast() {
  const { showSignInToast } = useSignInToast()

  return <button onClick={showSignInToast}>Open sign-in toast</button>
}

describe('SignInToast', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('shows the sign-in call to action when opened', () => {
    render(
      <SignInToastProvider>
        <TriggerSignInToast />
        <SignInToast />
      </SignInToastProvider>
    )

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Open sign-in toast' }))
    })

    expect(screen.getByText('Sign in required')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  })

  it('falls back to window.location.assign when popup is blocked', () => {
    const assignMock = vi.fn()
    vi.stubGlobal('location', { ...window.location, assign: assignMock })

    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    render(
      <SignInToastProvider>
        <TriggerSignInToast />
        <SignInToast />
      </SignInToastProvider>
    )

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Open sign-in toast' }))
    })

    expect(screen.getByText('Sign in required')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(openSpy).toHaveBeenCalledTimes(1)
    expect(openSpy).toHaveBeenCalledWith('/login', '_blank')
    expect(assignMock).toHaveBeenCalledWith('/login')
  })

  it('closes when close button is clicked', () => {
    render(
      <SignInToastProvider>
        <TriggerSignInToast />
        <SignInToast />
      </SignInToastProvider>
    )

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Open sign-in toast' }))
    })

    fireEvent.click(screen.getByRole('button', { name: 'close' }))

    expect(screen.queryByText('Sign in required')).not.toBeInTheDocument()
  })
})
