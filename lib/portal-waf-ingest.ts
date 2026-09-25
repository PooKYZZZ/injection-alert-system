import "server-only";

import { randomUUID } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";
import { z } from "zod";
import {
  enforcementRuntimeConfig,
  checkEnforcementForHeaders,
} from "./enforcement-check-runtime";
import { enforcementRouteResponse } from "./enforcement-boundary";
import {
  requestSourceIp,
  type EnforcementCheckResult,
  type EnforcementScope,
} from "./enforcement-check";

const DEFAULT_INGEST_URL = "http://backend:8000/api/internal/waf-events";
const MAX_BODY_BYTES = 1024;
const EDGE_REQUEST_ID_HEADER = "x-cybertrace-edge-request-id";
const EDGE_REQUEST_ID_PATTERN = /^[a-f0-9]{32}$/i;

const SAFE_FIELDS_BY_SCOPE: Partial<Record<EnforcementScope, readonly string[]>> = {
  SUPPORT_SUBMIT: ["subject", "category", "message"],
  APPOINTMENT_SUBMIT: ["branch", "serviceType", "notes"],
  COMMENTS_SUBMIT: ["message"],
  LOGIN_SUBMIT: ["username"],
  REQUEST_COPY_SUBMIT: ["purpose", "deliveryOption", "remarks"],
};

const ingestResponseSchema = z.object({
  alert_id: z.number().int().positive().nullable().optional(),
  prediction: z.enum(["Normal", "SQL Injection", "Code Injection", "Other Attacks"]),
  confidence: z.number().min(0).max(1),
  confidence_level: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
  action_taken: z.enum(["ALLOWED", "THROTTLED", "BLOCKED"]).nullable().optional(),
  model_version: z.string().nullable().optional(),
});

type PortalIngestConfig = {
  mode: "off" | "shadow" | "enforce";
  sourceTrustMode: "unverified" | "cloudflare_verified";
  endpoint: string;
  ingestApiKey: string;
  auditEvidenceKey: string;
  timeoutMs: number;
};

type IngestAndCheckDependencies = {
  config?: PortalIngestConfig;
  fetchImpl?: typeof fetch;
  checkEnforcement?: (
    scope: EnforcementScope,
    headers: Headers,
  ) => Promise<EnforcementCheckResult>;
  transactionId?: string;
  timestamp?: string;
};

function runtimeIngestConfig(): PortalIngestConfig {
  const enforcement = enforcementRuntimeConfig();
  const timeout = Number(process.env.WAF_INGEST_TIMEOUT_MS);
  return {
    mode: enforcement.mode,
    sourceTrustMode: enforcement.sourceTrustMode ?? "unverified",
    endpoint: process.env.WAF_INGEST_URL?.trim() || DEFAULT_INGEST_URL,
    ingestApiKey: process.env.WAF_INGEST_API_KEY?.trim() || "",
    auditEvidenceKey: process.env.WAF_AUDIT_EVIDENCE_KEY?.trim() || "",
    timeoutMs: Number.isFinite(timeout) && timeout > 0 ? timeout : 10_000,
  };
}

function requestTransactionId(request: NextRequest): string {
  const edgeRequestId = request.headers.get(EDGE_REQUEST_ID_HEADER)?.trim() ?? "";
  return EDGE_REQUEST_ID_PATTERN.test(edgeRequestId) ? edgeRequestId : randomUUID();
}

function pathMatchesScope(path: string, scope: EnforcementScope): boolean {
  switch (scope) {
    case "SUPPORT_SUBMIT":
      return path === "/support/submit";
    case "APPOINTMENT_SUBMIT":
      return path === "/appointments/submit";
    case "COMMENTS_SUBMIT":
      return path === "/comments/submit";
    case "LOGIN_SUBMIT":
      return path === "/login/submit";
    case "REQUEST_COPY_SUBMIT":
      return /^\/records\/[A-Za-z0-9-]+\/request-copy\/submit$/.test(path);
    default:
      return false;
  }
}

function encodeAllowedFields(
  scope: EnforcementScope,
  fields: Record<string, string>,
): string | null {
  const allowedFields = SAFE_FIELDS_BY_SCOPE[scope];
  if (!allowedFields) return null;

  const params = new URLSearchParams();
  const encoder = new TextEncoder();
  for (const key of allowedFields) {
    const rawValue = fields[key];
    if (typeof rawValue !== "string" || rawValue.length === 0) continue;

    let value = rawValue.slice(0, 512);
    params.set(key, value);
    while (encoder.encode(params.toString()).byteLength > MAX_BODY_BYTES && value) {
      value = value.slice(0, Math.floor(value.length * 0.75));
      if (value) params.set(key, value);
      else params.delete(key);
    }
  }

  return params.toString() || null;
}

