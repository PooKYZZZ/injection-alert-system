import { NextRequest, NextResponse } from "next/server";

import {
  checkEnforcementForHeaders,
  enforcementRuntimeConfig,
} from "./lib/enforcement-check-runtime";
import { applicationBlockAppliedLogEvent } from "./lib/enforcement-check";
import { enforcementPageResponse } from "./lib/enforcement-boundary";
import { ingestAndEnforcePortalRequest } from "./lib/portal-waf-ingest";

const DECISION_HEADER = "x-cybertrace-enforcement-decision";
const PROTECTED_GET_SCOPES = {
  "/records/search": { scope: "RECORD_SEARCH", input: "query" },
  "/transactions/status": { scope: "TRACK_STATUS", input: "ref" },
} as const;

function continueWithDecision(
  request: NextRequest,
  decision: "ALLOW" | "CHALLENGE",
): NextResponse {
  const requestHeaders = new Headers(request.headers);
  // Overwrite any caller-supplied value: this is an internal handoff to the
  // Server Component, never an input to the policy engine.
  requestHeaders.set(DECISION_HEADER, decision);
  return NextResponse.next({ request: { headers: requestHeaders } });
}

function inspectionUnavailableResponse(): NextResponse {
  return NextResponse.json(
    { error: "security_inspection_unavailable" },
    {
      status: 503,
      headers: { "cache-control": "no-store", "retry-after": "5" },
    },
  );
}

async function isChallengeResponse(response: NextResponse): Promise<boolean> {
  if (response.status !== 403) return false;
  try {
    const body: unknown = await response.clone().json();
    return (
      typeof body === "object" &&
      body !== null &&
      "error" in body &&
      body.error === "verification_required"
    );
  } catch {
    return false;
  }
}

export async function middleware(request: NextRequest): Promise<NextResponse> {
  if (request.method !== "GET") return NextResponse.next();
  const route =
    PROTECTED_GET_SCOPES[
      request.nextUrl.pathname as keyof typeof PROTECTED_GET_SCOPES
    ];
  if (!route) return NextResponse.next();

  try {
    const input = request.nextUrl.searchParams.get(route.input);
    if (input !== null && input.length > 0) {
      const enforcementResponse = await ingestAndEnforcePortalRequest({
        request,
        requestPath: request.nextUrl.pathname,
        scope: route.scope,
        fields: { [route.input]: input },
      });

      if (enforcementResponse) {
        if (await isChallengeResponse(enforcementResponse)) {
          return continueWithDecision(request, "CHALLENGE");
        }
        if (enforcementResponse.status === 429) {
          const retryAfterSeconds = Number(
            enforcementResponse.headers.get("retry-after"),
          );
          if (Number.isInteger(retryAfterSeconds) && retryAfterSeconds >= 1) {
            console.warn(
              JSON.stringify({
                event: "enforcement.application_throttle_applied",
                scope: route.scope,
                actual_decision: "THROTTLE",
                status_code: 429,
                retry_after_seconds: retryAfterSeconds,
              }),
            );
            return (
              enforcementPageResponse({
                decision: "THROTTLE",
                status: "checked",
                retryAfterSeconds,
              }) ?? enforcementResponse
            );
          }
        }
        if (enforcementResponse.status === 403) {
          console.info(
            JSON.stringify({
              ...applicationBlockAppliedLogEvent(),
              status_code: 403,
            }),
          );
          return (
            enforcementPageResponse({ decision: "BLOCK", status: "checked" }) ??
            enforcementResponse
          );
        }
        return enforcementResponse;
      }

      return continueWithDecision(request, "ALLOW");
    }

    // An empty form has no model input, but an existing source-scoped
    // restriction still applies before the page performs protected work.
    const enforcement = await checkEnforcementForHeaders(
      route.scope,
      request.headers,
    );
    if (
      enforcementRuntimeConfig().mode === "enforce" &&
      enforcement.status !== "checked"
    ) {
      return inspectionUnavailableResponse();
    }
    const response = enforcementPageResponse(enforcement);
    if (response) {
      if (enforcement.decision === "BLOCK") {
        console.info(
          JSON.stringify({
            ...applicationBlockAppliedLogEvent(),
            status_code: 403,
          }),
        );
      }
      return response;
    }
    return continueWithDecision(
      request,
      enforcement.decision === "CHALLENGE" ? "CHALLENGE" : "ALLOW",
    );
  } catch {
    console.error(
      JSON.stringify({
        event: "waf.protected_get_inspection_failed",
        request_path: request.nextUrl.pathname,
      }),
    );
    if (enforcementRuntimeConfig().mode === "enforce") {
      return inspectionUnavailableResponse();
    }
    return continueWithDecision(request, "ALLOW");
  }
}

export const config = {
  matcher: ["/records/search", "/transactions/status"],
  runtime: "nodejs",
};
