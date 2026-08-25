import { describe, expect, it } from 'vitest'

import { describeEvidenceRelationship } from './evidence'

describe('describeEvidenceRelationship', () => {
  it('reports that no CRS evidence is correlated when WAF fields are absent', () => {
    expect(
      describeEvidenceRelationship({
        prediction: 'SQL Injection',
        transaction_id: null,
        crs_score: null,
        crs_rule_ids: null,
        matched_rule_messages: null,
        matched_rule_tags: null,
      })
    ).toEqual({
      kind: 'ml_only',
      label: 'ML assessment only',
      description: 'The alert has model data but no WAF fields linked to it.',
    })
  })

  it('calls an exact SQLi CRS tag and SQL Injection prediction corroborated', () => {
    expect(
      describeEvidenceRelationship({
        prediction: 'SQL Injection',
        transaction_id: 'tx-1',
        crs_score: 5,
        crs_rule_ids: ['942100', '949110'],
        matched_rule_messages: ['SQL Injection Attack Detected'],
        matched_rule_tags: ['attack-sqli', 'paranoia-level/1'],
      })
    ).toEqual({
      kind: 'corroborated',
      label: 'WAF and ML evidence agree',
      description: 'The stored CRS attack-sqli tag matches the SQL Injection prediction.',
    })
  })

  it('does not treat a default zero CRS score as correlated evidence by itself', () => {
    expect(
      describeEvidenceRelationship({
        prediction: 'Normal',
        transaction_id: null,
        crs_score: 0,
        crs_rule_ids: [],
        matched_rule_messages: [],
        matched_rule_tags: [],
      })
    ).toEqual({
      kind: 'ml_only',
      label: 'ML assessment only',
      description: 'The alert has model data but no WAF fields linked to it.',
    })
  })

  it('does not claim agreement for WAF evidence without an exact class mapping', () => {
    expect(
      describeEvidenceRelationship({
        prediction: 'Code Injection',
        transaction_id: 'tx-2',
        crs_score: 10,
        crs_rule_ids: ['932160'],
        matched_rule_messages: ['Remote Command Execution'],
        matched_rule_tags: ['attack-rce'],
      })
    ).toEqual({
      kind: 'unmapped',
      label: 'WAF and ML evidence available',
      description: 'Evidence requires analyst correlation because the stored categories are not matched automatically.',
    })
  })

  it('reports a disagreement when an exact SQLi tag conflicts with the model class', () => {
    expect(
      describeEvidenceRelationship({
        prediction: 'Normal',
        transaction_id: 'tx-3',
        crs_score: 5,
        crs_rule_ids: ['942100'],
        matched_rule_messages: null,
        matched_rule_tags: ['attack-sqli'],
      })
    ).toEqual({
      kind: 'disagreement',
      label: 'WAF and ML evidence differ',
      description: 'The stored CRS attack-sqli tag does not match the Normal prediction.',
    })
  })
})
