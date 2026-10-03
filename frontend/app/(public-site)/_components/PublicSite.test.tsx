import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { AboutUsContent } from './PublicSite'

afterEach(() => cleanup())

describe('AboutUsContent', () => {
  it('shows listed students, supplied portraits, and their areas of focus', () => {
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

    for (const name of [
      'Mark Angelo A. Aquino',
      'Junaid Bantuas',
      'Eugene Dela Cruz',
      'Froilan Gayao',
      'Faron Jabez Nonan',
    ]) {
      expect(screen.getByRole('img', { name: `Portrait of ${name}` })).toBeInTheDocument()
    }

    expect(
      screen.queryByRole('img', { name: 'Formal portrait placeholder for Mark Angelo A. Aquino' })
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('img', { name: 'Formal portrait placeholder for Junaid Bantuas' })
    ).not.toBeInTheDocument()

    expect(screen.getByText('Intelligent Systems')).toBeInTheDocument()
    expect(screen.getByText('Data Science')).toBeInTheDocument()
    expect(screen.getAllByText('Systems Administration')).toHaveLength(3)
  })

  it('shows the adviser portrait and a concise description of the guidance role', () => {
    render(<AboutUsContent />)

    expect(screen.getByRole('heading', { name: 'Our project adviser' })).toBeInTheDocument()
    expect(screen.getByText('Robin Valenzuela · Team Adviser')).toBeInTheDocument()
    expect(
      screen.getByText('Academic guidance for Team 12 throughout the CyberTrace project.')
    ).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Portrait of Robin Valenzuela, Team Adviser' }))
      .toBeInTheDocument()
  })
})
