import 'server-only'

import { randomInt } from 'node:crypto'

import { hashPassword, verifyPasswordHash } from './password-hash'

export const BACKUP_CODE_COUNT = 8
export const BACKUP_CODE_PATTERN = /^[2-9A-HJ-NP-Z]{4}(?:-[2-9A-HJ-NP-Z]{4}){2}$/
const BACKUP_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'

export function generateBackupCodes(count = BACKUP_CODE_COUNT): string[] {
  if (!Number.isInteger(count) || count < 1 || count > 32) {
    throw new Error('Backup-code count is invalid.')
  }
  const codes = new Set<string>()
  while (codes.size < count) {
    const characters = Array.from({ length: 12 }, () =>
      BACKUP_ALPHABET[randomInt(BACKUP_ALPHABET.length)]
    )
    codes.add(`${characters.slice(0, 4).join('')}-${characters.slice(4, 8).join('')}-${characters.slice(8).join('')}`)
  }
  return [...codes]
}

export function backupCodeLookupPrefix(code: string): string {
  return code.replace(/-/g, '').slice(0, 4)
}

export function normalizeBackupCode(code: unknown): string | null {
  if (typeof code !== 'string') return null
  const normalized = code.trim().toUpperCase()
  return BACKUP_CODE_PATTERN.test(normalized) ? normalized : null
}

export async function hashBackupCode(code: string): Promise<string> {
  const normalized = normalizeBackupCode(code)
  if (!normalized) throw new Error('Backup code is invalid.')
  return hashPassword(normalized)
}

export async function verifyBackupCode(hash: string, code: string): Promise<boolean> {
  const normalized = normalizeBackupCode(code)
  if (!normalized) return false
  return verifyPasswordHash(hash, normalized)
}
