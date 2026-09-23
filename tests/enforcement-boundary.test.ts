import assert from "node:assert/strict";
import test from "node:test";

import { enforcementRouteResponse } from "../lib/enforcement-boundary";

test("route boundary returns a bounded 429 with Retry-After", async () => {
  const response = enforcementRouteResponse({
    decision: "THROTTLE",
    status: "checked",
    retryAfterSeconds: 7,
    decisionReason: "REPEATED_SUSPICIOUS_ACTIVITY",
  });

  assert.ok(response);
  assert.equal(response.status, 429);
  assert.equal(response.headers.get("retry-after"), "7");
  assert.deepEqual(await response.json(), { error: "request_throttled" });
});

test("route boundary blocks before business work for BLOCK and CHALLENGE", async () => {
  for (const decision of ["BLOCK", "CHALLENGE"] as const) {
    const response = enforcementRouteResponse(
      decision === "BLOCK"
        ? { decision, status: "checked" }
        : { decision, status: "checked", tier: "MEDIUM" },
    );
    assert.ok(response);
    assert.equal(response.status, 403);
  }
});

test("route boundary returns null for ALLOW", () => {
  assert.equal(
    enforcementRouteResponse({ decision: "ALLOW", status: "checked" }),
    null,
  );
});
