import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it } from 'vitest'

import { MLEnforcementMap } from './MLEnforcementMap'

afterEach(() => {
  cleanup()
})

describe('MLEnforcementMap', () => {
  it('renders an explicit actionable-attack count contract and all policy actions', () => {
    render(
      <MLEnforcementMap
        nonNormalCounts={{ critical: 4, high: 3, medium: 2, low: 1, informational: 5 }}
      />
    )

    expect(screen.getByText('Configured response policy')).toBeInTheDocument()
    expect(
      screen.getByText('Normal predictions remain ALLOWED; INFORMATIONAL and LOW actionable detections are ALLOWED with MONITOR ONLY intent; out-of-scope labels do not enter this policy.')
    ).toBeInTheDocument()
    const criticalRow = screen.getByText('CRITICAL actionable detections').closest('div')?.parentElement
    const highRow = screen.getByText('HIGH actionable detections').closest('div')?.parentElement
    const mediumRow = screen.getByText('MEDIUM actionable detections').closest('div')?.parentElement
    const lowRow = screen.getByText('LOW actionable detections').closest('div')?.parentElement
    const informationalRow = screen.getByText('INFORMATIONAL actionable detections').closest('div')?.parentElement
    expect(criticalRow).not.toBeNull()
    expect(highRow).not.toBeNull()
    expect(mediumRow).not.toBeNull()
    expect(lowRow).not.toBeNull()
    expect(informationalRow).not.toBeNull()
    expect(within(criticalRow as HTMLElement).getByText('BLOCK WITH EVIDENCE')).toBeInTheDocument()
    expect(within(highRow as HTMLElement).getByText('BLOCK WITH EVIDENCE')).toBeInTheDocument()
    expect(within(mediumRow as HTMLElement).getByText('THROTTLE WITH EVIDENCE')).toBeInTheDocument()
    expect(within(lowRow as HTMLElement).getByText('MONITOR ONLY')).toBeInTheDocument()
    expect(within(informationalRow as HTMLElement).getByText('MONITOR ONLY')).toBeInTheDocument()
    expect(screen.queryByText(/strictly bound/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/CRITICAL always BLOCKED/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/CRITICAL confidence always maps to BLOCKED/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/action_taken=CRITICAL/i)).not.toBeInTheDocument()
  })

  it('explains tier counts and each distinct response intent without claiming a runtime outcome', async () => {
    const user = userEvent.setup()
    render(
      <MLEnforcementMap
        nonNormalCounts={{ critical: 4, high: 3, medium: 2, low: 1, informational: 5 }}
      />
    )

    for (const tier of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']) {
      expect(
        screen.getAllByRole('button', { name: `About ${tier} actionable detections` })
      ).toHaveLength(1)
    }
    expect(screen.getAllByRole('button', { name: 'About Block with evidence' })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: 'About Throttle with evidence' })).toHaveLength(1)
    expect(screen.getAllByRole('button', { name: 'About Monitor only' })).toHaveLength(2)

    await user.click(screen.getByRole('button', { name: 'About HIGH actionable detections' }))
    expect(screen.getByRole('region', { name: 'HIGH actionable detections explanation' })).toHaveTextContent(
      /not a count of guaranteed unique HTTP requests/i
    )

    await user.click(screen.getAllByRole('button', { name: 'About Block with evidence' })[0])
    const blockHelp = screen.getByRole('region', { name: 'Block with evidence explanation' })
    expect(blockHelp).toHaveTextContent(/strong CRS evidence matches the predicted attack family/i)
    expect(blockHelp).toHaveTextContent(/does not confirm an HTTP block/i)

    await user.click(screen.getByRole('button', { name: 'About Throttle with evidence' }))
    const throttleHelp = screen.getByRole('region', { name: 'Throttle with evidence explanation' })
    expect(throttleHelp).toHaveTextContent(/repeated-suspicious-activity threshold/i)
    expect(throttleHelp).toHaveTextContent(/does not confirm throttling/i)

    await user.click(screen.getAllByRole('button', { name: 'About Monitor only' })[0])
    expect(screen.getByRole('region', { name: 'Monitor only explanation' })).toHaveTextContent(
      /does not prove the request was allowed by every system layer/i
    )
  })
})
