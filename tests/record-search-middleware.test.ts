import assert from "node:assert/strict";
import test from "node:test";
import { NextRequest } from "next/server";

import { middleware } from "../middleware";

test("Search middleware overwrites caller policy headers before allowing a query", async () => {
  const previousMode = process.env.ENFORCEMENT_MODE;
  const previousIngestKey = process.env.WAF_INGEST_API_KEY;
  const previousEvidenceKey = process.env.WAF_AUDIT_EVIDENCE_KEY;
  process.env.ENFORCEMENT_MODE = "off";
  process.env.WAF_INGEST_API_KEY = "";
  process.env.WAF_AUDIT_EVIDENCE_KEY = "";

  try {
    const request = new NextRequest(
      "https://target.cybertracesystems.com/records/search?query=Maple",
      {
        headers: {
          "x-cybertrace-enforcement-decision": "BLOCK",
        },
      },
    );
    const response = await middleware(request);

    assert.equal(response.headers.get("x-middleware-next"), "1");
    assert.equal(
      response.headers.get("x-middleware-request-x-cybertrace-enforcement-decision"),
      "ALLOW",
    );
  } finally {
    if (previousMode === undefined) delete process.env.ENFORCEMENT_MODE;
    else process.env.ENFORCEMENT_MODE = previousMode;
    if (previousIngestKey === undefined) delete process.env.WAF_INGEST_API_KEY;
    else process.env.WAF_INGEST_API_KEY = previousIngestKey;
    if (previousEvidenceKey === undefined) delete process.env.WAF_AUDIT_EVIDENCE_KEY;
    else process.env.WAF_AUDIT_EVIDENCE_KEY = previousEvidenceKey;
  }
});

test("Track Status middleware overwrites caller policy headers", async () => {
  const previousMode = process.env.ENFORCEMENT_MODE;
  const previousIngestKey = process.env.WAF_INGEST_API_KEY;
  const previousEvidenceKey = process.env.WAF_AUDIT_EVIDENCE_KEY;
  process.env.ENFORCEMENT_MODE = "off";
  process.env.WAF_INGEST_API_KEY = "";
  process.env.WAF_AUDIT_EVIDENCE_KEY = "";

  try {
    const request = new NextRequest(
      "https://target.cybertracesystems.com/transactions/status?ref=TXN-100201",
      {
        headers: {
          "x-cybertrace-enforcement-decision": "BLOCK",
        },
      },
    );
    const response = await middleware(request);

    assert.equal(response.headers.get("x-middleware-next"), "1");
    assert.equal(
      response.headers.get("x-middleware-request-x-cybertrace-enforcement-decision"),
      "ALLOW",
    );
  } finally {
    if (previousMode === undefined) delete process.env.ENFORCEMENT_MODE;
    else process.env.ENFORCEMENT_MODE = previousMode;
    if (previousIngestKey === undefined) delete process.env.WAF_INGEST_API_KEY;
    else process.env.WAF_INGEST_API_KEY = previousIngestKey;
    if (previousEvidenceKey === undefined) delete process.env.WAF_AUDIT_EVIDENCE_KEY;
    else process.env.WAF_AUDIT_EVIDENCE_KEY = previousEvidenceKey;
  }
});

test("empty protected GETs fail closed with 503 when ENFORCE checks are unavailable", async () => {
  const previousMode = process.env.ENFORCEMENT_MODE;
  const previousAppEnv = process.env.APP_ENV;
  const previousApiKey = process.env.ENFORCEMENT_CHECK_API_KEY;
  process.env.ENFORCEMENT_MODE = "enforce";
  process.env.APP_ENV = "testing";
  process.env.ENFORCEMENT_CHECK_API_KEY = "";

  try {
    for (const path of [
      "/records/search?query=",
      "/transactions/status?ref=",
    ]) {
      const response = await middleware(
        new NextRequest(`https://target.cybertracesystems.com${path}`),
      );

      assert.equal(response.status, 503);
      assert.equal(response.headers.get("cache-control"), "no-store");
      assert.equal(response.headers.get("retry-after"), "5");
    }
  } finally {
    if (previousMode === undefined) delete process.env.ENFORCEMENT_MODE;
    else process.env.ENFORCEMENT_MODE = previousMode;
    if (previousAppEnv === undefined) delete process.env.APP_ENV;
    else process.env.APP_ENV = previousAppEnv;
    if (previousApiKey === undefined) delete process.env.ENFORCEMENT_CHECK_API_KEY;
    else process.env.ENFORCEMENT_CHECK_API_KEY = previousApiKey;
  }
});
