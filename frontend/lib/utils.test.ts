import { describe, expect, it } from 'vitest'

import { getConfidenceLevel } from './utils'

describe('getConfidenceLevel', () => {
  it.each([
    [0.49, 'LOW'],
    [0.5, 'MEDIUM'],
    [0.8, 'MEDIUM'],
    [0.800001, 'HIGH'],
    [0.899999, 'HIGH'],
    [0.9, 'CRITICAL'],
    [1.0, 'CRITICAL'],
  ] as const)('maps %s to %s', (confidence, expectedTier) => {
    expect(getConfidenceLevel(confidence)).toBe(expectedTier)
  })
})
