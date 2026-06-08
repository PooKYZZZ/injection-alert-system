# Backend Readiness Verification - Land Records Demo Portal

## 1. Verdict

**Needs Cleanup.**

Core backend works. Tooling passes. SQLite works. Most forms write. Docker runs. Not full-ready: copy-request flow has record ID mismatch, Docker DB is lost after recreate, dependency security warnings remain.

## 2. Tooling

| Check | Result | Note |
| --- | --- | --- |
| `node -v` | Pass | `v22.22.2` |
| `npm -v` | Pass | `10.9.7` |
| `npm ci` | Pass | 5 npm vulnerabilities remain |
| `npx prisma validate` | Pass | Prisma schema valid |
| `npx prisma generate` | Pass | Prisma Client `6.19.0` generated |
| `npm run typecheck` | Pass | No TS errors |
| `npm run lint` | Pass | No ESLint errors |
| `npm run build` | Pass | Next `15.1.9` build OK |

## 3. Database

DB: `prisma/dev.db`

| Model | Before | After Local Tests | Result |
| --- | ---: | ---: | --- |
| Record | 10 | 10 | Pass |
| Transaction | 5 | 5 | Seed OK, copy flow failed |
| SupportTicket | 0 | 2 | Pass |
| Appointment | 0 | 1 | Pass |
| Comment | 3 | 5 | Pass |
| LoginAttempt | 0 | 2 | Pass |

Seed data exists. Prisma connects. Writes work for most models.

## 4. Routes

| Route | Method | Storage | Validation | Result |
| --- | --- | --- | --- | --- |
| `/` | GET | Prisma read | N/A | Pass |
| `/records/search` | GET | Prisma/mock read | Query based | Pass |
| `/records/LND-2026-0001` | GET | Page read | Param based | Pass |
| `/records/LND-2026-0001/request-copy` | GET | Prisma read | Param based | Fail, 404 |
| `/transactions/status` | GET | Prisma + static fallback | Query based | Pass |
| `/support` | GET | Page | N/A | Pass |
| `/support/submit` | POST | Prisma `SupportTicket` | Server-side | Pass |
| `/appointments` | GET | Page | N/A | Pass |
| `/appointments/submit` | POST | Prisma `Appointment` | Server-side | Pass |
| `/comments` | GET | Prisma `Comment` | N/A | Pass |
| `/comments/submit` | POST | Prisma `Comment` | Zod | Pass |
| `/login` | GET | Page | N/A | Pass |
| `/login/submit` | POST | Prisma `LoginAttempt` | Zod | Pass |
| `/success` | GET | Page | Query based | Pass |
| `/demo-guide` | GET | Page | N/A | Pass |

Middleware: exists, no-op, empty matcher. No route rewrite issue found.

## 5. Normal Forms

| Flow | Endpoint | Response | DB Write | Status Lookup | Verdict |
| --- | --- | --- | --- | --- | --- |
| Support | `/support/submit` | 303 | Yes | Yes | Pass |
| Appointment | `/appointments/submit` | 303 | Yes | Yes | Pass |
| Comment | `/comments/submit` | 303 | Yes | N/A | Pass |
| Login | `/login/submit` | 303 | Yes | N/A | Pass |
| Copy request | `/records/LND-2026-0001/request-copy/submit` | 404 | No | No | Fail |

Login stores username and `success=false`. Password not stored.

## 6. Validation

| Case | Expected | Actual | Verdict |
| --- | --- | --- | --- |
| Missing support fields | 400, no write | 400, no write | Pass |
| Invalid email | 400, no write | 400, no write | Pass |
| Past appointment date | 400, no write | 400, no write | Pass |
| Missing login username | 400, no write | 400, no write | Pass |
| Missing copy purpose | 400 expected | 404 record not found first | Needs cleanup |
| Bad copy record | 404, no write | 404, no write | Pass |
| Bad transaction ref | Clear not found | 200 page | Needs cleanup |

## 7. Suspicious Local Values

Simple local-only suspicious strings did not crash the app.

| Field / Route | Result |
| --- | --- |
| Search query | 200, no write, no crash |
| Support message | 303, write, no crash |
| Comment message | 303, write, no crash |
| Copy remarks | 404, no write |
| Login username | 303, write, no crash |

Backend-only readiness. No WAF installed yet. No blocking claim made.

## 8. Cookies

No `Set-Cookie` observed on tested submissions.

| Flow | Cookie |
| --- | --- |
| Support | None |
| Appointment | None |
| Comment | None |
| Login | None |
| Copy request | None |

Acceptable for local demo.

## 9. Docker

| Check | Result |
| --- | --- |
| Container | Running: `cybertrace-demo-portal` |
| App version | Next `15.1.9` |
| `/` | 200 |
| `/records/search` | 200 |
| `/comments` | 200 |
| Comment POST | 303 |
| Survives restart | Yes |
| Survives `docker compose down` + recreate | No |

Docker DB is container-local. Add a SQLite volume later if persistence matters during WAF testing.

## 10. WAF Readiness

Ready:

- Clear GET/POST routes exist.
- Native form posts are used.
- Form bodies are normal `application/x-www-form-urlencoded`.
- Field names are stable.
- No Server Actions needed for tested critical flows.
- Local `BASE_URL` style testing works.

Not ready:

- Copy request flow broken for current public `LND-*` record route.
- Docker DB is lost after recreate.
- npm security warnings remain.
- No ModSecurity/CRS proxy yet.

CRS note: future CRS behavior uses inspection and anomaly scoring. Do not claim guaranteed blocking before WAF tests run.

## 11. Top Issues

1. Copy request record mismatch: public route uses `LND-2026-0001`, Prisma seed uses `REC-2026-0001`.
2. Docker SQLite persistence is not durable after container recreate.
3. npm reports 5 vulnerabilities, including Next security warning.
4. Prisma `package.json#prisma` config is deprecated for Prisma 7.
5. Bad transaction reference returns a normal 200 page instead of clearer not-found behavior.

## 12. Next Step

Run Fix Batch 2:

- Align public record IDs and seeded Prisma record IDs.
- Add Docker SQLite persistence volume.
- Then rerun backend readiness audit.
