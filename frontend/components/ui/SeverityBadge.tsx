'use client'

import type { AlertConfidenceTier, AlertPrediction } from '@/features/alerts/contract'
import { ConfidenceTierBadge } from './ConfidenceTierBadge'

interface SeverityBadgeProps {
  severity: AlertConfidenceTier
  prediction?: AlertPrediction
}

export function SeverityBadge({ severity, prediction }: SeverityBadgeProps) {
  return <ConfidenceTierBadge confidenceTier={severity} prediction={prediction} />
}

