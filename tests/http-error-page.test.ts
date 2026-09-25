import assert from "node:assert/strict";
import test from "node:test";

import {
  httpErrorPageDocument,
  httpErrorPageMarkup,
  type HttpErrorStatus,
} from "../lib/http-error-page";

test("shared page template covers selected statuses and keeps their labels accurate", () => {
  const cases: Array<[HttpErrorStatus, string]> = [
    [403, "Access Restricted"],
    [404, "Page Not Found"],
    [429, "Too Many Requests"],
    [500, "Server Error"],
    [502, "Service Unavailable"],
    [503, "Temporarily Unavailable"],
    [504, "Request Timed Out"],
  ];

  for (const [status, title] of cases) {
    const document = httpErrorPageDocument(status);
    assert.match(document, new RegExp(`aria-label="HTTP ${status}"`));
    assert.match(document, new RegExp(`<h1 id="http-error-title">${title}</h1>`));
    assert.match(document, /Land Records Portal/);
    assert.doesNotMatch(document, /<script|https?:\/\//i);
  }
});

test("429 page displays only the supplied retry interval", () => {
  const document = httpErrorPageDocument(429, 7);

  assert.match(document, /Retry after 7 seconds\./);
  assert.doesNotMatch(document, /60 seconds/);
  assert.doesNotMatch(httpErrorPageMarkup(429), /Retry after/);
});

test("service errors offer a same-URL retry action", () => {
  const markup = httpErrorPageMarkup(503);

  assert.match(markup, /<form action="" method="get">/);
  assert.match(markup, /Try Again/);
});

test("restricted access page offers support without exposing enforcement details", () => {
  const document = httpErrorPageDocument(403);

  assert.match(document, /Contact Support/);
  assert.doesNotMatch(document, /CRS|confidence|policy|payload/i);
});
