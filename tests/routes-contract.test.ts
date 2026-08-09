import assert from "node:assert/strict";
import test from "node:test";

import { WAF_ROUTES } from "../lib/routes";

test("WAF route inventory matches the portal's actual form and query entry points", () => {
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
        route.method === "POST",
    ),
  );
});
