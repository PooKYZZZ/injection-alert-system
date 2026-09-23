import { NextResponse } from "next/server";
import type { EnforcementCheckResult } from "./enforcement-check";

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
