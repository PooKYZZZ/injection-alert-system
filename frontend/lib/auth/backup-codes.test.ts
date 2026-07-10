import { describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import {
  BACKUP_CODE_COUNT,
  BACKUP_CODE_PATTERN,
  generateBackupCodes,
  hashBackupCode,
  verifyBackupCode,
} from './backup-codes'

describe('backup codes', () => {
  it('generates eight human-readable unique codes', () => {
    const codes = generateBackupCodes()
    expect(codes).toHaveLength(BACKUP_CODE_COUNT)
    expect(new Set(codes).size).toBe(BACKUP_CODE_COUNT)
    for (const code of codes) expect(code).toMatch(BACKUP_CODE_PATTERN)
  })

  it('hashes and verifies a code without retaining plaintext', async () => {
    const code = generateBackupCodes(1)[0]
    const hash = await hashBackupCode(code)
    expect(hash).not.toContain(code)
    await expect(verifyBackupCode(hash, code)).resolves.toBe(true)
    await expect(verifyBackupCode(hash, 'AAAA-BBBB-CCCC')).resolves.toBe(false)
  })
})
