import assert from "node:assert/strict";
import test from "node:test";
import {
  checkRecordSearchShadowEnforcement,
  requestSourceIp,
  type ShadowEnforcementConfig,
} from "../lib/enforcement-check";

const config: ShadowEnforcementConfig = {
  mode: "shadow",
  endpoint: "http://backend:8000/api/internal/enforcement/check",
  apiKey: "test-enforcement-key",
  timeoutMs: 50,
};

test("uses a valid Cloudflare source before forwarded headers", () => {
  const headers = new Headers({
    "cf-connecting-ip": "203.0.113.10",
    "x-forwarded-for": "198.51.100.20, 198.51.100.21",
  });

  assert.equal(requestSourceIp(headers), "203.0.113.10");
});

test("falls back to the first valid forwarded address", () => {
  const headers = new Headers({
    "cf-connecting-ip": "not-an-ip",
    "x-forwarded-for": "198.51.100.20, 198.51.100.21",
  });

  assert.equal(requestSourceIp(headers), "198.51.100.20");
});

test("skips malformed forwarded hops until the first valid address", () => {
  const headers = new Headers({
    "x-forwarded-for": "not-an-ip, 198.51.100.20",
  });

  assert.equal(requestSourceIp(headers), "198.51.100.20");
});

test("skips the check when shadow mode is off", async () => {
  let calls = 0;
  const result = await checkRecordSearchShadowEnforcement({
    requestHeaders: new Headers({ "x-forwarded-for": "203.0.113.10" }),
    config: { ...config, mode: "off" },
    fetchImpl: async () => {
      calls += 1;
      throw new Error("must not call backend");
    },
  });

  assert.deepEqual(result, { decision: "ALLOW", status: "skipped" });
  assert.equal(calls, 0);
});

test("accepts only the exact ALLOW response", async () => {
  const result = await checkRecordSearchShadowEnforcement({
    requestHeaders: new Headers({ "x-forwarded-for": "203.0.113.10" }),
    config,
    fetchImpl: async () =>
      new Response(JSON.stringify({ decision: "ALLOW" }), { status: 200 }),
  });

  assert.deepEqual(result, { decision: "ALLOW", status: "checked" });
});

test("fails open when the backend returns 503", async () => {
  const result = await checkRecordSearchShadowEnforcement({
    requestHeaders: new Headers({ "x-forwarded-for": "203.0.113.10" }),
    config,
    fetchImpl: async () => new Response("unavailable", { status: 503 }),
  });

  assert.deepEqual(result, { decision: "ALLOW", status: "degraded" });
});

test("fails open on malformed success responses and never retries", async () => {
  let calls = 0;
  const result = await checkRecordSearchShadowEnforcement({
    requestHeaders: new Headers({ "x-forwarded-for": "203.0.113.10" }),
    config,
    fetchImpl: async () => {
      calls += 1;
      return new Response(JSON.stringify({ decision: "DENY" }), { status: 200 });
    },
  });

  assert.deepEqual(result, { decision: "ALLOW", status: "degraded" });
  assert.equal(calls, 1);
});

test("fails open when the backend request times out", async () => {
  const result = await checkRecordSearchShadowEnforcement({
    requestHeaders: new Headers({ "x-forwarded-for": "203.0.113.10" }),
    config: { ...config, timeoutMs: 1 },
    fetchImpl: (_input, init) =>
      new Promise((_, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new Error("aborted")));
      }),
  });

  assert.deepEqual(result, { decision: "ALLOW", status: "degraded" });
});
