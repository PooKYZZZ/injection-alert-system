import { NextResponse } from "next/server";
import type { EnforcementCheckResult } from "./enforcement-check";
import { httpErrorPageDocument } from "./http-error-page";

/**
 * Return a real HTTP response for page-level enforcement decisions.
 * Server Components can render a message but cannot set its HTTP status.
 */
export function enforcementPageResponse(
  result: EnforcementCheckResult,
): NextResponse | null {
  if (result.decision === "ALLOW" || result.decision === "CHALLENGE") {
    return null;
  }

  const throttled = result.decision === "THROTTLE";
  const status = throttled ? 429 : 403;
  const headers = new Headers({
    "cache-control": "no-store",
    "content-type": "text/html; charset=utf-8",
    "x-content-type-options": "nosniff",
  });
  if (throttled) {
    headers.set("retry-after", String(result.retryAfterSeconds));
  }

  return new NextResponse(
    httpErrorPageDocument(status, throttled ? result.retryAfterSeconds : undefined),
    { status, headers },
  );
}

/**
 * Convert an enforcement decision into a small, non-sensitive route response.
 * Call this before parsing a request body or touching Prisma.
 */
export function enforcementRouteResponse(
  result: EnforcementCheckResult,
): NextResponse | null {
  if (result.decision === "ALLOW") return null;

  if (result.decision === "THROTTLE") {
    return NextResponse.json(
      { error: "request_throttled" },
      {
        status: 429,
        headers: { "Retry-After": String(result.retryAfterSeconds) },
      },
    );
  }

  if (result.decision === "CHALLENGE") {
    return NextResponse.json(
      { error: "verification_required" },
      { status: 403 },
    );
  }

  return NextResponse.json({ error: "request_blocked" }, { status: 403 });
}
