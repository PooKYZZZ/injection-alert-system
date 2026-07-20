import { isIP } from "node:net";

export type ShadowEnforcementConfig = {
  mode: "off" | "shadow";
  endpoint: string;
  apiKey: string;
  timeoutMs: number;
};

export type ShadowCheckResult =
  | { decision: "ALLOW"; status: "skipped"; reason: "MODE_OFF" | "NO_SOURCE_IP" }
  | { decision: "ALLOW"; status: "checked" }
  | {
      decision: "ALLOW";
      status: "degraded";
      reason:
        | "CONFIG_INVALID"
        | "HTTP_ERROR"
        | "TIMEOUT_OR_NETWORK"
        | "INVALID_RESPONSE";
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

export async function checkRecordSearchShadowEnforcement({
  requestHeaders,
  config,
  fetchImpl = fetch,
}: {
  requestHeaders: Pick<Headers, "get">;
  config: ShadowEnforcementConfig;
  fetchImpl?: FetchLike;
}): Promise<ShadowCheckResult> {
  if (config.mode !== "shadow") {
    return { decision: "ALLOW", status: "skipped", reason: "MODE_OFF" };
  }

  const sourceIp = requestSourceIp(requestHeaders);
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
      return {
        decision: "ALLOW",
        status: "degraded",
        reason: "INVALID_RESPONSE",
      };
    }
    return exactAllowResponse(body)
      ? { decision: "ALLOW", status: "checked" }
      : {
          decision: "ALLOW",
          status: "degraded",
          reason: "INVALID_RESPONSE",
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
