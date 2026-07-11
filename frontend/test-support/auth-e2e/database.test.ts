import { describe, expect, it } from 'vitest'

import { safeDatabaseErrorCode } from './database'

describe('authentication E2E database diagnostics', () => {
  it('retains only a bounded database error code', () => {
    expect(safeDatabaseErrorCode({ code: '42501', details: 'secret row' })).toBe(
      '42501'
    )
    expect(safeDatabaseErrorCode({ code: 'not safe!' })).toBe('UNKNOWN')
    expect(safeDatabaseErrorCode({ details: 'secret row' })).toBe('UNKNOWN')
  })
})