function unavailableResponse(
  transactionId: string,
  requestPath: string,
  statusCode?: number,
): NextResponse {
  console.warn(
    JSON.stringify({
      event: "waf.portal_post_inspection_unavailable",
      transaction_id: transactionId,
      request_path: requestPath,
      ...(statusCode ? { status_code: statusCode } : {}),
    }),
  );
  return NextResponse.json(
    { error: "security_inspection_unavailable" },
    {
      status: 503,
      headers: { "cache-control": "no-store", "retry-after": "5" },
    },
  );
}

/**
 * Send an allowlisted POST body to the internal model pipeline, then apply any
 * newly created route-scoped policy before the handler can write business data.
 * Request content is used transiently for inference; the backend stores only
 * request metadata and one-way model-input hashes for this source.
 */
export async function ingestAndEnforcePortalPost(
  input: {
    request: NextRequest;
    requestPath: string;
    scope: EnforcementScope;
    fields: Record<string, string>;
  },
  dependencies: IngestAndCheckDependencies = {},
): Promise<NextResponse | null> {
  const config = dependencies.config ?? runtimeIngestConfig();
  const transactionId =
    dependencies.transactionId ?? requestTransactionId(input.request);
  const timestamp = dependencies.timestamp ?? new Date().toISOString();
  const { request, requestPath, scope, fields } = input;

  if (request.method.toUpperCase() !== "POST" || !pathMatchesScope(requestPath, scope)) {
    console.error(
      JSON.stringify({
        event: "waf.portal_post_scope_mismatch",
        transaction_id: transactionId,
        request_path: requestPath,
        scope,
      }),
    );
    return NextResponse.json({ error: "security_inspection_unavailable" }, { status: 500 });
  }

  if (!config.ingestApiKey || !config.auditEvidenceKey) {
    if (config.mode !== "enforce") {
      console.warn(
        JSON.stringify({
          event: "waf.portal_post_ingest_not_configured",
          transaction_id: transactionId,
          request_path: requestPath,
        }),
      );
      return null;
    }
    return unavailableResponse(transactionId, requestPath);
  }

  const trustedSourceIp =
    config.sourceTrustMode === "cloudflare_verified"
      ? requestSourceIp(request.headers, { active: true })
      : null;
  const sanitizedBody = encodeAllowedFields(scope, fields);
  const payload = {
    ingest_source: "portal_route_bridge",
    transaction_id: transactionId,
    timestamp,
    source_ip: trustedSourceIp,
    source_provenance: trustedSourceIp
      ? "CLOUDFLARE_CONNECTING_IP"
      : "DIRECT_REMOTE_ADDR",
    cf_connecting_ip_matches_client_ip: trustedSourceIp ? true : null,
    request_method: "POST",
    request_path: requestPath,
    crs_score: 0,
    crs_rule_ids: ["no-crs-match"],
    sanitized_body: sanitizedBody,
  };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.timeoutMs);
  let response: Response;
  try {
    response = await (dependencies.fetchImpl ?? fetch)(config.endpoint, {
      method: "POST",
      headers: {
        authorization: `Bearer ${config.ingestApiKey}`,
        "content-type": "application/json",
        "X-CyberTrace-WAF-Audit": "portal_route",
        "X-CyberTrace-WAF-Audit-Key": config.auditEvidenceKey,
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
      cache: "no-store",
    });
  } catch {
    clearTimeout(timeout);
    if (config.mode === "enforce") {
      return unavailableResponse(transactionId, requestPath);
    }
    console.warn(
      JSON.stringify({
        event: "waf.portal_post_ingest_degraded",
        transaction_id: transactionId,
        request_path: requestPath,
      }),
    );
    return null;
  }
  clearTimeout(timeout);

  if (!response.ok) {
    if (config.mode === "enforce") {
      return unavailableResponse(transactionId, requestPath, response.status);
    }
    console.warn(
      JSON.stringify({
        event: "waf.portal_post_ingest_degraded",
        transaction_id: transactionId,
        request_path: requestPath,
        status_code: response.status,
      }),
    );
    return null;
  }

  let result: z.infer<typeof ingestResponseSchema>;
  try {
    result = ingestResponseSchema.parse(await response.json());
  } catch {
    if (config.mode === "enforce") {
      return unavailableResponse(transactionId, requestPath, response.status);
    }
    console.warn(
      JSON.stringify({
        event: "waf.portal_post_ingest_degraded",
        transaction_id: transactionId,
        request_path: requestPath,
        status_code: response.status,
      }),
    );
    return null;
  }

  console.info(
    JSON.stringify({
      event: "waf.portal_post_ingest_completed",
      transaction_id: transactionId,
      request_path: requestPath,
      prediction: result.prediction,
      confidence: result.confidence,
      confidence_tier: result.confidence_level,
      ml_action_recommendation: result.action_taken ?? null,
    }),
  );

  const enforcement = await (dependencies.checkEnforcement ?? checkEnforcementForHeaders)(
    scope,
    request.headers,
  );
  if (config.mode === "enforce" && enforcement.status !== "checked") {
    return unavailableResponse(transactionId, requestPath);
  }
  return enforcementRouteResponse(enforcement);
}
