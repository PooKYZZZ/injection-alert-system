import { describe, expect, it } from 'vitest'

import { describeEvidenceRelationship } from './evidence'

describe('describeEvidenceRelationship', () => {
  it.each([
    ['CORROBORATED', 'WAF and ML evidence agree'],
    ['ML_ONLY', 'ML assessment only'],
    ['WAF_ONLY', 'WAF evidence only'],
    ['CONFLICTING', 'WAF and ML evidence differ'],
    ['INCOMPLETE', 'Evidence relationship incomplete'],
  ] as const)('uses the backend %s relationship without reclassifying it', (kind, label) => {
    expect(describeEvidenceRelationship({ evidence_relationship: kind })).toMatchObject({
      kind,
      label,
    })
  })

  it('reports incomplete when detail evidence is unavailable', () => {
    expect(describeEvidenceRelationship({ evidence_relationship: null })).toMatchObject({
      kind: 'INCOMPLETE',
      label: 'Evidence relationship incomplete',
    })
  })
})
