import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import type { HTMLAttributes, ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Alert } from '@/features/alerts/types'

import { AlertDrawer } from './AlertDrawer'

const {
  labelReviewMutateMock,
  triageMutateMock,
  actionMutateMock,
  useAlertMock,
} = vi.hoisted(() => ({
  labelReviewMutateMock: vi.fn(),
  triageMutateMock: vi.fn(),
  actionMutateMock: vi.fn(),
  useAlertMock: vi.fn(),
}))

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
  useAlert: useAlertMock,
  useTriageMutation: () => ({
    mutate: triageMutateMock,
    isPending: false,
    isError: false,
  }),
  useActionMutation: () => ({
    mutate: actionMutateMock,
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
  triageMutateMock.mockReset()
  actionMutateMock.mockReset()
  useAlertMock.mockReset()
  useAlertMock.mockReturnValue({ data: undefined, isPending: false, isError: false })
})

beforeEach(() => {
  useAlertMock.mockReturnValue({ data: undefined, isPending: false, isError: false })
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
  it('loads and displays detail-only correlation, response, relationship, and action history fields', () => {
    useAlertMock.mockReturnValue({
      data: {
        ...alertFixture,
        request_correlation_id: 'a'.repeat(32),
        observed_http_status: 403,
        evidence_relationship: 'CORROBORATED',
        correlated_records: [
          {
            id: 22,
            ingest_source: 'modsec_audit_bridge',
            transaction_id: 'modsec-22',
            prediction: 'SQL Injection',
            observed_http_status: 403,
            crs_score: 5,
            crs_rule_ids: ['942100'],
            matched_rule_tags: ['application-multi', 'OWASP_CRS'],
          },
        ],
        action_history: [
          {
            id: 4,
            traffic_log_id: 19,
            previous_action: 'ALLOWED',
            new_action: 'BLOCKED',
            actor_id: 'analyst-1',
            changed_at: '2026-09-30T02:00:00Z',
            reason: null,
          },
        ],
      } as Alert,
      isPending: false,
      isError: false,
    })

    render(<AlertDrawer alert={alertFixture} onClose={vi.fn()} />)

    expect(screen.getByText('Correlation ID').closest('dt')?.nextElementSibling).toHaveTextContent('a'.repeat(32))
    expect(screen.getByText('Observed HTTP status').closest('dt')?.nextElementSibling).toHaveTextContent('403')
    expect(screen.getByText('Record #22 · modsec_audit_bridge')).toBeInTheDocument()
    expect(screen.queryByText('Evidence relationship incomplete')).not.toBeInTheDocument()
    expect(screen.getByText('WAF and ML evidence agree')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'About Transaction ID' })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: 'About Observed HTTP status' })).toHaveLength(3)
    expect(screen.getAllByRole('button', { name: 'About Rule IDs' })).toHaveLength(2)

    const relatedRecord = screen.getByText('Record #22 · modsec_audit_bridge').closest('li')
    const relatedRecordDetails = relatedRecord?.querySelector('dl')
    expect(relatedRecordDetails).toHaveClass('grid-cols-[minmax(0,96px)_20px_minmax(0,1fr)]')
    expect(relatedRecordDetails).toHaveClass('[&>dt]:grid-cols-[minmax(0,1fr)_20px]')

    const wafRecord = screen.getByText('Correlated ModSecurity record #22').parentElement
    const wafRecordDetails = wafRecord?.querySelector('dl')
    expect(wafRecordDetails).toHaveClass('grid-cols-[minmax(0,96px)_20px_minmax(0,1fr)]')
    expect(wafRecordDetails).toHaveClass('[&>dt]:grid-cols-[minmax(0,1fr)_20px]')
    expect(within(wafRecordDetails as HTMLElement).getByText('Rule tags').closest('dt')?.nextElementSibling)
      .toHaveTextContent('application-multi, OWASP_CRS')

    fireEvent.click(screen.getByText('Action change history'))
    expect(screen.getByText('ALLOWED → BLOCKED')).toBeInTheDocument()
    expect(screen.getByText(/analyst-1/)).toBeInTheDocument()
  })

  it('shows an explicit loading and failure state for alert detail requests', () => {
    useAlertMock.mockReturnValue({ data: undefined, isPending: false, isError: true })
    render(<AlertDrawer alert={alertFixture} onClose={vi.fn()} />)

    expect(screen.getByText(/Additional traffic details could not be loaded/)).toBeInTheDocument()
  })

  it('clarifies the saved action label is not the observed WAF or origin response', () => {
    render(<AlertDrawer alert={alertFixture} onClose={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Recorded action label' })).toBeInTheDocument()
    expect(
      screen.getByText(
        'This label may come from the confidence policy or a manual update. Saving it changes the alert record only; it does not send a WAF command or confirm the HTTP response.'
      )
    ).toBeInTheDocument()
  })

  it('adds contextual help to detail fields and controls without duplicating existing explanations', () => {
    render(
      <AlertDrawer
        role="OWNER"
        alert={{
          ...alertFixture,
          transaction_id: 'modsec-1',
          ingest_source: 'modsec_audit_bridge',
          query_string: 'query=example',
          model_version: 'model-2026-09',
          preprocessing_version: 'preprocess-v2',
          policy_decision: 'WAF_BLOCK',
          policy_decision_reason: 'STRONG_CRS_EVIDENCE',
          policy_evidence_context: { strong_waf_evidence: true },
          policy_version: 'confidence-enforcement-v3',
          notification_status: { email: 'sent', telegram: 'retry_wait' },
          request_correlation_id: 'request-correlation-1',
          observed_http_status: 403,
          matched_rule_tags: ['attack-sqli'],
          triage_status: 'new',
        }}
        onClose={vi.fn()}
      />
    )

    const expectedHelp = [
      'Alert ID',
      'Time',
      'Request',
      'Model version',
      'Preprocessing',
      'Decision reason',
      'Evidence basis',
      'Policy version',
      'Notifications',
      'Correlation ID',
      'Observed HTTP status',
      'Enforcement source',
      'Related records',
      'WAF evidence',
      'Transaction ID',
      'CRS score',
      'Rule IDs',
      'Rule tags',
      'Host',
      'Request method/path/protocol',
      'Captured query string',
      'Start Review',
      'Resolve',
      'False Positive',
      'Escalate',
      'Save as Blocked',
      'Save as Throttled',
      'Save as Allowed',
    ]

    for (const label of expectedHelp) {
      expect(screen.getByRole('button', { name: `About ${label}` })).toBeInTheDocument()
    }
    expect(screen.getAllByRole('button', { name: 'About Source IP' })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: 'About Confidence' })).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: 'About Policy decision' })).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: 'About Source IP origin' })).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: 'About Source IP verification' })).toHaveLength(1)

    const notificationsTerm = screen.getByText('Notifications').closest('dt')
    const notificationsValue = notificationsTerm?.nextElementSibling
    expect(notificationsTerm).toHaveClass('min-w-0')
    const coreDetailsList = notificationsTerm?.parentElement
    expect(coreDetailsList).toHaveClass('grid-cols-[minmax(0,96px)_20px_minmax(0,1fr)]')
    expect(coreDetailsList).toHaveClass('[&>dt]:grid-cols-[minmax(0,1fr)_20px]')
    expect(coreDetailsList).toHaveClass('[&>dt]:col-span-2', '[&>dd]:col-start-3')
    expect(notificationsValue).toHaveClass('min-w-0')
    const coreTermsWithHelp = Array.from(coreDetailsList?.querySelectorAll('dt') ?? []).filter((term) =>
      term.querySelector('button[aria-label^="About "]')
    )
    expect(coreTermsWithHelp).toHaveLength(14)

    const ownRuleTagsTerm = screen.getByText('Rule tags').closest('dt')
    expect(ownRuleTagsTerm?.parentElement).toHaveClass('grid-cols-[minmax(0,96px)_20px_minmax(0,1fr)]')
    expect(ownRuleTagsTerm?.nextElementSibling).toHaveTextContent('attack-sqli')

    for (const label of ['Host', 'Request method/path/protocol', 'Captured query string']) {
      const help = screen.getByRole('button', { name: `About ${label}` })
      expect(help.parentElement?.parentElement).toHaveClass('grid-cols-[minmax(0,1fr)_20px]')
    }
    expect(screen.getByRole('button', { name: 'About WAF evidence' }).parentElement?.parentElement)
      .toHaveClass('grid-cols-[minmax(0,1fr)_20px]')
    expect(screen.getByRole('button', { name: 'About Related records' }).parentElement?.parentElement)
      .toHaveClass('grid-cols-[minmax(0,1fr)_20px]')
    for (const label of [
      'Start Review',
      'Resolve',
      'False Positive',
      'Escalate',
      'Save as Blocked',
      'Save as Throttled',
      'Save as Allowed',
    ]) {
      expect(screen.getByRole('button', { name: `About ${label}` }).parentElement).toHaveClass('shrink-0')
    }

    const notificationList = within(notificationsValue as HTMLElement).getByRole('list', {
      name: 'Notification channel statuses',
    })
    const notificationRows = within(notificationList).getAllByRole('listitem')
    expect(notificationRows).toHaveLength(2)
    expect(within(notificationRows[0]!).getByText('email')).toBeInTheDocument()
    expect(within(notificationRows[0]!).getByText('sent')).toBeInTheDocument()
    expect(within(notificationRows[1]!).getByText('telegram')).toBeInTheDocument()
    expect(within(notificationRows[1]!).getByText('retry wait')).toBeInTheDocument()

    const notificationsHelp = screen.getByRole('button', { name: 'About Notifications' })
    expect(notificationsHelp.parentElement).toHaveClass('shrink-0')
    fireEvent.click(notificationsHelp)
    const notificationExplanation = screen.getByRole('region', { name: 'Notifications explanation' })
    expect(notificationExplanation).toHaveTextContent('delivery status saved for each notification channel')
    expect(notificationExplanation).toHaveTextContent('does not show whether the request was allowed, throttled, or blocked')
    fireEvent.keyDown(notificationsHelp, { key: 'Escape' })

    fireEvent.click(screen.getByRole('button', { name: 'About Enforcement source' }))
    expect(screen.getByRole('region', { name: 'Enforcement source explanation' })).toHaveTextContent(
      /“Not recorded” means it is unknown here/i
    )

    fireEvent.keyDown(screen.getByRole('button', { name: 'About Enforcement source' }), { key: 'Escape' })
    fireEvent.click(screen.getByRole('button', { name: 'About Captured query string' }))
    expect(screen.getByRole('region', { name: 'Captured query string explanation' })).toHaveTextContent(
      /may be absent or simply not retained/i
    )
  })

  it('keeps opening read-only and offers an explicit Start Review action for new alerts', () => {
    render(
      <AlertDrawer
        role="ANALYST"
        alert={{ ...alertFixture, triage_status: 'new' }}
        onClose={vi.fn()}
      />
    )

    expect(screen.getByRole('button', { name: 'Start Review' })).toBeInTheDocument()
    expect(triageMutateMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Start Review' }))

    expect(triageMutateMock).toHaveBeenCalledWith(
      { id: 'drawer-review', status: 'in_review' },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    )
  })

  it('removes placeholder header text, styles captured request as evidence, and keeps unselected interventions actionable', () => {
    render(
      <AlertDrawer
        role="OWNER"
        alert={{
          alert_id: 'drawer-1',
          transaction_id: 'tx-drawer-1',
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
          policy_decision: 'APPLICATION_BLOCK',
          policy_decision_reason: 'STRONG_CRS_EVIDENCE',
          policy_version: 'confidence-enforcement-v2',
          policy_evidence_context: { strong_waf_evidence: true },
          notification_status: { email: 'sent', telegram: 'retry_wait' },
          ingest_source: 'modsec_audit_bridge',
          source_provenance: 'DIRECT_REMOTE_ADDR',
          source_verification_status: 'VERIFIED',
          matched_rule_messages: ['SQL Injection Attack Detected'],
          matched_rule_tags: ['attack-sqli'],
          evidence_relationship: 'CORROBORATED',
        }}
        onClose={vi.fn()}
      />
    )

    expect(screen.queryByText(/summary header/i)).not.toBeInTheDocument()
    expect(screen.queryByText('dashboard.local')).not.toBeInTheDocument()
    expect(screen.getByText('Alert ID').closest('dt')?.nextElementSibling).toHaveTextContent('drawer-1')
    expect(screen.getByText('Host').closest('div')?.lastElementChild).toHaveTextContent('—')
    expect(screen.getByText('Transaction ID').closest('dt')?.nextElementSibling).toHaveTextContent('tx-drawer-1')
    expect(screen.getByText('WAF and ML evidence agree')).toBeInTheDocument()
    expect(screen.getByText('SQL Injection Attack Detected')).toBeInTheDocument()
    expect(screen.getByText('attack-sqli')).toBeInTheDocument()
    expect(screen.getByText('Policy decision').closest('dt')?.nextElementSibling).toHaveTextContent('APPLICATION_BLOCK')
    expect(screen.getByText('Decision reason').closest('dt')?.nextElementSibling).toHaveTextContent('STRONG CRS EVIDENCE')
    expect(screen.getByRole('heading', { name: 'Training feedback' })).toBeInTheDocument()

    const capturedRequestHeading = screen.getByRole('heading', { name: 'Request details' })
    const evidenceShell = capturedRequestHeading.nextElementSibling

    expect(evidenceShell).not.toBeNull()
    expect(evidenceShell).toHaveClass('border-surface-border')
    expect(evidenceShell).toHaveClass('bg-surface-inset')

    const blockedButton = screen.getByRole('button', { name: /^Save as Blocked/ })
    const allowedButton = screen.getByRole('button', { name: /^Save as Allowed/ })

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

    expect(screen.getByText('95.00% · CRITICAL')).toBeInTheDocument()
  })

  it('shows the separately captured query string without duplicating the request line', () => {
    const queryString = 'query=LND-2026-0001&order=latest%20first'
    render(
      <AlertDrawer
        alert={{
          ...alertFixture,
          request_path: '/records/search',
          request_method: 'GET',
          payload_snippet: 'GET /records/search HTTP/1.1',
          query_string: queryString,
        }}
        onClose={vi.fn()}
      />
    )

    expect(screen.getByText('Captured query string (sensitive values redacted):')).toBeInTheDocument()
    expect(screen.getByText(queryString)).toBeInTheDocument()
    expect(screen.queryByText('GET /records/search HTTP/1.1')).not.toBeInTheDocument()
  })

  it('explains source verification and uses the revised detail section labels', () => {
    const onClose = vi.fn()
    render(
      <AlertDrawer
        alert={{
          ...alertFixture,
          source_provenance: 'CLOUDFLARE_CONNECTING_IP',
          source_verification_status: 'VERIFIED',
        }}
        onClose={onClose}
      />
    )

    expect(screen.getByText('Source IP origin').closest('dt')?.nextElementSibling).toHaveTextContent('Cloudflare connecting IP')
    expect(screen.getByText('Source IP verification').closest('dt')?.nextElementSibling).toHaveTextContent('Verified')
    expect(screen.getByRole('heading', { name: 'Request details' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Review & triage' })).toBeInTheDocument()

    const sourceHelp = screen.getByRole('button', { name: 'About Source IP verification' })
    fireEvent.click(sourceHelp)
    expect(screen.getByRole('region', { name: 'Source IP verification explanation' })).toHaveTextContent(/configured Cloudflare tunnel checks/i)

    fireEvent.keyDown(sourceHelp, { key: 'Escape' })
    expect(screen.queryByRole('region', { name: 'Source IP verification explanation' })).not.toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('explains why synchronous portal input is not included in Traffic Details', () => {
    render(
      <AlertDrawer
        alert={{
          ...alertFixture,
          request_path: '/records/search',
          request_method: 'GET',
          payload_snippet: 'GET /records/search HTTP/1.1',
          ingest_source: 'portal_route_bridge',
        }}
        onClose={vi.fn()}
      />
    )

    expect(
      screen.getByText(
        'This portal request was inspected, but its submitted input is intentionally not saved with this traffic record.'
      )
    ).toBeInTheDocument()
  })

  it('explains that access-log events do not retain query strings', () => {
    render(
      <AlertDrawer
        alert={{
          ...alertFixture,
          request_path: '/records/search',
          request_method: 'GET',
          payload_snippet: 'GET /records/search HTTP/1.1',
          ingest_source: 'nginx_access_bridge',
        }}
        onClose={vi.fn()}
      />
    )

    expect(
      screen.getByText(
        'Access-log events do not retain query strings, so the original input is unavailable here.'
      )
    ).toBeInTheDocument()
  })

  it('labels manual action updates as record-only changes and keeps the drawer current', () => {
    const onActionUpdated = vi.fn()
    const updatedAlert = { ...alertFixture, action_taken: 'BLOCKED' as const }

    render(
      <AlertDrawer
        role="ADMIN"
        alert={alertFixture}
        onClose={vi.fn()}
        onActionUpdated={onActionUpdated}
      />
    )

    expect(screen.getByText('Recorded: Throttled')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Save as Blocked/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Save as Throttled/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Save as Allowed/ })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /^Save as Blocked/ }))

    expect(actionMutateMock).toHaveBeenCalledWith(
      { id: alertFixture.alert_id, action: 'BLOCKED' },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    )

    const [, options] = actionMutateMock.mock.calls[0]
    options.onSuccess(updatedAlert)

    expect(onActionUpdated).toHaveBeenCalledWith(updatedAlert)
  })

  it('explains when no correlated CRS evidence is available', () => {
    render(
      <AlertDrawer
        alert={{
          ...alertFixture,
          transaction_id: null,
          crs_score: null,
          crs_rule_ids: null,
          matched_rule_messages: null,
          matched_rule_tags: null,
        }}
        onClose={vi.fn()}
      />
    )

    expect(screen.getByText('No correlated CRS evidence available')).toBeInTheDocument()
  })

  it.each([
    ['VIEWER', false, false, false],
    ['ANALYST', true, false, false],
    ['ADMIN', true, true, false],
    [undefined, false, false, false],
    ['FUTURE_ROLE', false, false, false],
    ['OWNER', true, true, true],
  ] as const)(
    'renders mutation affordances for role %s',
    (role, canTriage, canUpdateAction, canManageTrainingFeedback) => {
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

      expect(Boolean(screen.queryByRole('button', { name: /^Resolve/i }))).toBe(canTriage)
      expect(Boolean(screen.queryByRole('button', { name: /^Save as Blocked/ }))).toBe(
        canUpdateAction
      )
      expect(
        Boolean(screen.queryByRole('heading', { name: 'Training feedback' }))
      ).toBe(canManageTrainingFeedback)
      expect(Boolean(screen.queryByLabelText('Verified classification'))).toBe(
        canManageTrainingFeedback
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

  it('shows Owner review controls and requires a selection before submitting', () => {
    render(<AlertDrawer role="OWNER" alert={alertFixture} onClose={vi.fn()} />)

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
      reviewer_id: 'owner-1',
      reviewer_role: 'OWNER',
      reviewed_at: '2026-08-04T00:00:00Z',
    }

    render(
      <AlertDrawer
        role="OWNER"
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

    expect(onReviewUpdated).toHaveBeenCalledWith(alertFixture.alert_id, review)
  })

  it('makes the drawer content vertically scrollable', () => {
    render(<AlertDrawer role="ANALYST" alert={alertFixture} onClose={vi.fn()} />)

    expect(screen.getByTestId('alert-drawer-scroll-region')).toHaveClass('overflow-y-auto')
  })

  it.each(['ADMIN', 'ANALYST', 'VIEWER'] as const)(
    'hides the complete training feedback section from %s',
    (role) => {
      render(<AlertDrawer role={role} alert={alertFixture} onClose={vi.fn()} />)

      expect(
        screen.queryByRole('heading', { name: 'Training feedback' })
      ).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Verified classification')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Review note (optional)')).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Approve for training' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Exclude from training' })).not.toBeInTheDocument()
      expect(screen.getByText('Alert ID')).toBeInTheDocument()
      expect(labelReviewMutateMock).not.toHaveBeenCalled()
    }
  )

  it('shows Normal records as read-only traffic with the stored action and no alert controls', () => {
    render(
      <AlertDrawer
        role="OWNER"
        alert={{
          ...alertFixture,
          alert_id: 'traffic-record-18',
          prediction: 'Normal',
          confidence: 0.82,
          confidence_level: 'MEDIUM',
          action_taken: 'ALLOWED',
          triage_status: null,
        }}
        onClose={vi.fn()}
      />
    )

    expect(screen.getByText('Traffic Details')).toBeInTheDocument()
    expect(screen.getByText('Traffic record ID').closest('dt')?.nextElementSibling).toHaveTextContent(
      'traffic-record-18'
    )
    expect(screen.getByText('Normal').closest('span')).toHaveClass('border-severity-safe-border')
    expect(screen.getByText('Normal traffic has no analyst triage workflow.')).toBeInTheDocument()
    expect(screen.getByText('Recorded action label: Allowed.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start Review' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Resolve' })).not.toBeInTheDocument()
    expect(screen.queryByText('Update action label')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Training feedback' })).not.toBeInTheDocument()
    expect(triageMutateMock).not.toHaveBeenCalled()
    expect(actionMutateMock).not.toHaveBeenCalled()
    expect(labelReviewMutateMock).not.toHaveBeenCalled()
  })
})
