import { fireEvent, render, screen, within } from '@testing-library/react'
import { act, type HTMLAttributes, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { BulkActionBar } from './BulkActionBar'

const mutateAsyncMock = vi.fn()

vi.mock('@/features/alerts/queries', () => ({
  useTriageMutation: () => ({
    mutateAsync: mutateAsyncMock,
  }),
}))

vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  },
}))

describe('BulkActionBar', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mutateAsyncMock.mockReset()
    mutateAsyncMock.mockResolvedValue({})
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
    vi.clearAllMocks()
  })

  it('clears the summary timeout on unmount', async () => {
    const onClearSelection = vi.fn()

    const { unmount } = render(
      <BulkActionBar selectedIds={new Set(['1'])} onClearSelection={onClearSelection} />
    )

    await act(async () => {
      fireEvent.click(screen.getAllByRole('button', { name: 'Resolve' })[0])
      await Promise.resolve()
    })
    expect(screen.getByText('1 alert updated')).toBeInTheDocument()
    expect(vi.getTimerCount()).toBe(1)

    unmount()

    expect(vi.getTimerCount()).toBe(0)
  })

  it('removes the summary after the timeout elapses', async () => {
    const onClearSelection = vi.fn()

    render(
      <BulkActionBar selectedIds={new Set(['1'])} onClearSelection={onClearSelection} />
    )

    await act(async () => {
      fireEvent.click(screen.getAllByRole('button', { name: 'Resolve' })[0])
      await Promise.resolve()
    })
    expect(screen.getByText('1 alert updated')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(3000)
      await Promise.resolve()
    })
    expect(screen.queryByText('1 alert updated')).not.toBeInTheDocument()
  })

  it('uses set1 authored selection accent and semantic action affordances', () => {
    const onClearSelection = vi.fn()

    const { container } = render(
      <BulkActionBar selectedIds={new Set(['1', '2'])} onClearSelection={onClearSelection} />
    )

    const shell = container.firstElementChild
    expect(shell).not.toBeNull()
    expect(shell).toHaveClass('border-surface-border')
    expect(shell).toHaveClass('bg-surface-card')

    const scopedQueries = within(container)

    const selectedLabel = screen.getByText('2 selected')
    const selectedIcon = selectedLabel.parentElement?.querySelector('svg')
    expect(selectedIcon).not.toBeNull()
    expect(selectedIcon).toHaveClass('text-action-accent')

    expect(scopedQueries.getByRole('button', { name: 'Mark False Positive' })).toHaveClass('border-action-border')
    expect(scopedQueries.getByRole('button', { name: 'Escalate' })).toHaveClass('border-severity-high-border')
    expect(scopedQueries.getByRole('button', { name: 'Resolve' })).toHaveClass('border-severity-safe-border')
  })
})
