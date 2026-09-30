import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { CONFIDENCE_THRESHOLDS } from "./constants"
import { AlertConfidenceTier } from "@/features/alerts/types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getConfidenceLevel(confidence: number): AlertConfidenceTier {
  if (confidence === 0) return 'INFORMATIONAL'
  if (confidence < CONFIDENCE_THRESHOLDS.LOW) return 'LOW'
  if (confidence < CONFIDENCE_THRESHOLDS.HIGH) return 'MEDIUM'
  if (confidence < CONFIDENCE_THRESHOLDS.CRITICAL) return 'HIGH'
  return 'CRITICAL'
}

export function formatMs(ms: number): string {
  return `${ms.toFixed(0)} ms`
}
