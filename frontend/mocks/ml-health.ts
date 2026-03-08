import { MLHealthData } from '@/features/ml-health/types'
import { CONFIDENCE_THRESHOLDS } from '@/lib/constants'

export const MOCK_ML_HEALTH: MLHealthData = {
  model_version: "v1.2.4",
  status: "HEALTHY",
  latency_ms: 45,
  latency_trend: -2,
  drift_score: 0.02,
  drift_status: "NORMAL",
  traffic_processed: 120500,
  thresholds: {
    low: CONFIDENCE_THRESHOLDS.LOW,
    medium: CONFIDENCE_THRESHOLDS.MEDIUM,
    high: CONFIDENCE_THRESHOLDS.HIGH,
  }
}
