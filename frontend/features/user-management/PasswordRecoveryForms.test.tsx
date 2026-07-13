import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ForgotPasswordForm } from './ForgotPasswordForm'
import { ResetPasswordForm } from './ResetPasswordForm'

describe('password recovery forms', () => {
  it('uses generic forgot-password copy', () => {
    render(<ForgotPasswordForm />)
    expect(screen.getByRole('heading', { name: /forgot password/i })).toBeInTheDocument()
    expect(screen.getByText(/if the account is eligible/i)).toBeInTheDocument()
  })

  it('does not auto-login after reset', () => {
    render(<ResetPasswordForm token={'a'.repeat(43)} />)
    expect(screen.getByText(/will not be signed in automatically/i)).toBeInTheDocument()
  })
})
