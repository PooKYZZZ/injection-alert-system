import { describe, expect, it } from 'vitest'

import { SAFE_FAILURE_CONTEXT } from './failure-artifacts'

describe('authentication E2E failure artifacts', () => {
  it('uses a fixed context that cannot contain interactive values', () => {
    expect(SAFE_FAILURE_CONTEXT).toBe(
      '# Page snapshot\n\nInteractive values are omitted. See the masked failure screenshot.'
    )
  })
})
