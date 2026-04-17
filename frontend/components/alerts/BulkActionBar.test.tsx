import { fireEvent, render, screen } from '@testing-library/react'
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

  it('uses set1 card shell tokens for the bulk action container', () => {
    const onClearSelection = vi.fn()
    const { container } = render(
      <BulkActionBar selectedIds={new Set(['1'])} onClearSelection={onClearSelection} />
    )

    const wrapper = container.firstElementChild
    expect(wrapper).not.toBeNull()
    expect(wrapper).toHaveClass('bg-bg-card')
    expect(wrapper).toHaveClass('border-border-light')
  })
})
