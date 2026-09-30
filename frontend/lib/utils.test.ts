import { describe, expect, it } from 'vitest'

import { getConfidenceLevel } from './utils'

describe('getConfidenceLevel', () => {
  it.each([
    [0, 'INFORMATIONAL'],
    [Number.MIN_VALUE, 'LOW'],
    [0.3899, 'LOW'],
    [0.39, 'LOW'],
    [0.3999, 'LOW'],
    [0.4, 'MEDIUM'],
    [0.69, 'MEDIUM'],
    [0.6999, 'MEDIUM'],
    [0.7, 'HIGH'],
    [0.89, 'HIGH'],
    [0.8999, 'HIGH'],
    [0.9, 'CRITICAL'],
    [1.0, 'CRITICAL'],
  ] as const)('maps %s to %s', (confidence, expectedTier) => {
    expect(getConfidenceLevel(confidence)).toBe(expectedTier)
  })
})
