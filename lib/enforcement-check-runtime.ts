import "server-only";

import {
  checkRecordSearchEnforcement,
  enforcementRuntimeLogEvent,
  verifyRecordSearchEnforcementChallenge,
  type ChallengeVerificationResult,
  type EnforcementCheckResult,
  type EnforcementConfig,
  type AppEnv,
} from "./enforcement-check";

const DEFAULT_ENDPOINT =
  "http://backend:8000/api/internal/enforcement/check";
const DEFAULT_CHALLENGE_ENDPOINT =
  "http://backend:8000/api/internal/enforcement/challenge";
const DEFAULT_TIMEOUT_MS = 1000;
const DEFAULT_CHALLENGE_TIMEOUT_MS = 5000;

function parseAppEnv(value: string | undefined): AppEnv {
  if (
    value === "development" ||
    value === "testing" ||
    value === "staging" ||
    value === "production"
  ) {
    return value;
  }
  return value ? "invalid" : "development";
}

function runtimeConfig(): EnforcementConfig {
  const rawTimeout = Number(process.env.ENFORCEMENT_CHECK_TIMEOUT_MS);
  const rawChallengeTimeout = Number(
    process.env.ENFORCEMENT_CHALLENGE_TIMEOUT_MS,
  );
  const mode =
    process.env.ENFORCEMENT_MODE === "enforce"
      ? "enforce"
      : process.env.ENFORCEMENT_MODE === "shadow"
        ? "shadow"
        : "off";
  return {
    mode,
    endpoint: process.env.ENFORCEMENT_CHECK_URL?.trim() || DEFAULT_ENDPOINT,
    challengeEndpoint:
      process.env.ENFORCEMENT_CHALLENGE_URL?.trim() ||
      DEFAULT_CHALLENGE_ENDPOINT,
    apiKey: process.env.ENFORCEMENT_CHECK_API_KEY?.trim() || "",
    timeoutMs:
      Number.isFinite(rawTimeout) && rawTimeout > 0
        ? rawTimeout
        : DEFAULT_TIMEOUT_MS,
    challengeTimeoutMs:
      Number.isFinite(rawChallengeTimeout) && rawChallengeTimeout > 0
        ? rawChallengeTimeout
        : DEFAULT_CHALLENGE_TIMEOUT_MS,
    siteKey: process.env.ENFORCEMENT_TURNSTILE_SITE_KEY?.trim() || "",
    allowUnverifiedSourceForTests:
      process.env.ENFORCEMENT_ALLOW_UNVERIFIED_SOURCE_FOR_TESTS === "true",
    sourceTrustMode:
      process.env.ENFORCEMENT_SOURCE_TRUST_MODE === "cloudflare_verified"
        ? "cloudflare_verified"
        : "unverified",
    appEnv: parseAppEnv(process.env.APP_ENV || process.env.NODE_ENV),
  };
}

export function enforcementRuntimeConfig(): EnforcementConfig {
  return runtimeConfig();
}

export async function checkRecordSearchEnforcementFromRuntime(): Promise<EnforcementCheckResult> {
  const { headers } = await import("next/headers");
  const result = await checkRecordSearchEnforcement({
    requestHeaders: await headers(),
    config: runtimeConfig(),
  });
  const logEntry = enforcementRuntimeLogEvent(result);
  if (logEntry) {
    console.warn(JSON.stringify(logEntry));
  }
  return result;
}

export async function checkRecordSearchShadowEnforcementFromRuntime(): Promise<EnforcementCheckResult> {
  return checkRecordSearchEnforcementFromRuntime();
}

export async function verifyRecordSearchEnforcementChallengeFromRuntime(
  token: string,
): Promise<ChallengeVerificationResult> {
  const { headers } = await import("next/headers");
  return verifyRecordSearchEnforcementChallenge({
    requestHeaders: await headers(),
    config: runtimeConfig(),
    token,
  });
}
