import assert from "node:assert/strict";
import test from "node:test";

import { WAF_ROUTES } from "../lib/routes";

test("WAF route inventory matches the portal's actual form and query entry points", () => {
  assert.ok(WAF_ROUTES.every((route) => route.enforcementScope));
  const search = WAF_ROUTES.find(
    (route) => route.path === "/records/search" && route.method === "GET",
  );
  assert.ok(search);
  assert.deepEqual(
    search.expectedParams.map((parameter) => parameter.name),
    ["query"],
  );
  assert.equal(search.safeExample, "/records/search?query=Maple");
  assert.equal(
    search.suspiciousExample,
    "/records/search?query=%27+OR+1%3D1+--",
  );

  assert.ok(
    WAF_ROUTES.some(
      (route) => route.path === "/login/submit" && route.method === "POST",
    ),
  );
  assert.ok(
    WAF_ROUTES.some(
      (route) =>
        route.path === "/records/[recordNo]/request-copy/submit" &&
        route.method === "POST" &&
        route.enforcementScope === "REQUEST_COPY_SUBMIT",
    ),
  );
});

test("all user-controlled WAF routes use the shared backend scope contract", () => {
  const expectedScopes = new Map([
    ["/records/search", "RECORD_SEARCH"],
    ["/records/[recordNo]", "RECORD_DETAIL"],
    ["/transactions/status", "TRACK_STATUS"],
    ["/support/submit", "SUPPORT_SUBMIT"],
    ["/appointments/submit", "APPOINTMENT_SUBMIT"],
    ["/comments/submit", "COMMENTS_SUBMIT"],
    ["/login/submit", "LOGIN_SUBMIT"],
    ["/records/[recordNo]/request-copy", "REQUEST_COPY_SUBMIT"],
    ["/records/[recordNo]/request-copy/submit", "REQUEST_COPY_SUBMIT"],
  ]);

  for (const [path, scope] of expectedScopes) {
    assert.equal(
      WAF_ROUTES.find((route) => route.path === path)?.enforcementScope,
      scope,
    );
  }
});

test("baseline form workflows retain their method, route, and payload fields", () => {
  const expected = [
    {
      path: "/records/search",
      method: "GET",
      fields: ["query"],
    },
    {
      path: "/transactions/status",
      method: "GET",
      fields: ["ref"],
    },
    {
      path: "/appointments/submit",
      method: "POST",
      fields: ["fullName", "email", "branch", "serviceType", "preferredDate", "notes"],
    },
    {
      path: "/support/submit",
      method: "POST",
      fields: ["email", "category", "subject", "referenceNo", "message"],
    },
    {
      path: "/records/[recordNo]/request-copy/submit",
      method: "POST",
      fields: ["fullName", "email", "purpose", "deliveryOption", "remarks"],
    },
    {
      path: "/login/submit",
      method: "POST",
      fields: ["username", "password"],
    },
    {
      path: "/comments/submit",
      method: "POST",
      fields: ["displayName", "message"],
    },
  ];

  for (const contract of expected) {
    const actual = WAF_ROUTES.find((route) => route.path === contract.path);
    assert.ok(actual, `Missing WAF route contract for ${contract.path}`);
    assert.equal(actual.method, contract.method, `${contract.path} method`);
    assert.deepEqual(
      actual.expectedParams.map((parameter) => parameter.name).sort(),
      [...contract.fields].sort(),
      `${contract.path} payload fields`,
    );
  }
});
