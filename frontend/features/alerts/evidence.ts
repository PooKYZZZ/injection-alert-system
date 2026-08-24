import type { AlertPrediction } from './contract'

export type EvidenceRelationshipKind = 'ml_only' | 'corroborated' | 'unmapped' | 'disagreement'

export interface EvidenceRelationship {
  kind: EvidenceRelationshipKind
  label: string
  description: string
}

export interface EvidenceRelationshipInput {
  prediction: AlertPrediction
  transaction_id?: string | null
  crs_score?: number | null
  crs_rule_ids?: string[] | null
  matched_rule_messages?: string[] | null
  matched_rule_tags?: string[] | null
}

function hasCrsEvidence(alert: EvidenceRelationshipInput): boolean {
  return Boolean(
    alert.transaction_id?.trim() ||
      (typeof alert.crs_score === 'number' && alert.crs_score > 0) ||
      alert.crs_rule_ids?.length ||
      alert.matched_rule_messages?.length ||
      alert.matched_rule_tags?.length
  )
}

export function describeEvidenceRelationship(
  alert: EvidenceRelationshipInput
): EvidenceRelationship {
  if (!hasCrsEvidence(alert)) {
    return {
      kind: 'ml_only',
      label: 'ML assessment only',
      description: 'No correlated CRS evidence is available for this alert.',
    }
  }

  const hasExactSqlInjectionTag = (alert.matched_rule_tags ?? []).some(
    (tag) => tag.trim().toLowerCase() === 'attack-sqli'
  )

  if (hasExactSqlInjectionTag && alert.prediction === 'SQL Injection') {
    return {
      kind: 'corroborated',
      label: 'WAF and ML evidence agree',
      description: 'The stored CRS attack-sqli tag matches the SQL Injection prediction.',
    }
  }

  if (hasExactSqlInjectionTag) {
    return {
      kind: 'disagreement',
      label: 'WAF and ML evidence differ',
      description: `The stored CRS attack-sqli tag does not match the ${alert.prediction} prediction.`,
    }
  }

  return {
    kind: 'unmapped',
    label: 'WAF and ML evidence available',
    description: 'Both evidence sources are present, but their stored categories are not mapped automatically.',
  }
}
