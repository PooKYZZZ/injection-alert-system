import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SeverityBadge } from './SeverityBadge'

describe('SeverityBadge', () => {
  it('renders BENIGN when prediction is Normal even if confidence level is HIGH', () => {
    render(<SeverityBadge severity="HIGH" prediction="Normal" />)

    expect(screen.getByText('BENIGN')).toBeInTheDocument()
    expect(screen.queryByText('HIGH')).not.toBeInTheDocument()
  })

  it('keeps confidence-level label for non-Normal predictions', () => {
    render(<SeverityBadge severity="HIGH" prediction="SQL Injection" />)

    expect(screen.getByText('HIGH')).toBeInTheDocument()
  })
})
