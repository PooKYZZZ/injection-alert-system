import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { HTMLAttributes, ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AlertDrawer } from './AlertDrawer'

const labelReviewMutateMock = vi.fn()

vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: HTMLAttributes<HTMLDivElement>) => <div {...props}>{children}</div>,
  },
}))

vi.mock('@radix-ui/react-dialog', () => ({
  Root: ({ children }: { children: ReactNode }) => <>{children}</>,
  Portal: ({ children }: { children: ReactNode }) => <>{children}</>,
  Overlay: ({ children }: { children: ReactNode }) => <>{children}</>,
  Content: ({ children }: { children: ReactNode }) => <>{children}</>,
  Title: ({ children, className }: { children: ReactNode; className?: string }) => (
    <h2 className={className}>{children}</h2>
  ),
  Description: ({ children, className }: { children: ReactNode; className?: string }) => (
    <p className={className}>{children}</p>
  ),
  Close: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('@/features/alerts/queries', () => ({
  useTriageMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  }),
  useActionMutation: () => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  }),
  useLabelReviewMutation: () => ({
    mutate: labelReviewMutateMock,
    isPending: false,
    isError: false,
  }),
}))

afterEach(() => {
  cleanup()
  labelReviewMutateMock.mockReset()
})

const alertFixture = {
  alert_id: 'drawer-review',
  timestamp: '2026-04-03T10:00:00.000Z',
  source_ip: '10.0.0.9',
  request_path: '/admin/login',
  request_method: 'POST',
  payload_snippet: 'payload',
  prediction: 'SQL Injection' as const,
  confidence: 0.91,
  confidence_level: 'HIGH' as const,
  action_taken: 'THROTTLED' as const,
  triage_status: 'in_review' as const,
  crs_score: 11,
  crs_rule_ids: ['942100'],
}

