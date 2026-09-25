import { describe, expect, it } from 'vitest'

import { getActionLabelText } from './ActionLabel'

describe('getActionLabelText', () => {
  it('labels LOW actionable ALLOWED traffic as monitor-only', () => {
    expect(getActionLabelText('ALLOWED', 'LOW', 'SQL Injection')).toBe('Monitor Only')
    expect(getActionLabelText('ALLOWED', 'LOW', 'Code Injection')).toBe('Monitor Only')
  })

  it('keeps ordinary allowed and out-of-scope traffic distinct', () => {
    expect(getActionLabelText('ALLOWED', 'LOW', 'Normal')).toBe('Allowed')
    expect(getActionLabelText('ALLOWED', 'LOW', 'Other Attacks')).toBe('Allowed')
    expect(getActionLabelText('ALLOWED', 'MEDIUM', 'SQL Injection')).toBe('Allowed')
  })
})
