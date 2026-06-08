# Batch 2 Backend Runtime Fix Report

## 1. Result

**Passed.**

Backend runtime blockers fixed. Copy request works. Docker DB persists. WAF testing can start for backend flows.

## 2. Files Changed

| File | Why |
| --- | --- |
| `prisma/seed.ts` | Seed records now use public `LND-*` IDs |
| `docker-compose.yml` | Mounts `./prisma:/app/prisma` for durable SQLite |
| `scripts/backend-readiness-check.ts` | Uses selected test port correctly |
| `docs/BACKEND_READINESS_EVIDENCE.json` | Fresh Docker readiness evidence |
| `docs/BATCH2_BACKEND_RUNTIME_FIX_REPORT.md` | This report |

## 3. Record ID Convention

Chosen: **`LND-2026-####`**

Why:

- UI already links to `LND-*`.
- Search uses `LND-*`.
- WAF docs/tests already expect `LND-2026-0001`.
- Less route churn.

Seed changed:

- `REC-2026-0001` -> `LND-2026-0001`
- Same pattern through `LND-2026-0010`
- Seeded transactions now reference `LND-*`

## 4. Copy Request Test

| Check | Result |
| --- | --- |
| GET `/records/LND-2026-0001` | 200 |
| GET `/records/LND-2026-0001/request-copy` | 200 |
| POST `/records/LND-2026-0001/request-copy/submit` | 303 |
| Transaction write | Yes |
| Generated ref | `TXN-2026-9641` |
| Status lookup | Found |
| GET `/transactions/status?ref=TXN-2026-9641` | 200 |

## 5. DB Counts

Final Docker readiness rerun:

| Model | Before | After |
| --- | ---: | ---: |
| Record | 10 | 10 |
| Transaction | 7 | 9 |
| SupportTicket | 2 | 4 |
| Appointment | 1 | 2 |
| Comment | 6 | 8 |
| LoginAttempt | 2 | 4 |

Copy request specific:

| Model | Before | After |
| --- | ---: | ---: |
| Transaction | 7 | 8 |

## 6. Docker

| Check | Result |
| --- | --- |
| `docker compose build` | Pass |
| `docker compose up -d --force-recreate` | Pass |
| Container | `cybertrace-demo-portal` running |
| Next version | `15.1.9` |
| `/` | 200 |
| `/records/search` | 200 |
| `/records/LND-2026-0001/request-copy` | 200 |
| Comment POST | 303 |
| Survives restart | Yes |
| Survives `docker compose down` + `up -d` | Yes |

Persistence proof:

- Marker: `Docker volume audit f4004334459f4e59841d1707da0cb0d1`
- Before restart: found
- After restart: found
- After down/up recreate: found

Volume:

- `./prisma:/app/prisma`
- SQLite stays in host `prisma/dev.db`

## 7. npm Audit

Result: **5 vulnerabilities**

| Package | Severity | Source |
| --- | --- | --- |
| `next` | critical | direct |
| `postcss` | moderate | via `next` |
| `prisma` | high | direct |
| `@prisma/config` | high | via `prisma` |
| `effect` | high | via `@prisma/config` |

Available non-major fixes reported:

- `next@15.5.19`
- `prisma@6.19.3`

Not applied in this batch:

- Prompt said investigate/report.
- No Next 16.
- No Prisma 7.

## 8. Commands

| Command | Result |
| --- | --- |
| `npm ci` | Pass |
| `npx prisma validate` | Pass |
| `npx prisma generate` | Pass |
| `npm run typecheck` | Pass |
| `npm run lint` | Pass |
| `npm run build` | Pass |
| `npx prisma db seed` | Pass |
| `docker compose build` | Pass |
| `docker compose up -d --force-recreate` | Pass |
| Backend readiness rerun | Pass |

Note:

- First `npm ci` hit Windows `EPERM` from stale local Next/TS node processes.
- Stopped workspace Node processes.
- Reran `npm ci`.
- Passed.

## 9. WAF Start?

**Yes, backend flows can start WAF testing.**

Ready:

- GET routes work.
- Native POST forms work.
- SQLite writes work.
- Generated refs can be looked up.
- Docker runs.
- Docker DB persists across recreate.

Still not WAF itself:

- ModSecurity not added.
- CRS not added.
- CyberTrace ingest not added.

## 10. Next Batch

Fix Batch 3:

- Patch vulnerable deps without major upgrade:
- `next` -> `15.5.19`
- `eslint-config-next` -> matching `15.5.x`
- `prisma` and `@prisma/client` -> `6.19.3`
- Rerun full build + readiness.
