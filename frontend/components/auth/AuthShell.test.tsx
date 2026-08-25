import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { AuthShell } from './AuthShell'

afterEach(cleanup)

describe('AuthShell', () => {
  it('provides a branded security-operations frame around authentication content', () => {
    render(
      <AuthShell>
        <section aria-labelledby="test-heading">
          <h1 id="test-heading">Test authentication content</h1>
        </section>
      </AuthShell>,
    )

    expect(screen.getByRole('complementary', { name: 'CyberTrace security operations' })).toBeInTheDocument()
    expect(screen.getByText('WAF–ML security operations')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Protect the request path.' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Authentication form' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'CyberTrace home' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('heading', { name: 'Test authentication content' })).toBeInTheDocument()
  })
})
