import assert from "node:assert/strict";
import test from "node:test";
import { NextRequest } from "next/server";

import {
  ingestAndEnforcePortalPost,
  ingestAndEnforcePortalRequest,
} from "../lib/portal-waf-ingest";
import type { EnforcementCheckResult, EnforcementScope } from "../lib/enforcement-check";

const config = {
  mode: "enforce" as const,
  sourceTrustMode: "cloudflare_verified" as const,
  endpoint: "http://backend:8000/api/internal/waf-events",
  ingestApiKey: "test-ingest-key",
  auditEvidenceKey: "test-audit-evidence-key",
  timeoutMs: 1000,
};

const normalPrediction = {
  prediction: "Normal",
  confidence: 0.91,
  confidence_level: "HIGH",
  action_taken: "ALLOWED",
};

function request(
  path: string,
  headers: Record<string, string> = { "cf-connecting-ip": "203.0.113.25" },
) {
  return new NextRequest(`https://target.cybertracesystems.com${path}`, {
    method: "POST",
    headers: {
      "x-cybertrace-cloudflare-peer-verified": "1",
      ...headers,
    },
  });
}

function getRequest(
  path: string,
  headers: Record<string, string> = { "cf-connecting-ip": "203.0.113.25" },
) {
  return new NextRequest(`https://target.cybertracesystems.com${path}`, {
    headers: {
      "x-cybertrace-cloudflare-peer-verified": "1",
      ...headers,
    },
  });
}

