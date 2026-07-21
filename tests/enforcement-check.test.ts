import assert from "node:assert/strict";
import test from "node:test";
import {
  checkRecordSearchShadowEnforcement,
  checkRecordSearchEnforcement,
  verifyRecordSearchEnforcementChallenge,
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

  assert.deepEqual(result, {
    decision: "ALLOW",
    status: "skipped",
    reason: "MODE_OFF",
  });
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

  assert.deepEqual(result, {
    decision: "ALLOW",
    status: "degraded",
    reason: "HTTP_ERROR",
  });
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

  assert.deepEqual(result, {
    decision: "ALLOW",
    status: "degraded",
    reason: "INVALID_RESPONSE",
  });
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

  assert.deepEqual(result, {
    decision: "ALLOW",
    status: "degraded",
    reason: "TIMEOUT_OR_NETWORK",
  });
});

test("reports shadow misconfiguration as degraded rather than skipped", async () => {
  const result = await checkRecordSearchShadowEnforcement({
    requestHeaders: new Headers({ "x-forwarded-for": "203.0.113.10" }),
    config: { ...config, apiKey: "" },
    fetchImpl: async () => {
      throw new Error("must not call backend");
    },
  });

  assert.deepEqual(result, {
    decision: "ALLOW",
    status: "degraded",
    reason: "CONFIG_INVALID",
  });
});

test("parses active challenge and throttle decisions", async () => {
  const enforceConfig = {
    ...config,
    mode: "enforce" as const,
    allowUnverifiedSourceForTests: true,
  };
  const challenge = await checkRecordSearchEnforcement({
    requestHeaders: new Headers({ "cf-connecting-ip": "203.0.113.10" }),
    config: enforceConfig,
    fetchImpl: async () =>
      new Response(JSON.stringify({ decision: "CHALLENGE", enforcement_tier: "LOW" }), {
        status: 200,
      }),
  });
  const throttle = await checkRecordSearchEnforcement({
    requestHeaders: new Headers({ "cf-connecting-ip": "203.0.113.10" }),
    config: enforceConfig,
    fetchImpl: async () =>
      new Response(JSON.stringify({ decision: "THROTTLE", retry_after_seconds: 4 }), {
        status: 200,
      }),
  });

  assert.deepEqual(challenge, {
    decision: "CHALLENGE",
    status: "checked",
    tier: "LOW",
  });
  assert.deepEqual(throttle, {
    decision: "THROTTLE",
    status: "checked",
    retryAfterSeconds: 4,
  });
});

test("active mode does not fall back to arbitrary forwarded headers", async () => {
  const result = await checkRecordSearchEnforcement({
    requestHeaders: new Headers({ "x-forwarded-for": "203.0.113.10" }),
    config: { ...config, mode: "enforce" },
    fetchImpl: async () => {
      throw new Error("must not call backend");
    },
  });

  assert.deepEqual(result, {
    decision: "ALLOW",
    status: "skipped",
    reason: "NO_SOURCE_IP",
  });
});

test("active malformed decisions fail open", async () => {
  const result = await checkRecordSearchEnforcement({
    requestHeaders: new Headers({ "cf-connecting-ip": "203.0.113.10" }),
    config: { ...config, mode: "enforce" },
    fetchImpl: async () =>
      new Response(JSON.stringify({ decision: "DENY" }), { status: 200 }),
  });

  assert.deepEqual(result, {
    decision: "ALLOW",
    status: "degraded",
    reason: "INVALID_RESPONSE",
  });
});

test("challenge verification stays server-side and accepts only verified status", async () => {
  let requestBody = "";
  const result = await verifyRecordSearchEnforcementChallenge({
    requestHeaders: new Headers({ "cf-connecting-ip": "203.0.113.10" }),
    config: {
      ...config,
      mode: "enforce",
      challengeEndpoint: "http://backend:8000/api/internal/enforcement/challenge",
    },
    token: "turnstile-token",
    fetchImpl: async (_input, init) => {
      requestBody = String(init?.body);
      return new Response(JSON.stringify({ verified: true, status: "VERIFIED" }), {
        status: 200,
      });
    },
  });

  assert.deepEqual(result, { verified: true, status: "VERIFIED" });
  assert.match(requestBody, /turnstile-token/);
  assert.match(requestBody, /203\.0\.113\.10/);
});

test("challenge verification does not turn provider failure into a bypass", async () => {
  const result = await verifyRecordSearchEnforcementChallenge({
    requestHeaders: new Headers({ "cf-connecting-ip": "203.0.113.10" }),
    config: {
      ...config,
      mode: "enforce",
      challengeEndpoint: "http://backend:8000/api/internal/enforcement/challenge",
    },
    token: "turnstile-token",
    fetchImpl: async () =>
      new Response(JSON.stringify({ verified: false, status: "UNAVAILABLE" }), {
        status: 200,
      }),
  });

  assert.deepEqual(result, { verified: false, status: "UNAVAILABLE" });
});
