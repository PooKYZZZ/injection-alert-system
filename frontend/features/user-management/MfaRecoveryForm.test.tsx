import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MfaRecoveryForm } from './MfaRecoveryForm'

describe('MfaRecoveryForm', () => {
  it('offers backup-code and verified-email recovery without dashboard claims', () => {
    render(<MfaRecoveryForm />)
    expect(screen.getByRole('heading', { name: /recover authenticator access/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /use backup code/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send a recovery code/i })).toBeInTheDocument()
    expect(screen.queryByText(/dashboard/i)).toBeInTheDocument()
  })
})