function response(body: unknown = normalPrediction, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

test("ingests only allowlisted support text with verified Cloudflare source", async () => {
  let sentPayload: Record<string, unknown> | undefined;
  let sentHeaders: Headers | undefined;
  const sequence: string[] = [];
  const result = await ingestAndEnforcePortalPost(
    {
      request: request("/support/submit", {
        "cf-connecting-ip": "203.0.113.25",
        "x-forwarded-for": "198.51.100.9",
      }),
      requestPath: "/support/submit",
      scope: "SUPPORT_SUBMIT",
      fields: {
        subject: "Records question",
        category: "General Inquiry",
        message: "Please check the title.",
        email: "private@example.test",
        referenceNo: "REC-PRIVATE-1",
        password: "must-not-be-sent",
      },
    },
    {
      config,
      transactionId: "portal-test-1",
      timestamp: "2026-09-24T10:00:00.000Z",
      fetchImpl: async (_input, init) => {
        sequence.push("ingest");
        sentPayload = JSON.parse(String(init?.body)) as Record<string, unknown>;
        sentHeaders = new Headers(init?.headers);
        return response();
      },
      checkEnforcement: async (scope: EnforcementScope, headers: Headers) => {
        sequence.push("enforcement");
        assert.equal(scope, "SUPPORT_SUBMIT");
        assert.equal(headers.get("cf-connecting-ip"), "203.0.113.25");
        return { decision: "ALLOW", status: "checked" };
      },
    },
  );

  assert.equal(result, null);
  assert.deepEqual(sequence, ["ingest", "enforcement"]);
  assert.ok(sentPayload);
  assert.equal(sentPayload.ingest_source, "portal_route_bridge");
  assert.equal(sentPayload.source_ip, "203.0.113.25");
  assert.equal(sentPayload.source_provenance, "CLOUDFLARE_CONNECTING_IP");
  assert.equal(sentPayload.cf_connecting_ip_matches_client_ip, true);
  assert.equal(sentPayload.crs_score, 0);
  assert.deepEqual(sentPayload.crs_rule_ids, ["no-crs-match"]);
  assert.equal(sentPayload.query_string, undefined);
  assert.equal(sentPayload.request_headers, undefined);
  const body = new URLSearchParams(String(sentPayload.sanitized_body));
  assert.equal(body.get("subject"), "Records question");
  assert.equal(body.get("category"), "General Inquiry");
  assert.equal(body.get("message"), "Please check the title.");
  assert.equal(body.has("email"), false);
  assert.equal(body.has("referenceNo"), false);
  assert.equal(body.has("password"), false);
  assert.equal(sentHeaders?.get("authorization"), "Bearer test-ingest-key");
  assert.equal(sentHeaders?.get("X-CyberTrace-WAF-Audit"), "portal_route");
  assert.equal(
    sentHeaders?.get("X-CyberTrace-WAF-Audit-Key"),
    "test-audit-evidence-key",
  );
});

test("inspects the current Search Records GET query before page work", async () => {
  const query = "' OR 1=1 --";
  let sentPayload: Record<string, unknown> | undefined;
  const sequence: string[] = [];
  const result = await ingestAndEnforcePortalRequest(
    {
      request: getRequest("/records/search?query=%27+OR+1%3D1+--", {
        "cf-connecting-ip": "203.0.113.25",
        "x-cybertrace-edge-request-id": "0123456789abcdef0123456789abcdef",
      }),
      requestPath: "/records/search",
      scope: "RECORD_SEARCH",
      fields: { query },
    },
    {
      config,
      fetchImpl: async (_input, init) => {
        sequence.push("inference");
        sentPayload = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return response();
      },
      checkEnforcement: async (scope, headers) => {
        sequence.push("policy-check");
        assert.equal(scope, "RECORD_SEARCH");
        assert.equal(headers.get("cf-connecting-ip"), "203.0.113.25");
        return { decision: "ALLOW", status: "checked" };
      },
    },
  );

  assert.equal(result, null);
  assert.deepEqual(sequence, ["inference", "policy-check"]);
  assert.equal(sentPayload?.request_method, "GET");
  assert.equal(sentPayload?.request_path, "/records/search");
  assert.equal(sentPayload?.source_ip, "203.0.113.25");
  assert.equal(sentPayload?.source_provenance, "CLOUDFLARE_CONNECTING_IP");
  assert.equal(sentPayload?.cf_connecting_ip_matches_client_ip, true);
  assert.equal(sentPayload?.query_string, undefined);
  assert.equal(sentPayload?.request_headers, undefined);
  assert.equal(sentPayload?.crs_score, 0);
  assert.deepEqual(sentPayload?.crs_rule_ids, ["no-crs-match"]);
  assert.equal(
    new URLSearchParams(String(sentPayload?.sanitized_body)).get("query"),
    query,
  );
});

test("inspects the Track Status reference before protected database reads", async () => {
  const reference = "TXN-100201";
  let sentPayload: Record<string, unknown> | undefined;
  const result = await ingestAndEnforcePortalRequest(
    {
      request: getRequest("/transactions/status?ref=TXN-100201", {
        "cf-connecting-ip": "203.0.113.25",
        "x-cybertrace-edge-request-id": "1123456789abcdef0123456789abcdef",
      }),
      requestPath: "/transactions/status",
      scope: "TRACK_STATUS",
      fields: { ref: reference },
    },
    {
      config,
      fetchImpl: async (_input, init) => {
        sentPayload = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return response();
      },
      checkEnforcement: async (scope) => {
        assert.equal(scope, "TRACK_STATUS");
        return { decision: "ALLOW", status: "checked" };
      },
    },
  );

  assert.equal(result, null);
  assert.equal(sentPayload?.request_method, "GET");
  assert.equal(sentPayload?.request_path, "/transactions/status");
  assert.equal(sentPayload?.query_string, undefined);
  assert.equal(
    new URLSearchParams(String(sentPayload?.sanitized_body)).get("ref"),
    reference,
  );
});

test("Search Records returns actual policy 429/403 before protected work", async () => {
  for (const [decision, expectedStatus] of [
    ["THROTTLE", 429],
    ["BLOCK", 403],
  ] as const) {
    const result = await ingestAndEnforcePortalRequest(
      {
        request: getRequest("/records/search?query=policy-test"),
        requestPath: "/records/search",
        scope: "RECORD_SEARCH",
        fields: { query: "policy-test" },
      },
      {
        config,
        fetchImpl: async () => response(),
        checkEnforcement: async () =>
          decision === "THROTTLE"
            ? {
                decision,
                status: "checked",
                retryAfterSeconds: 30,
                decisionReason: "REPEATED_SUSPICIOUS_ACTIVITY",
              }
            : { decision, status: "checked", decisionReason: "STRONG_CRS_EVIDENCE" },
      },
    );

    assert.ok(result);
    assert.equal(result.status, expectedStatus);
    if (expectedStatus === 429) {
      assert.equal(result.headers.get("retry-after"), "30");
    }
  }
});

test("does not permit GET inspection on routes outside the allowlist", async () => {
  let ingestionCalled = false;
  const result = await ingestAndEnforcePortalRequest(
    {
      request: getRequest("/support/submit"),
      requestPath: "/support/submit",
      scope: "SUPPORT_SUBMIT",
      fields: { message: "not a GET route" },
    },
    {
      config,
      fetchImpl: async () => {
        ingestionCalled = true;
        return response();
      },
      checkEnforcement: async () => ({ decision: "ALLOW", status: "checked" }),
    },
  );

  assert.equal(ingestionCalled, false);
  assert.ok(result);
  assert.equal(result.status, 500);
});

test("uses the reverse-proxy request id for portal-ingest correlation", async () => {
  const edgeRequestId = "0123456789abcdef0123456789abcdef";
  let sentPayload: Record<string, unknown> | undefined;

  await ingestAndEnforcePortalPost(
    {
      request: request("/comments/submit", {
        "cf-connecting-ip": "203.0.113.25",
        "x-cybertrace-edge-request-id": edgeRequestId,
      }),
      requestPath: "/comments/submit",
      scope: "COMMENTS_SUBMIT",
      fields: { message: "Synthetic correlation probe" },
    },
    {
      config,
      fetchImpl: async (_input, init) => {
        sentPayload = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return response();
      },
      checkEnforcement: async () => ({ decision: "ALLOW", status: "checked" }),
    },
  );

  assert.equal(sentPayload?.transaction_id, edgeRequestId);
});

test("does not accept a caller-controlled non-proxy id as the event id", async () => {
  let sentPayload: Record<string, unknown> | undefined;

  await ingestAndEnforcePortalPost(
    {
      request: request("/comments/submit", {
        "cf-connecting-ip": "203.0.113.25",
        "x-cybertrace-edge-request-id": "attacker-controlled-id",
      }),
      requestPath: "/comments/submit",
      scope: "COMMENTS_SUBMIT",
      fields: { message: "Synthetic correlation probe" },
    },
    {
      config,
      fetchImpl: async (_input, init) => {
        sentPayload = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return response();
      },
      checkEnforcement: async () => ({ decision: "ALLOW", status: "checked" }),
    },
  );

  assert.match(String(sentPayload?.transaction_id), /^[0-9a-f-]{36}$/i);
  assert.notEqual(sentPayload?.transaction_id, "attacker-controlled-id");
});

test("applies the post-inference application block response", async () => {
  const sequence: string[] = [];
  const result = await ingestAndEnforcePortalPost(
    {
      request: request("/comments/submit"),
      requestPath: "/comments/submit",
      scope: "COMMENTS_SUBMIT",
      fields: { message: "saved harmless marker" },
    },
    {
      config,
      fetchImpl: async () => {
        sequence.push("inference");
        return response({
          prediction: "Code Injection",
          confidence: 0.95,
          confidence_level: "CRITICAL",
          action_taken: "BLOCKED",
        });
      },
      checkEnforcement: async () => {
        sequence.push("policy-check");
        return {
          decision: "BLOCK",
          status: "checked",
          decisionReason: "STRONG_CRS_EVIDENCE",
        };
      },
    },
  );

  assert.deepEqual(sequence, ["inference", "policy-check"]);
  assert.ok(result);
  assert.equal(result.status, 403);
  assert.deepEqual(await result.json(), { error: "request_blocked" });
});

test("fails closed when only untrusted X-Forwarded-For is present", async () => {
  let sentPayload: Record<string, unknown> | undefined;
  let enforcementResult: EnforcementCheckResult | undefined;
  const result = await ingestAndEnforcePortalPost(
    {
      request: request("/login/submit", {
        "x-forwarded-for": "198.51.100.77",
        "x-cybertrace-cloudflare-peer-verified": "0",
      }),
      requestPath: "/login/submit",
      scope: "LOGIN_SUBMIT",
      fields: { username: "qa-user", password: "must-not-be-sent" },
    },
    {
      config,
      fetchImpl: async (_input, init) => {
        sentPayload = JSON.parse(String(init?.body)) as Record<string, unknown>;
        return response();
      },
      checkEnforcement: async () => {
        enforcementResult = {
          decision: "ALLOW",
          status: "skipped",
          reason: "NO_SOURCE_IP",
        };
        return enforcementResult;
      },
    },
  );

  assert.equal(sentPayload?.source_ip, null);
  assert.equal(sentPayload?.source_provenance, "DIRECT_REMOTE_ADDR");
  assert.equal(sentPayload?.cf_connecting_ip_matches_client_ip, null);
  assert.equal(
    new URLSearchParams(String(sentPayload?.sanitized_body)).has("password"),
    false,
  );
  assert.equal(enforcementResult?.status, "skipped");
  assert.ok(result);
  assert.equal(result.status, 503);
});

test("fails closed when active inference is unavailable", async () => {
  let enforcementCalled = false;
  const result = await ingestAndEnforcePortalPost(
    {
      request: request("/appointments/submit"),
      requestPath: "/appointments/submit",
      scope: "APPOINTMENT_SUBMIT",
      fields: { branch: "Pasig", serviceType: "Records review", notes: "QA" },
    },
    {
      config,
      fetchImpl: async () => {
        throw new Error("simulated network outage");
      },
      checkEnforcement: async () => {
        enforcementCalled = true;
        return { decision: "ALLOW", status: "checked" };
      },
    },
  );

  assert.equal(enforcementCalled, false);
  assert.ok(result);
  assert.equal(result.status, 503);
  assert.deepEqual(await result.json(), {
    error: "security_inspection_unavailable",
  });
});

test("invalid route-scope pairing is rejected before making a request", async () => {
  let fetchCalled = false;
  const result = await ingestAndEnforcePortalPost(
    {
      request: request("/comments/submit"),
      requestPath: "/support/submit",
      scope: "COMMENTS_SUBMIT",
      fields: { message: "marker" },
    },
    {
      config,
      fetchImpl: async () => {
        fetchCalled = true;
        return response();
      },
    },
  );

  assert.equal(fetchCalled, false);
  assert.ok(result);
  assert.equal(result.status, 500);
});
