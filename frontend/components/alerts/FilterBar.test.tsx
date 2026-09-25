import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { FilterBar } from './FilterBar'

const mockReplace = vi.fn()
let mockSearchParams = new URLSearchParams()

vi.mock('next/navigation', () => ({
  usePathname: () => '/alerts',
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
}))

beforeEach(() => {
  mockReplace.mockReset()
  mockSearchParams = new URLSearchParams()
})

afterEach(() => {
  cleanup()
  window.history.replaceState({}, '', '/alerts')
})

describe('FilterBar', () => {
  it('exposes named filter controls and updates the URL without losing existing params', async () => {
    const user = userEvent.setup()
    mockSearchParams = new URLSearchParams('search=sql&page=3')
    window.history.replaceState({}, '', '/alerts?search=sql&page=3')

    render(<FilterBar filteredCount={40} />)

    expect(screen.getByLabelText('Time Window')).toHaveValue('ALL')

    await user.selectOptions(screen.getByLabelText('Time Window'), '24h')

    expect(mockReplace).toHaveBeenCalledWith(
      '/alerts?search=sql&page=1&window=24h',
      { scroll: false }
    )
  })

  it('falls back to ALL for malformed filter values', () => {
    mockSearchParams = new URLSearchParams('window=bogus&action=bogus')

    render(<FilterBar />)

    expect(screen.getByLabelText('Time Window')).toHaveValue('ALL')
    expect(screen.getByLabelText('Action Taken')).toHaveValue('ALL')
  })

  it('keeps Normal traffic disabled until explicitly enabled', () => {
    render(<FilterBar />)

    expect(screen.getByRole('checkbox', { name: 'Include Normal Traffic' })).not.toBeChecked()
  })

  it('enables Normal traffic while preserving other filters and resetting pagination', async () => {
    const user = userEvent.setup()
    mockSearchParams = new URLSearchParams('search=demo&page=3&action=ALLOWED')
    window.history.replaceState({}, '', '/alerts?search=demo&page=3&action=ALLOWED')

    const view = render(<FilterBar />)

    await user.click(screen.getByRole('checkbox', { name: 'Include Normal Traffic' }))

    expect(mockReplace).toHaveBeenCalledWith(
      '/alerts?search=demo&page=1&action=ALLOWED&include_normal=true',
      { scroll: false }
    )
    mockSearchParams = new URLSearchParams('search=demo&page=1&action=ALLOWED&include_normal=true')
    window.history.replaceState(
      {},
      '',
      '/alerts?search=demo&page=1&action=ALLOWED&include_normal=true'
    )
    view.rerender(<FilterBar />)
    expect(
      screen.getByText(/Normal traffic has no triage status/)
    ).toBeInTheDocument()
  })

  it('disables Normal traffic without clearing other selected filters', async () => {
    const user = userEvent.setup()
    mockSearchParams = new URLSearchParams('include_normal=true&page=4&triage_status=new')
    window.history.replaceState({}, '', '/alerts?include_normal=true&page=4&triage_status=new')

    render(<FilterBar />)

    await user.click(screen.getByRole('checkbox', { name: 'Include Normal Traffic' }))

    expect(mockReplace).toHaveBeenCalledWith(
      '/alerts?page=1&triage_status=new',
      { scroll: false }
    )
  })

  it('clears the Normal traffic scope with Clear all', async () => {
    const user = userEvent.setup()
    mockSearchParams = new URLSearchParams('include_normal=true&window=24h')
    window.history.replaceState({}, '', '/alerts?include_normal=true&window=24h')

    render(<FilterBar />)

    await user.click(screen.getByRole('button', { name: 'Clear all' }))

    expect(mockReplace).toHaveBeenCalledWith('/alerts?page=1', { scroll: false })
  })

  it('uses operator-friendly labels while keeping canonical filter values', () => {
    render(<FilterBar />)

    expect(screen.getByRole('option', { name: '6 hours' })).toHaveValue('6h')
    expect(screen.getByRole('option', { name: 'In Review' })).toHaveValue('in_review')
    expect(screen.getByRole('option', { name: 'Critical confidence' })).toHaveValue('CRITICAL')
  })
})
