# HTTP Error Pages

The portal uses a small dark error-page template for page responses. The page
header, status badge, icon, message, and action follow the selected Land Records
Portal design.

| Status | Response owner | Behavior |
| --- | --- | --- |
| 403 | Next.js middleware or target NGINX/ModSecurity | Generic access-restricted page; no rule, payload, or model details are exposed. |
| 404 | Next.js App Router | Branded page for missing routes and pages that call `notFound()`. |
| 429 | Next.js middleware | Branded page with the actual `Retry-After` value; the header remains unchanged. |
| 500 | Next.js page error boundary or target NGINX | Generic server-error fallback. Application route handlers keep their existing JSON or text bodies. |
| 502, 503, 504 | Target NGINX when it generates a gateway failure | Static pages remain available when the portal upstream is unavailable. Upstream responses pass through unchanged. |

The target NGINX error documents are static and served internally. NGINX does
not enable `proxy_intercept_errors`, so upstream API response bodies and headers
are not replaced with HTML. The app continues returning JSON for its route
handler validation, enforcement, and challenge responses.

## Local verification

The portal was built and exercised through an isolated local Compose project.
The page responses returned 404 and 500 with the branded card; a POST to the
challenge route kept its existing JSON 400 response. The enforcement boundary
unit test and a local boundary fixture returned 429 with `Retry-After: 7`, and
the page displayed that same value. The 7-second value is test input, not a
live rate-limit setting. NGINX generated 403/500/502/503/504 pages were also
checked locally; the ModSecurity 403 came from a CRS block and the 502 from the
isolated portal being stopped. No live deployment claim is implied.

Screenshots are in `docs/evidence/http-error-pages/`.
