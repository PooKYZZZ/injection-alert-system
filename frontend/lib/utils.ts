import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { CONFIDENCE_THRESHOLDS } from "./constants"
import { AlertSeverity } from "@/features/alerts/types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getConfidenceLevel(confidence: number): AlertSeverity {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return 'HIGH'
  if (confidence >= CONFIDENCE_THRESHOLDS.LOW) return 'MEDIUM'
  return 'LOW'
}

export function formatMs(ms: number): string {
  return `${ms.toFixed(0)} ms`
}
