import "server-only";

import {
  checkRecordSearchShadowEnforcement,
  type ShadowCheckResult,
  type ShadowEnforcementConfig,
} from "./enforcement-check";

const DEFAULT_ENDPOINT =
  "http://backend:8000/api/internal/enforcement/check";
const DEFAULT_TIMEOUT_MS = 250;

function runtimeConfig(): ShadowEnforcementConfig {
  const rawTimeout = Number(process.env.ENFORCEMENT_CHECK_TIMEOUT_MS);
  return {
    mode: process.env.ENFORCEMENT_MODE === "shadow" ? "shadow" : "off",
    endpoint: process.env.ENFORCEMENT_CHECK_URL?.trim() || DEFAULT_ENDPOINT,
    apiKey: process.env.ENFORCEMENT_CHECK_API_KEY?.trim() || "",
    timeoutMs:
      Number.isFinite(rawTimeout) && rawTimeout > 0
        ? rawTimeout
        : DEFAULT_TIMEOUT_MS,
  };
}

export async function checkRecordSearchShadowEnforcementFromRuntime(): Promise<ShadowCheckResult> {
  const { headers } = await import("next/headers");
  const result = await checkRecordSearchShadowEnforcement({
    requestHeaders: await headers(),
    config: runtimeConfig(),
  });
  if (result.status === "degraded") {
    console.warn(
      JSON.stringify({
        event: "enforcement.shadow_check_degraded",
        reason: result.reason,
        actual_decision: result.decision,
      }),
    );
  }
  return result;
}
