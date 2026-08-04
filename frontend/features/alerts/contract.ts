export const ALERT_PREDICTION_VALUES = [
  'SQL Injection',
  'Code Injection',
  'Other Attacks',
  'Normal',
] as const

// Current alert transport values mirror backend-emitted `action_taken` values.
// If `ALLOWED` is later renamed to `LOGGED`, that change must start in backend
// policy/source code and only then propagate through frontend contracts.
export const ALERT_ACTION_TAKEN_VALUES = [
  'BLOCKED',
  'THROTTLED',
  'ALLOWED',
] as const

export const ALERT_CONFIDENCE_TIER_VALUES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const

export type AlertPrediction = (typeof ALERT_PREDICTION_VALUES)[number]
export type AlertAction = (typeof ALERT_ACTION_TAKEN_VALUES)[number]
export type AlertConfidenceTier = (typeof ALERT_CONFIDENCE_TIER_VALUES)[number]
export const ALERT_SEVERITY_VALUES = ALERT_CONFIDENCE_TIER_VALUES
export type AlertSeverity = AlertConfidenceTier

export const VERIFIED_LABEL_VALUES = ALERT_PREDICTION_VALUES
export const LABEL_REVIEW_APPROVAL_STATE_VALUES = [
  'approved_for_training',
  'excluded_from_training',
] as const
export const LABEL_REVIEW_STORED_APPROVAL_STATE_VALUES = [
  ...LABEL_REVIEW_APPROVAL_STATE_VALUES,
  'superseded',
] as const
export type VerifiedLabel = (typeof VERIFIED_LABEL_VALUES)[number]
export type LabelReviewApprovalState = (typeof LABEL_REVIEW_STORED_APPROVAL_STATE_VALUES)[number]

export const ALERT_FIELD_REMAPS = {
  id: 'alert_id',
  source: 'source_ip',
  path: 'request_path',
  method: 'request_method',
  action: 'action_taken',
} as const

export const ALERT_PAGINATION_REMAPS = {
  page_size: 'pageSize',
} as const

export const ALERT_DISPLAY_PREDICTION_ALIASES: Record<AlertPrediction, string> = {
  'SQL Injection': 'SQLi',
  'Code Injection': 'Code Injection',
  'Other Attacks': 'Other Attacks',
  Normal: 'Normal',
}

export const ALERT_DISPLAY_ACTION_ALIASES: Record<AlertAction, string> = {
  BLOCKED: 'Blocked',
  THROTTLED: 'Throttled',
  ALLOWED: 'Allowed',
}