describe('AlertDrawer', () => {
  it('removes placeholder header text, styles captured request as evidence, and keeps unselected interventions actionable', () => {
    render(
      <AlertDrawer
        role="ADMIN"
        alert={{
          alert_id: 'drawer-1',
          timestamp: '2026-04-03T10:00:00.000Z',
          source_ip: '10.0.0.9',
          request_path: '/admin/login',
          request_method: 'POST',
          payload_snippet: "username=admin' OR '1'='1",
          prediction: 'SQL Injection',
          confidence: 0.91,
          confidence_level: 'HIGH',
          action_taken: 'THROTTLED',
          triage_status: 'in_review',
          crs_score: 11,
          crs_rule_ids: ['942100'],
        }}
        onClose={vi.fn()}
      />
    )

    expect(screen.queryByText(/summary header/i)).not.toBeInTheDocument()
    expect(screen.queryByText('dashboard.local')).not.toBeInTheDocument()
    expect(screen.getByText('Alert ID').nextElementSibling).toHaveTextContent('drawer-1')
    expect(screen.getByText('Host').nextElementSibling).toHaveTextContent('—')

    const capturedRequestHeading = screen.getByRole('heading', { name: 'Captured Request' })
    const evidenceShell = capturedRequestHeading.nextElementSibling

    expect(evidenceShell).not.toBeNull()
    expect(evidenceShell).toHaveClass('border-surface-border')
    expect(evidenceShell).toHaveClass('bg-surface-inset')

    const blockedButton = screen.getByRole('button', { name: /Blocked/i })
    const allowedButton = screen.getByRole('button', { name: /Allowed/i })

    expect(blockedButton).not.toBeDisabled()
    expect(allowedButton).not.toBeDisabled()
    expect(blockedButton).toHaveClass('border-surface-border')
    expect(allowedButton).toHaveClass('border-surface-border')
  })

  it('renders CRITICAL confidence tiers in the drawer confidence label', () => {
    render(
      <AlertDrawer
        alert={{
          alert_id: 'drawer-crit',
          timestamp: '2026-04-03T10:00:00.000Z',
          source_ip: '10.0.0.9',
          request_path: '/admin/login',
          request_method: 'POST',
          payload_snippet: "username=admin' OR '1'='1",
          prediction: 'SQL Injection',
          confidence: 0.95,
          confidence_level: 'CRITICAL',
          action_taken: 'BLOCKED',
          triage_status: 'in_review',
          crs_score: 11,
          crs_rule_ids: ['942100'],
        }}
        onClose={vi.fn()}
      />
    )

    expect(screen.getByText('95% (Critical confidence)')).toBeInTheDocument()
  })

  it.each([
    ['VIEWER', false, false],
    ['ANALYST', true, false],
    ['ADMIN', true, true],
    [undefined, false, false],
    ['OWNER', false, false],
  ] as const)(
    'renders mutation affordances for role %s',
    (role, canTriage, canUpdateAction) => {
      render(
        <AlertDrawer
          role={role}
          alert={{
            alert_id: 'drawer-role',
            timestamp: '2026-04-03T10:00:00.000Z',
            source_ip: '10.0.0.9',
            request_path: '/admin/login',
            request_method: 'POST',
            payload_snippet: 'payload',
            prediction: 'SQL Injection',
            confidence: 0.91,
            confidence_level: 'HIGH',
            action_taken: 'THROTTLED',
            triage_status: 'in_review',
            crs_score: 11,
            crs_rule_ids: ['942100'],
          }}
          onClose={vi.fn()}
        />
      )

      expect(Boolean(screen.queryByRole('button', { name: /Resolve/i }))).toBe(canTriage)
      expect(Boolean(screen.queryByRole('button', { name: /Blocked/i }))).toBe(
        canUpdateAction
      )

      if (role === 'ANALYST') {
        expect(screen.getByText('Action updates require Admin.')).toBeInTheDocument()
      } else if (!canTriage) {
        expect(screen.getByText('Viewer mode: read-only.')).toBeInTheDocument()
        expect(
          screen.getByText('Triage updates require Analyst or Admin.')
        ).toBeInTheDocument()
        expect(screen.getByText('Action updates require Admin.')).toBeInTheDocument()
      }
    }
  )

  it('shows analyst review controls and requires a selection before submitting', () => {
    render(<AlertDrawer role="ANALYST" alert={alertFixture} onClose={vi.fn()} />)

    expect(screen.getByLabelText('Verified classification')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve for training' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Exclude from training' })).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Verified classification'), {
      target: { value: 'Normal' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Approve for training' }))

    expect(labelReviewMutateMock).toHaveBeenCalledWith(
      {
        id: 'drawer-review',
        verifiedLabel: 'Normal',
        approvalState: 'approved_for_training',
        reviewNote: undefined,
      },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    )
  })

  it('forwards the returned review so the selected alert can refresh immediately', () => {
    const onReviewUpdated = vi.fn()
    const review = {
      id: 4,
      traffic_log_id: 7,
      revision: 2,
      verified_label: 'Normal',
      approval_state: 'approved_for_training',
      reviewer_id: 'analyst-1',
      reviewer_role: 'ANALYST',
      reviewed_at: '2026-08-04T00:00:00Z',
    }

    render(
      <AlertDrawer
        role="ANALYST"
        alert={alertFixture}
        onClose={vi.fn()}
        onReviewUpdated={onReviewUpdated}
      />
    )

    fireEvent.change(screen.getByLabelText('Verified classification'), {
      target: { value: 'Normal' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Approve for training' }))

    const [, options] = labelReviewMutateMock.mock.calls[0]
    options.onSuccess(review)

    expect(onReviewUpdated).toHaveBeenCalledWith(review)
  })

  it('makes the drawer content vertically scrollable', () => {
    render(<AlertDrawer role="ANALYST" alert={alertFixture} onClose={vi.fn()} />)

    expect(screen.getByTestId('alert-drawer-scroll-region')).toHaveClass('overflow-y-auto')
  })

  it('hides verified review mutation controls from viewers', () => {
    render(<AlertDrawer role="VIEWER" alert={alertFixture} onClose={vi.fn()} />)

    expect(screen.queryByLabelText('Verified classification')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve for training' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Exclude from training' })).not.toBeInTheDocument()
    expect(labelReviewMutateMock).not.toHaveBeenCalled()
  })
})
