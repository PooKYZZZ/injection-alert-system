import assert from "node:assert/strict";
import test from "node:test";

import {
  enforcementPageResponse,
  enforcementRouteResponse,
} from "../lib/enforcement-boundary";

test("page throttle boundary returns HTTP 429 with Retry-After", async () => {
  const response = enforcementPageResponse({
    decision: "THROTTLE",
    status: "checked",
    retryAfterSeconds: 7,
    decisionReason: "STRONG_CRS_EVIDENCE",
  });

  assert.ok(response);
  assert.equal(response.status, 429);
  assert.equal(response.headers.get("retry-after"), "7");
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.match(await response.text(), /Search temporarily limited/);
});

test("page block boundary returns HTTP 403 without exposing policy details", async () => {
  const response = enforcementPageResponse({
    decision: "BLOCK",
    status: "checked",
    decisionReason: "STRONG_CRS_EVIDENCE",
  });

  assert.ok(response);
  assert.equal(response.status, 403);
  assert.equal(response.headers.get("retry-after"), null);
  const body = await response.text();
  assert.match(body, /Access temporarily blocked/);
  assert.doesNotMatch(body, /STRONG_CRS_EVIDENCE/);
});

test("page boundary leaves ALLOW and CHALLENGE rendering to the page", () => {
  assert.equal(
    enforcementPageResponse({ decision: "ALLOW", status: "checked" }),
    null,
  );
  assert.equal(
    enforcementPageResponse({ decision: "CHALLENGE", status: "checked", tier: "LOW" }),
    null,
  );
});

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
