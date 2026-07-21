import { isIP } from "node:net";

export type EnforcementMode = "off" | "shadow" | "enforce";

export type EnforcementConfig = {
  mode: EnforcementMode;
  endpoint: string;
  challengeEndpoint?: string;
  apiKey: string;
  timeoutMs: number;
  siteKey?: string;
  allowUnverifiedSourceForTests?: boolean;
};

export type ShadowEnforcementConfig = Omit<EnforcementConfig, "mode"> & {
  mode: "off" | "shadow";
};

export type EnforcementCheckResult =
  | { decision: "ALLOW"; status: "skipped"; reason: "MODE_OFF" | "NO_SOURCE_IP" }
  | { decision: "ALLOW"; status: "checked" }
  | { decision: "CHALLENGE"; status: "checked"; tier: "LOW" | "MEDIUM" }
  | { decision: "THROTTLE"; status: "checked"; retryAfterSeconds: number }
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

type ChallengeFailureStatus =
  | "INVALID"
  | "UNAVAILABLE"
  | "NO_ACTIVE_ENFORCEMENT"
  | "SOURCE_INELIGIBLE";

export type ChallengeVerificationResult =
  | { verified: true; status: "VERIFIED" }
  | {
      verified: false;
      status: ChallengeFailureStatus;
    };

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

function exactAllowResponse(value: unknown): value is { decision: "ALLOW" } {
  if (value === null || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return Object.keys(record).length === 1 && record.decision === "ALLOW";
}

function parseActiveResponse(value: unknown):
  | { decision: "ALLOW" }
  | { decision: "CHALLENGE"; tier: "LOW" | "MEDIUM" }
  | { decision: "THROTTLE"; retryAfterSeconds: number }
  | null {
  if (value === null || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  if (exactAllowResponse(value)) return { decision: "ALLOW" };
  if (
    Object.keys(record).length === 2 &&
    record.decision === "CHALLENGE" &&
    (record.enforcement_tier === "LOW" || record.enforcement_tier === "MEDIUM")
  ) {
    return { decision: "CHALLENGE", tier: record.enforcement_tier };
  }
  if (
    Object.keys(record).length === 2 &&
    record.decision === "THROTTLE" &&
    typeof record.retry_after_seconds === "number" &&
    Number.isInteger(record.retry_after_seconds) &&
    record.retry_after_seconds >= 1
  ) {
    return {
      decision: "THROTTLE",
      retryAfterSeconds: record.retry_after_seconds,
    };
  }
  return null;
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
  if (config.mode === "off") {
    return { decision: "ALLOW", status: "skipped", reason: "MODE_OFF" };
  }

  const active = config.mode === "enforce";
  const sourceIp = requestSourceIp(requestHeaders, {
    active,
    allowUnverifiedSourceForTests: config.allowUnverifiedSourceForTests,
  });
  if (!config.apiKey || !config.endpoint || config.timeoutMs <= 0) {
    return { decision: "ALLOW", status: "degraded", reason: "CONFIG_INVALID" };
  }
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
      body: JSON.stringify({ scope: "RECORD_SEARCH", source_ip: sourceIp }),
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
        ? { decision: "ALLOW", status: "checked" }
        : { decision: "ALLOW", status: "degraded", reason: "INVALID_RESPONSE" };
    }
    const parsed = parseActiveResponse(body);
    if (!parsed) {
      return { decision: "ALLOW", status: "degraded", reason: "INVALID_RESPONSE" };
    }
    if (parsed.decision === "ALLOW") return { decision: "ALLOW", status: "checked" };
    if (parsed.decision === "CHALLENGE") {
      return { decision: "CHALLENGE", status: "checked", tier: parsed.tier };
    }
    return {
      decision: "THROTTLE",
      status: "checked",
      retryAfterSeconds: parsed.retryAfterSeconds,
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
  if (config.mode !== "enforce" || !config.apiKey || !config.challengeEndpoint) {
    return { verified: false, status: "UNAVAILABLE" };
  }
  const sourceIp = requestSourceIp(requestHeaders, {
    active: true,
    allowUnverifiedSourceForTests: config.allowUnverifiedSourceForTests,
  });
  if (!sourceIp || !token || token.length > 2048) {
    return { verified: false, status: "INVALID" };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.timeoutMs);
  try {
    const response = await fetchImpl(config.challengeEndpoint, {
      method: "POST",
      headers: {
        authorization: `Bearer ${config.apiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ scope: "RECORD_SEARCH", source_ip: sourceIp, token }),
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
      return { verified: false, status: body.status as ChallengeFailureStatus };
    }
    return { verified: false, status: "UNAVAILABLE" };
  } catch {
    return { verified: false, status: "UNAVAILABLE" };
  } finally {
    clearTimeout(timeout);
  }
}
