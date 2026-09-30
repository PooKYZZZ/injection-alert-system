import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'
import { InfoDisclosure } from './InfoDisclosure'

afterEach(() => cleanup())

describe('InfoDisclosure', () => {
  it('opens with keyboard activation and exposes the explanation to assistive technology', async () => {
    const user = userEvent.setup()
    render(
      <InfoDisclosure label="Confidence">
        Confidence describes support for the predicted classification, not attack severity.
      </InfoDisclosure>
    )

    const control = screen.getByRole('button', { name: 'About Confidence' })
    expect(control).toHaveAttribute('aria-expanded', 'false')

    control.focus()
    await user.keyboard('{Enter}')

    expect(control).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('region', { name: 'Confidence explanation' })).toHaveTextContent(/not attack severity/i)

    await user.keyboard('{Escape}')
    expect(control).toHaveAttribute('aria-expanded', 'false')
    expect(control).toHaveFocus()
  })

  it('closes on an outside pointer interaction', async () => {
    const user = userEvent.setup()
    render(
      <>
        <InfoDisclosure label="Recorded action">Stored label only.</InfoDisclosure>
        <button type="button">Other control</button>
      </>
    )

    await user.click(screen.getByRole('button', { name: 'About Recorded action' }))
    expect(screen.getByRole('region', { name: 'Recorded action explanation' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Other control' }))

    expect(screen.queryByRole('region', { name: 'Recorded action explanation' })).not.toBeInTheDocument()
  })
})
