import { NextResponse } from "next/server";
import type { EnforcementCheckResult } from "./enforcement-check";

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
  const title = throttled
    ? "Search temporarily limited"
    : "Access temporarily blocked";
  const message = throttled
    ? `Please wait ${result.retryAfterSeconds} seconds before trying again.`
    : "Access to this request is temporarily blocked.";
  const headers = new Headers({
    "cache-control": "no-store",
    "content-type": "text/html; charset=utf-8",
    "x-content-type-options": "nosniff",
  });
  if (throttled) {
    headers.set("retry-after", String(result.retryAfterSeconds));
  }

  return new NextResponse(
    `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title}</title></head><body><main><h1>${title}</h1><p>${message}</p><p><a href="/">Return to the demo portal</a></p></main></body></html>`,
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
