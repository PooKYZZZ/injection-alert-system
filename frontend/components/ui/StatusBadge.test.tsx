import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('uses a compact semantic status treatment without forced uppercase text', () => {
    render(<StatusBadge label="Pending setup" tone="warning" domain="lifecycle" />)

    expect(screen.getByText('Pending setup')).toHaveClass('rounded', 'text-xs')
    expect(screen.getByText('Pending setup')).not.toHaveClass('uppercase')
  })
})
