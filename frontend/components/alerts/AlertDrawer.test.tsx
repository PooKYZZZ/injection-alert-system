import { render, screen } from '@testing-library/react'
import type { HTMLAttributes, ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { AlertDrawer } from './AlertDrawer'

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
}))

describe('AlertDrawer', () => {
  it('removes placeholder header text, styles captured request as evidence, and keeps unselected interventions actionable', () => {
    render(
      <AlertDrawer
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
})
