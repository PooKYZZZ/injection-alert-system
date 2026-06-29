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
    medium: (CONFIDENCE_THRESHOLDS.LOW + CONFIDENCE_THRESHOLDS.HIGH) / 2,
    high: CONFIDENCE_THRESHOLDS.HIGH,
    critical: CONFIDENCE_THRESHOLDS.CRITICAL,
  },
  // Optional eval metadata from model registry artifacts
  macro_f1: 0.924,
  ece: 0.031,
  per_class_f1: {
    sqli: 0.94,
    xss: 0.91,
    benign: 0.96,
  },
  calibration_bins: [
    { bin_idx: 0, bin_center: 0.05, accuracy: 0.02, confidence: 0.05, count: 120 },
    { bin_idx: 1, bin_center: 0.15, accuracy: 0.12, confidence: 0.15, count: 450 },
    { bin_idx: 2, bin_center: 0.25, accuracy: 0.22, confidence: 0.25, count: 890 },
    { bin_idx: 3, bin_center: 0.35, accuracy: 0.34, confidence: 0.35, count: 1200 },
    { bin_idx: 4, bin_center: 0.45, accuracy: 0.44, confidence: 0.45, count: 1500 },
    { bin_idx: 5, bin_center: 0.55, accuracy: 0.56, confidence: 0.55, count: 1800 },
    { bin_idx: 6, bin_center: 0.65, accuracy: 0.66, confidence: 0.65, count: 2200 },
    { bin_idx: 7, bin_center: 0.75, accuracy: 0.76, confidence: 0.75, count: 2600 },
    { bin_idx: 8, bin_center: 0.85, accuracy: 0.86, confidence: 0.85, count: 3100 },
    { bin_idx: 9, bin_center: 0.95, accuracy: 0.96, confidence: 0.95, count: 4500 },
  ],
  prediction_distribution: {
    baseline: { sqli: 3200, xss: 2700, benign: 8500 },
    current: { sqli: 3420, xss: 2850, benign: 8920 },
  },
  queue: {
    enabled: true,
    max_size: 100,
    depth: 0,
    available_capacity: 100,
    worker_count: 1,
    worker_running: true,
    total_enqueued: 0,
    total_processed: 0,
    total_failed: 0,
    overflow_count: 0,
    last_error: null,
    last_error_at: null,
    last_processed_at: null,
  },
}
