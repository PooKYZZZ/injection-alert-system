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
})
