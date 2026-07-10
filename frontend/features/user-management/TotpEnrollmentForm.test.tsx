import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TotpEnrollmentForm } from './TotpEnrollmentForm'

describe('TotpEnrollmentForm', () => {
  it('starts with an explicit enrollment action and no secret rendered', () => {
    vi.stubGlobal('fetch', vi.fn())
    render(<TotpEnrollmentForm />)
    expect(screen.getByRole('button', { name: /start authenticator setup/i })).toBeInTheDocument()
    expect(screen.queryByText('JBSWY3DPEHPK3PXP')).not.toBeInTheDocument()
  })
})
