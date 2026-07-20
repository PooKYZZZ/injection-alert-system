import { isIP } from "node:net";

const DEFAULT_ENDPOINT =
  "http://backend:8000/api/internal/enforcement/check";
const DEFAULT_TIMEOUT_MS = 250;

export type ShadowEnforcementConfig = {
  mode: "off" | "shadow";
  endpoint: string;
  apiKey: string;
  timeoutMs: number;
};

export type ShadowCheckResult = {
  decision: "ALLOW";
  status: "skipped" | "checked" | "degraded";
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

export function requestSourceIp(requestHeaders: Pick<Headers, "get">) {
  return (
    validIp(requestHeaders.get("cf-connecting-ip")) ||
    firstForwardedAddress(requestHeaders.get("x-forwarded-for")) ||
    null
  );
}

function exactAllowResponse(value: unknown): value is { decision: "ALLOW" } {
  if (value === null || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return (
    Object.keys(record).length === 1 && record.decision === "ALLOW"
  );
}

function runtimeConfig(): ShadowEnforcementConfig {
  const rawTimeout = Number(process.env.ENFORCEMENT_CHECK_TIMEOUT_MS);
  return {
    mode: process.env.ENFORCEMENT_MODE === "shadow" ? "shadow" : "off",
    endpoint:
      process.env.ENFORCEMENT_CHECK_URL?.trim() || DEFAULT_ENDPOINT,
    apiKey: process.env.ENFORCEMENT_CHECK_API_KEY?.trim() || "",
    timeoutMs:
      Number.isFinite(rawTimeout) && rawTimeout > 0
        ? rawTimeout
        : DEFAULT_TIMEOUT_MS,
  };
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
  if (config.mode !== "shadow" || !config.apiKey) {
    return { decision: "ALLOW", status: "skipped" };
  }

  const sourceIp = requestSourceIp(requestHeaders);
  if (!sourceIp) return { decision: "ALLOW", status: "skipped" };

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
    if (!response.ok) return { decision: "ALLOW", status: "degraded" };

    let body: unknown;
    try {
      body = await response.json();
    } catch {
      return { decision: "ALLOW", status: "degraded" };
    }
    return exactAllowResponse(body)
      ? { decision: "ALLOW", status: "checked" }
      : { decision: "ALLOW", status: "degraded" };
  } catch {
    return { decision: "ALLOW", status: "degraded" };
  } finally {
    clearTimeout(timeout);
  }
}

export async function checkRecordSearchShadowEnforcementFromRuntime(): Promise<ShadowCheckResult> {
  const { headers } = await import("next/headers");
  return checkRecordSearchShadowEnforcement({
    requestHeaders: await headers(),
    config: runtimeConfig(),
  });
}
