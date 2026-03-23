# Security Best Practices Report

## Executive Summary

I reviewed the current uncommitted changes with a FastAPI and Next.js/React security lens. The highest-impact issue is the new global Content Security Policy shipping with `unsafe-inline` and `unsafe-eval`, which significantly weakens the main browser-side XSS control you just added. I also found two backend hardening gaps in the new FastAPI middleware/config path: host-header validation is still absent, and the request-size limit can be bypassed whenever `Content-Length` is omitted.

---

## High Severity

### SBP-001

- **Rule ID:** NEXT-HEADERS-001 / REACT-CSP-001
- **Severity:** High
- **Location:** `frontend/next.config.ts` lines 28-37
- **Evidence:**

```ts
{
  key: 'Content-Security-Policy',
  value: [
    "default-src 'self'",
    "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
  ].join('; '),
}
```

- **Impact:** The new CSP is present, but allowing both `'unsafe-inline'` and `'unsafe-eval'` in `script-src` materially weakens XSS defenses and leaves a successful injection far easier to exploit.
- **Fix:** Split CSP behavior by environment. Keep any dev-only relaxation out of the production header path, and remove `'unsafe-inline'` and `'unsafe-eval'` from production `script-src`. If a framework/runtime requirement truly needs one of them, document exactly why and scope it to the narrowest environment possible.
- **Mitigation:** If you cannot tighten the CSP immediately, treat it as partial hardening only and prioritize removing any DOM/HTML injection sinks elsewhere in the app.
- **False positive notes:** If this config is only ever used in local development, the risk is lower. As written, it applies to all routes and appears intended for the runtime header policy, so I am treating it as production-relevant.

---

## Medium Severity

### SBP-002

- **Rule ID:** FASTAPI-DEPLOY-003 baseline host validation
- **Severity:** Medium
- **Location:** `web_app/presentation/app.py` lines 95-140
- **Evidence:**

```py
app = FastAPI(
    title="Injection Alert Classification System",
    description="API for classifying HTTP requests as normal or injection attacks",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

# ... only CORSMiddleware, SecurityHeadersMiddleware, BodySizeLimitMiddleware are added
```

- **Impact:** The app still has no visible `TrustedHostMiddleware` or equivalent host allowlist, so it relies entirely on upstream infrastructure for Host-header validation. That is a common hardening gap that can matter for cache poisoning, poisoned absolute URL generation, and proxy/header confusion if the edge layer is misconfigured.
- **Fix:** Add `TrustedHostMiddleware` with an allowlist driven by configuration, or document and verify that the reverse proxy/load balancer enforces the same control before requests reach FastAPI.
- **Mitigation:** If this is intentionally delegated to infrastructure, make that explicit in code or docs and verify the edge configuration as part of deployment checks.
- **False positive notes:** I did not find app code in the reviewed files that directly builds security-sensitive absolute URLs from `Host`, so this is a hardening finding rather than proof of an immediately exploitable bug.

### SBP-003

- **Rule ID:** FASTAPI-LIMITS-001
- **Severity:** Medium
- **Location:** `web_app/presentation/middleware/body_limit.py` lines 28-30
- **Evidence:**

```py
content_length = request.headers.get("content-length")
if content_length is None:
    return await call_next(request)
```

- **Impact:** The new request-size limit only fires when the client supplies `Content-Length`. A client that streams a body without that header can bypass the application-side size check, which weakens the intended DoS protection unless the edge proxy also enforces a hard body limit.
- **Fix:** Enforce request-size limits at the reverse proxy/load balancer and, if feasible, add streaming/body-read safeguards in the app for endpoints that accept large or attacker-controlled bodies.
- **Mitigation:** Document that this middleware is advisory and depends on edge-layer body limits for full enforcement.
- **False positive notes:** Some servers or client libraries will set `Content-Length` automatically, so casual requests will still be limited. This finding is about a bypassable control, not a claim that every request path is currently exploitable.

---

## Low Severity

### SBP-004

- **Rule ID:** NEXT-DEPLOY-001 / deployment secret hygiene
- **Severity:** Low
- **Location:** `docker-compose.yml` lines 20-27
- **Evidence:**

```yml
frontend:
  build: ./frontend
  ports:
    - "3000:3000"
  env_file:
    - frontend/.env.local
  environment:
    FASTAPI_BASE_URL: http://backend:8000
```

- **Impact:** The compose file injects the entire `frontend/.env.local` file into the frontend container. That is acceptable for local development, but it increases the chance that dev-only settings or broader-than-needed secrets are loaded into runtime containers when this compose setup is reused outside a tightly controlled local environment.
- **Fix:** Prefer a dedicated compose env file with only the variables actually required by the containerized frontend, and keep `.env.local` for interactive local development only.
- **Mitigation:** Ensure this compose stack is clearly documented as local-only and never used as-is for shared or production environments.
- **False positive notes:** This is an operational least-privilege concern, not evidence that a secret is already exposed to the browser.

---

## Files Reviewed

- `docker-compose.yml`
- `frontend/lib/bff-client.ts`
- `frontend/lib/bff-client.test.ts`
- `frontend/next-env.d.ts`
- `web_app/presentation/app.py`
- `web_app/presentation/middleware/body_limit.py`
- Staged context also checked in:
  - `frontend/next.config.ts`
  - `frontend/proxy.ts`
  - `web_app/presentation/middleware/security_headers.py`
  - `Dockerfile`
  - `frontend/Dockerfile`
  - `.github/workflows/ci.yml`

## Notes

- I did not find evidence in the reviewed uncommitted files of secrets being committed directly into source.
- I did not find a direct browser-to-FastAPI boundary bypass in the current unstaged `docker-compose.yml`; removing the published `modsecurity` port corrected that earlier regression.
