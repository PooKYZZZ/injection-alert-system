import { describe, expect, it } from 'vitest'

import { parseAuthE2EState } from './state'

const identity = {
  id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
  email: 'auth-e2e@example.test',
  password: 'high-entropy-disposable-password',
}

const validState = {
  runId: '6f86bfb4-6fe0-4c77-9f04-665ab15b9d10',
  identities: {
    enroll: identity,
    login: { ...identity, id: '8b8bb9de-1dff-44b7-9a44-12efe8a6716f', email: 'login-e2e@example.test', totpSecret: 'JBSWY3DPEHPK3PXP' },
    backup: { ...identity, id: '9c9bb9de-1dff-44b7-9a44-12efe8a6716f', email: 'backup-e2e@example.test', backupCode: 'ABCD-EFGH-JKLM' },
    email: { ...identity, id: 'adabb9de-1dff-44b7-9a44-12efe8a6716f', email: 'email-e2e@example.test' },
    stepup: { ...identity, id: 'bebbb9de-1dff-44b7-9a44-12efe8a6716f', email: 'stepup-e2e@example.test', totpSecret: 'JBSWY3DPEHPK3PXP' },
  },
  roleMatrix: {
    owner: { ...identity, id: 'cfbbb9de-1dff-44b7-9a44-12efe8a6716f', email: 'owner-e2e@example.test', totpSecret: 'JBSWY3DPEHPK3PXP' },
    admin: { ...identity, id: 'd0bbb9de-1dff-44b7-9a44-12efe8a6716f', email: 'admin-e2e@example.test', totpSecret: 'JBSWY3DPEHPK3PXP' },
    analyst: { ...identity, id: 'e1bbb9de-1dff-44b7-9a44-12efe8a6716f', email: 'analyst-e2e@example.test', totpSecret: 'JBSWY3DPEHPK3PXP' },
    viewer: { ...identity, id: 'f2bbb9de-1dff-44b7-9a44-12efe8a6716f', email: 'viewer-e2e@example.test' },
  },
}

describe('authentication E2E state', () => {
  it('accepts isolated identities and purpose-specific secret material', () => {
    expect(parseAuthE2EState(JSON.stringify(validState))).toEqual(validState)
  })

  it('rejects identities that are not isolated from one another', () => {
    const duplicated = structuredClone(validState)
    duplicated.identities.login.id = duplicated.identities.enroll.id
    duplicated.identities.login.email = duplicated.identities.enroll.email

    expect(() => parseAuthE2EState(JSON.stringify(duplicated))).toThrow(
      'Authentication E2E state is unavailable.'
    )
  })

  it('rejects malformed state without echoing supplied values', () => {
    const raw = JSON.stringify({ password: 'must-not-appear' })

    expect(() => parseAuthE2EState(raw)).toThrow(
      'Authentication E2E state is unavailable.'
    )
    try {
      parseAuthE2EState(raw)
    } catch (error) {
      expect(String(error)).not.toContain('must-not-appear')
    }
  })
})
