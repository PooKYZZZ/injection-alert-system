import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PageHeader } from './PageHeader'

describe('PageHeader', () => {
  it('exposes one page-level heading and a readable description', () => {
    render(
      <PageHeader
        title="Dashboard"
        description="Review request activity and enforcement outcomes."
      />
    )

    expect(screen.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Review request activity and enforcement outcomes.')).toHaveClass(
      'max-w-2xl'
    )
  })
})
