import { NextRequest } from "next/server";

export interface DemoRequestMetadata {
  traceId: string;
  requestId: string;
  ipAddress: string;
  userAgent: string;
}

/**
 * Extracts optional cybersecurity auditing headers and telemetry values.
 * 
 * NOTE ON INTEGRATION ARCHITECTURE:
 * 1. These IDs and indicators are for local sandbox/demo correlation only.
 * 2. External inspection and rule matching can later live on a proxy layer that
 *    intercepts all incoming public requests before they reach this Next.js app.
 * 3. The analytics system should ingest proxy-generated event logs, not direct app internals.
 * 4. This helper is utilized here so the mock portal can display a "Demo Correlation Panel"
 *    and keep track of simulation traces like `x-demo-trace-id` inside our UI.
 */
export function getDemoRequestMetadata(request: NextRequest): DemoRequestMetadata {
  const traceId = request.headers.get("x-demo-trace-id") || "";
  const requestId = request.headers.get("x-request-id") || "";
  const ipAddress = request.headers.get("x-forwarded-for")?.split(",")[0] || "127.0.0.1";
  const userAgent = request.headers.get("user-agent") || "Mozilla/5.0 (Sandbox/Auditor)";

  return {
    traceId,
    requestId,
    ipAddress,
    userAgent,
  };
}

/**
 * Static client-safe helper for optional trace parameters.
 */
export function extractClientTraceId(searchParams: Record<string, string | string[] | undefined>): string {
  if (!searchParams) return "";
  const traceId = searchParams.traceId || searchParams["x-demo-trace-id"];
  if (Array.isArray(traceId)) return traceId[0] || "";
  return traceId || "";
}
