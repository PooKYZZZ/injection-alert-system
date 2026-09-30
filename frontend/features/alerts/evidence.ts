import type { EvidenceRelationship } from './types'

export interface EvidenceRelationshipInput {
  evidence_relationship?: EvidenceRelationship | null
}

const evidenceRelationshipCopy: Record<
  EvidenceRelationship,
  { label: string; description: string }
> = {
  CORROBORATED: {
    label: 'WAF and ML evidence agree',
    description: 'The stored CRS evidence supports the same actionable class as the model prediction.',
  },
  ML_ONLY: {
    label: 'ML assessment only',
    description: 'Model data is available, but no linked CRS evidence was recorded.',
  },
  WAF_ONLY: {
    label: 'WAF evidence only',
    description: 'CRS evidence is available without an actionable model classification.',
  },
  CONFLICTING: {
    label: 'WAF and ML evidence differ',
    description: 'The stored CRS and model evidence support different classifications.',
  },
  INCOMPLETE: {
    label: 'Evidence relationship incomplete',
    description: 'The available records do not support a reliable comparison.',
  },
}

export function describeEvidenceRelationship(
  alert: EvidenceRelationshipInput
): { kind: EvidenceRelationship; label: string; description: string } {
  const kind = alert.evidence_relationship ?? 'INCOMPLETE'
  return { kind, ...evidenceRelationshipCopy[kind] }
}
