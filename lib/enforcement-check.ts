import { isIP } from "node:net";

export type EnforcementMode = "off" | "shadow" | "enforce";
export type EnforcementScope =
  | "RECORD_SEARCH"
  | "RECORD_DETAIL"
  | "TRACK_STATUS"
  | "SUPPORT_SUBMIT"
  | "APPOINTMENT_SUBMIT"
  | "COMMENTS_SUBMIT"
  | "LOGIN_SUBMIT"
  | "REQUEST_COPY_SUBMIT";
export type AppEnv =
  | "development"
  | "testing"
  | "staging"
  | "production"
  | "invalid";

export const MIN_CHALLENGE_TIMEOUT_MS = 4000;

export type EnforcementConfig = {
  mode: EnforcementMode;
  endpoint: string;
  challengeEndpoint?: string;
  apiKey: string;
  timeoutMs: number;
  challengeTimeoutMs?: number;
  siteKey?: string;
  allowUnverifiedSourceForTests?: boolean;
  sourceTrustMode?: "unverified" | "cloudflare_verified";
  appEnv?: AppEnv;
};

export type ShadowEnforcementConfig = Omit<EnforcementConfig, "mode"> & {
  mode: "off" | "shadow";
};

export type EnforcementCheckResult =
  | { decision: "ALLOW"; status: "skipped"; reason: "MODE_OFF" | "NO_SOURCE_IP" }
  | { decision: "ALLOW"; status: "checked"; decisionReason?: string }
  | {
      decision: "CHALLENGE";
      status: "checked";
      tier: "LOW" | "MEDIUM";
      decisionReason?: string;
    }
  | {
      decision: "THROTTLE";
      status: "checked";
      retryAfterSeconds: number;
      decisionReason?: string;
    }
  | { decision: "BLOCK"; status: "checked"; decisionReason?: string }
  | {
      decision: "ALLOW";
      status: "degraded";
      reason:
        | "CONFIG_INVALID"
        | "HTTP_ERROR"
        | "TIMEOUT_OR_NETWORK"
        | "INVALID_RESPONSE";
    };

export type ShadowCheckResult = Extract<
  EnforcementCheckResult,
  { decision: "ALLOW" }
>;

type InternalChallengeFailureStatus =
  | "INVALID"
  | "UNAVAILABLE"
  | "NO_ACTIVE_ENFORCEMENT"
  | "SOURCE_INELIGIBLE";

export type ChallengeVerificationResult =
  | { verified: true; status: "VERIFIED" }
  | {
      verified: false;
      status: InternalChallengeFailureStatus;
    };

export type BrowserChallengeVerificationResult =
  | { verified: true; status: "VERIFIED" }
  | {
      verified: false;
      status: "INVALID" | "UNAVAILABLE" | "NO_LONGER_REQUIRED";
    };

const TURNSTILE_TEST_SITE_KEYS = new Set([
  "1x00000000000000000000AA",
  "2x00000000000000000000AB",
  "1x00000000000000000000BB",
  "2x00000000000000000000BB",
  "3x00000000000000000000FF",
]);

export function validateActiveEnforcementConfig(
  config: EnforcementConfig,
): boolean {
  if (config.mode !== "enforce") return true;
  const appEnv = config.appEnv ?? "development";
  const deployed = appEnv === "production" || appEnv === "staging";
  const controlledTestEnvironment =
    appEnv === "development" || appEnv === "testing";
  return Boolean(
    config.challengeEndpoint &&
      config.siteKey &&
      config.challengeTimeoutMs &&
      config.challengeTimeoutMs >= MIN_CHALLENGE_TIMEOUT_MS &&
      appEnv !== "invalid" &&
      (!config.allowUnverifiedSourceForTests || controlledTestEnvironment) &&
      (config.allowUnverifiedSourceForTests ||
        config.sourceTrustMode === "cloudflare_verified") &&
      !(deployed && TURNSTILE_TEST_SITE_KEYS.has(config.siteKey)),
  );
}

type FetchLike = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

function validIp(value: string | null): string | null {
  const candidate = value?.trim() || "";
  return candidate && !candidate.includes(",") && isIP(candidate) !== 0
    ? candidate
    : null;
}

function firstForwardedAddress(value: string | null): string | null {
  for (const hop of value?.split(",") || []) {
    const candidate = validIp(hop);
    if (candidate) return candidate;
  }
  return null;
}

export function requestSourceIp(
  requestHeaders: Pick<Headers, "get">,
  options: { active?: boolean; allowUnverifiedSourceForTests?: boolean } = {},
) {
  const cloudflareIp = validIp(requestHeaders.get("cf-connecting-ip"));
  if (cloudflareIp) return cloudflareIp;
  if (options.active && !options.allowUnverifiedSourceForTests) return null;
  return firstForwardedAddress(requestHeaders.get("x-forwarded-for"));
}

function validDecisionReason(value: unknown): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= 128;
}

