import { fireEvent, render, screen, within } from '@testing-library/react'
import { type HTMLAttributes, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AlertDrawer } from './AlertDrawer'
import { useActionMutation, useTriageMutation } from '@/features/alerts/queries'
import type { Alert } from '@/features/alerts/types'

vi.mock('@/features/alerts/queries', () => ({
  useTriageMutation: vi.fn(),
  useActionMutation: vi.fn(),
}))

vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  },
}))

const mockedUseTriageMutation = vi.mocked(useTriageMutation)
const mockedUseActionMutation = vi.mocked(useActionMutation)

const triageMutateMock = vi.fn()
const actionMutateMock = vi.fn()

function buildAlert(overrides: Partial<Alert>): Alert {
  return {
    alert_id: 'alert-default',
    timestamp: '2026-04-17T08:30:00.000Z',
    source_ip: '10.0.0.8',
    request_path: '/api/login',
    request_method: 'POST',
    payload_snippet: "' OR 1=1 --",
    prediction: 'SQL Injection',
    confidence: 0.91,
    confidence_level: 'HIGH',
    action_taken: 'ALLOWED',
    triage_status: 'new',
    crs_score: 9,
    crs_rule_ids: ['942100'],
    ...overrides,
  }
}

describe('AlertDrawer', () => {
  beforeEach(() => {
    triageMutateMock.mockReset()
    actionMutateMock.mockReset()

    mockedUseTriageMutation.mockReturnValue({
      mutate: triageMutateMock,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useTriageMutation>)

    mockedUseActionMutation.mockReturnValue({
      mutate: actionMutateMock,
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useActionMutation>)
  })

  it('does not leak optimistic triage/action display when switching to a different alert id', () => {
    const alertA = buildAlert({ alert_id: 'alert-a', prediction: 'SQL Injection', triage_status: 'new', action_taken: 'ALLOWED' })
    const alertB = buildAlert({ alert_id: 'alert-b', prediction: 'Normal', triage_status: 'new', action_taken: 'ALLOWED' })

    const { rerender } = render(<AlertDrawer alert={alertA} onClose={vi.fn()} />)

    fireEvent.click(screen.getByRole('button', { name: /Escalate/i }))
    fireEvent.click(screen.getByRole('button', { name: /Blocked/i }))

    rerender(<AlertDrawer alert={alertB} onClose={vi.fn()} />)

    const summaryHeader = screen.getByText('Summary Header')
    const summaryContainer = summaryHeader.closest('div')

    expect(summaryContainer).not.toBeNull()

    const inSummary = within(summaryContainer as HTMLElement)
    expect(inSummary.getByText('Normal')).toBeInTheDocument()
    expect(inSummary.getByText('New')).toBeInTheDocument()
    expect(inSummary.getByText('Allowed')).toBeInTheDocument()
    expect(inSummary.queryByText('Escalated')).not.toBeInTheDocument()
    expect(inSummary.queryByText('Blocked')).not.toBeInTheDocument()
  })
})
