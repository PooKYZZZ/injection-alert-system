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