function exactAllowResponse(
  value: unknown,
): value is { decision: "ALLOW"; decision_reason?: string } {
  if (value === null || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record);
  return (
    (keys.length === 1 || keys.length === 2) &&
    record.decision === "ALLOW" &&
    (keys.length === 1 || validDecisionReason(record.decision_reason))
  );
}

function parseActiveResponse(value: unknown):
  | { decision: "ALLOW"; decisionReason?: string }
  | { decision: "CHALLENGE"; tier: "LOW" | "MEDIUM"; decisionReason?: string }
  | { decision: "THROTTLE"; retryAfterSeconds: number; decisionReason?: string }
  | { decision: "BLOCK"; decisionReason?: string }
  | null {
  if (value === null || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (exactAllowResponse(value)) {
    return {
      decision: "ALLOW",
      ...(validDecisionReason(record.decision_reason)
        ? { decisionReason: record.decision_reason }
        : {}),
    };
  }
  if (
    (Object.keys(record).length === 1 || Object.keys(record).length === 2) &&
    record.decision === "BLOCK" &&
    (Object.keys(record).length === 1 || validDecisionReason(record.decision_reason))
  ) {
    return {
      decision: "BLOCK",
      ...(validDecisionReason(record.decision_reason)
        ? { decisionReason: record.decision_reason }
        : {}),
    };
  }
  if (
    (Object.keys(record).length === 2 || Object.keys(record).length === 3) &&
    record.decision === "CHALLENGE" &&
    (record.enforcement_tier === "LOW" || record.enforcement_tier === "MEDIUM") &&
    (Object.keys(record).length === 2 || validDecisionReason(record.decision_reason))
  ) {
    return {
      decision: "CHALLENGE",
      tier: record.enforcement_tier,
      ...(validDecisionReason(record.decision_reason)
        ? { decisionReason: record.decision_reason }
        : {}),
    };
  }
  if (
    (Object.keys(record).length === 2 || Object.keys(record).length === 3) &&
    record.decision === "THROTTLE" &&
    typeof record.retry_after_seconds === "number" &&
    Number.isInteger(record.retry_after_seconds) &&
    record.retry_after_seconds >= 1 &&
    (Object.keys(record).length === 2 || validDecisionReason(record.decision_reason))
  ) {
    return {
      decision: "THROTTLE",
      retryAfterSeconds: record.retry_after_seconds,
      ...(validDecisionReason(record.decision_reason)
        ? { decisionReason: record.decision_reason }
        : {}),
    };
  }
  return null;
}

export async function checkEnforcement({
  requestHeaders,
  config,
  scope,
  fetchImpl = fetch,
}: {
  requestHeaders: Pick<Headers, "get">;
  config: EnforcementConfig;
  scope: EnforcementScope;
  fetchImpl?: FetchLike;
}): Promise<EnforcementCheckResult> {
  if (config.mode === "off") {
    return { decision: "ALLOW", status: "skipped", reason: "MODE_OFF" };
  }

  const active = config.mode === "enforce";
  const activeConfigInvalid = active && !validateActiveEnforcementConfig(config);
  if (
    !config.apiKey ||
    !config.endpoint ||
    config.timeoutMs <= 0 ||
    activeConfigInvalid
  ) {
    return { decision: "ALLOW", status: "degraded", reason: "CONFIG_INVALID" };
  }
  const sourceIp = requestSourceIp(requestHeaders, {
    active,
    allowUnverifiedSourceForTests: config.allowUnverifiedSourceForTests,
  });
  if (!sourceIp) {
    return { decision: "ALLOW", status: "skipped", reason: "NO_SOURCE_IP" };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.timeoutMs);
  try {
    const response = await fetchImpl(config.endpoint, {
      method: "POST",
      headers: {
        authorization: `Bearer ${config.apiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ scope, source_ip: sourceIp }),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      return { decision: "ALLOW", status: "degraded", reason: "HTTP_ERROR" };
    }

    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return { decision: "ALLOW", status: "degraded", reason: "INVALID_RESPONSE" };
    }
    if (!active) {
      return exactAllowResponse(body)
        ? {
            decision: "ALLOW",
            status: "checked",
            ...(validDecisionReason(
              (body as Record<string, unknown>).decision_reason,
            )
              ? {
                  decisionReason: (body as Record<string, unknown>)
                    .decision_reason as string,
                }
              : {}),
          }
        : { decision: "ALLOW", status: "degraded", reason: "INVALID_RESPONSE" };
    }
    const parsed = parseActiveResponse(body);
    if (!parsed) {
      return { decision: "ALLOW", status: "degraded", reason: "INVALID_RESPONSE" };
    }
    if (parsed.decision === "ALLOW") {
      return {
        decision: "ALLOW",
        status: "checked",
        ...(parsed.decisionReason
          ? { decisionReason: parsed.decisionReason }
          : {}),
      };
    }
    if (parsed.decision === "CHALLENGE") {
      return {
        decision: "CHALLENGE",
        status: "checked",
        tier: parsed.tier,
        ...(parsed.decisionReason
          ? { decisionReason: parsed.decisionReason }
          : {}),
      };
    }
    if (parsed.decision === "BLOCK") {
      return {
        decision: "BLOCK",
        status: "checked",
        ...(parsed.decisionReason
          ? { decisionReason: parsed.decisionReason }
          : {}),
      };
    }
    return {
      decision: "THROTTLE",
      status: "checked",
      retryAfterSeconds: parsed.retryAfterSeconds,
      ...(parsed.decisionReason
        ? { decisionReason: parsed.decisionReason }
        : {}),
    };
  } catch {
    return {
      decision: "ALLOW",
      status: "degraded",
      reason: "TIMEOUT_OR_NETWORK",
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkRecordSearchEnforcement({
  requestHeaders,
  config,
  fetchImpl = fetch,
}: {
  requestHeaders: Pick<Headers, "get">;
  config: EnforcementConfig;
  fetchImpl?: FetchLike;
}): Promise<EnforcementCheckResult> {
  return checkEnforcement({
    requestHeaders,
    config,
    scope: "RECORD_SEARCH",
    fetchImpl,
  });
}

export function enforcementRuntimeLogEvent(result: EnforcementCheckResult) {
  if (result.status === "degraded") {
    return {
      event: "enforcement.check_degraded",
      reason: result.reason,
      actual_decision: result.decision,
    } as const;
  }
  return null;
}

export function applicationBlockAppliedLogEvent(
  scope: EnforcementScope = "RECORD_SEARCH",
) {
  return {
    event: "enforcement.application_block_applied",
    scope,
    actual_decision: "BLOCK",
  } as const;
}

export async function checkRecordSearchShadowEnforcement({
  requestHeaders,
  config,
  fetchImpl = fetch,
}: {
  requestHeaders: Pick<Headers, "get">;
  config: ShadowEnforcementConfig;
  fetchImpl?: FetchLike;
}): Promise<ShadowCheckResult> {
  return checkRecordSearchEnforcement({
    requestHeaders,
    config,
    fetchImpl,
  }) as Promise<ShadowCheckResult>;
}

export async function verifyEnforcementChallenge({
  requestHeaders,
  config,
  scope,
  token,
  fetchImpl = fetch,
}: {
  requestHeaders: Pick<Headers, "get">;
  config: EnforcementConfig;
  scope: EnforcementScope;
  token: string;
  fetchImpl?: FetchLike;
}): Promise<ChallengeVerificationResult> {
  if (
    config.mode !== "enforce" ||
    !config.apiKey ||
    !config.endpoint ||
    !validateActiveEnforcementConfig(config)
  ) {
    return { verified: false, status: "UNAVAILABLE" };
  }
  const sourceIp = requestSourceIp(requestHeaders, {
    active: true,
    allowUnverifiedSourceForTests: config.allowUnverifiedSourceForTests,
  });
  if (!sourceIp || !token || token.length > 2048) {
    return { verified: false, status: "INVALID" };
  }
  const challengeEndpoint = config.challengeEndpoint;
  if (!challengeEndpoint) {
    return { verified: false, status: "UNAVAILABLE" };
  }

  const controller = new AbortController();
  const timeout = setTimeout(
    () => controller.abort(),
    config.challengeTimeoutMs ?? config.timeoutMs,
  );
  try {
    const response = await fetchImpl(challengeEndpoint, {
      method: "POST",
      headers: {
        authorization: `Bearer ${config.apiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ scope, source_ip: sourceIp, token }),
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) return { verified: false, status: "UNAVAILABLE" };
    const body = (await response.json()) as Record<string, unknown>;
    if (body.verified === true && body.status === "VERIFIED") {
      return { verified: true, status: "VERIFIED" };
    }
    if (
      body.verified === false &&
      [
        "INVALID",
        "UNAVAILABLE",
        "NO_ACTIVE_ENFORCEMENT",
        "SOURCE_INELIGIBLE",
      ].includes(body.status as string)
    ) {
      return {
        verified: false,
        status: body.status as InternalChallengeFailureStatus,
      };
    }
    return { verified: false, status: "UNAVAILABLE" };
  } catch {
    return { verified: false, status: "UNAVAILABLE" };
  } finally {
    clearTimeout(timeout);
  }
}

export async function verifyRecordSearchEnforcementChallenge({
  requestHeaders,
  config,
  token,
  fetchImpl = fetch,
}: {
  requestHeaders: Pick<Headers, "get">;
  config: EnforcementConfig;
  token: string;
  fetchImpl?: FetchLike;
}): Promise<ChallengeVerificationResult> {
  return verifyEnforcementChallenge({
    requestHeaders,
    config,
    scope: "RECORD_SEARCH",
    token,
    fetchImpl,
  });
}

export function normalizeBrowserChallengeResult(
  result: ChallengeVerificationResult,
): BrowserChallengeVerificationResult {
  if (result.verified) return result;
  if (
    result.status === "NO_ACTIVE_ENFORCEMENT" ||
    result.status === "SOURCE_INELIGIBLE"
  ) {
    return { verified: false, status: "NO_LONGER_REQUIRED" };
  }
  return { verified: false, status: result.status };
}
