import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { EmptyState, ErrorState, LoadingSkeleton } from './StateViews'

describe('StateViews', () => {
  it('announces loading and error states with a keyboard-safe retry button', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <>
        <LoadingSkeleton rows={2} />
        <ErrorState message="Stats unavailable" onRetry={onRetry} />
      </>
    )

    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Stats unavailable')

    const retryButton = screen.getByRole('button', { name: 'Retry' })
    expect(retryButton).toHaveAttribute('type', 'button')
    expect(retryButton).toHaveClass('focus-visible:outline-none')

    await user.click(retryButton)
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('hides the decorative empty-state icon from assistive technology', () => {
    const { container } = render(<EmptyState />)

    expect(container.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })
})
