import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MfaVerifyForm } from './MfaVerifyForm'

describe('MfaVerifyForm', () => {
  it('requires a six-digit authenticator code', () => {
    render(<MfaVerifyForm />)
    expect(screen.getByRole('heading', { name: /verify your authenticator/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
  })
})
