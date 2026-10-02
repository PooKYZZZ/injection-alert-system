import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { AboutUsContent } from './PublicSite'

afterEach(() => cleanup())

describe('AboutUsContent', () => {
  it('shows listed students, supplied portraits, and placeholders for unavailable portraits', () => {
    render(<AboutUsContent />)

    expect(screen.getByRole('heading', { name: 'Meet Team 12.' })).toBeInTheDocument()

    for (const name of [
      'Mark Angelo A. Aquino',
      'Junaid Bantuas',
      'Eugene Dela Cruz',
      'Froilan Gayao',
      'Faron Jabez Nonan',
    ]) {
      expect(screen.getByRole('heading', { name })).toBeInTheDocument()
    }

    expect(screen.getByRole('img', { name: 'Portrait of Eugene Dela Cruz' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Portrait of Faron Jabez Nonan' })).toBeInTheDocument()
    for (const name of ['Mark Angelo A. Aquino', 'Junaid Bantuas', 'Froilan Gayao']) {
      expect(
        screen.getByRole('img', { name: `Formal portrait placeholder for ${name}` })
      ).toBeInTheDocument()
    }

    expect(screen.getAllByText('Role title to be confirmed')).toHaveLength(5)
  })

  it('keeps the adviser distinct and avoids inventing identity details', () => {
    render(<AboutUsContent />)

    expect(screen.getByRole('heading', { name: 'Our project adviser' })).toBeInTheDocument()
    expect(screen.getByText('Robin Valenzuela · Team Adviser')).toBeInTheDocument()
    expect(
      screen.getByRole('img', {
        name: 'Formal portrait placeholder for the CyberTrace project adviser',
      })
    ).toBeInTheDocument()
  })
})
