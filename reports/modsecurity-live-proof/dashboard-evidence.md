# CyberTrace Dashboard Screenshot Evidence

## Purpose

Record local dashboard screenshot evidence that CyberTrace displays WAF and ML alert evidence from the verified ModSecurity/OWASP CRS demo path.

This is demo evidence only. It is not a pixel-perfect visual regression baseline and is not production deployment proof.

## Evidence Source Reports

- `reports/modsecurity-live-proof/e2e-proof.md`
- `reports/modsecurity-live-proof/crs-baseline.md`
- `reports/modsecurity-live-proof/demo-target-crs-proof.md`

## Runtime Environment

- Dashboard URL: `http://localhost:3000`
- Capture tool: initial Playwright capture was replaced by reviewed pasted screenshots from the operator
- Browser: local browser capture, exact browser not recorded in pasted image metadata
- Viewport: pasted screenshots are `1920x920`
- Date/time: initial replacement set `2026-06-24 23:42:18 +08:00`; final demo-target screenshot set saved `2026-06-27 +08:00`
- Git commit: `c1ec4c2`
- Runtime target scope: local dashboard pages only (`/login`, `/dashboard`, `/alerts`, `/ml-health`)

## Screenshot Replacement Method

- Reviewed pasted files `image1.png` through `image5.png` under `reports/modsecurity-live-proof/screenshots/`.
- Deleted the earlier Playwright-generated PNG files.
- Renamed the pasted files to descriptive evidence names.
- Did not write cookies, session headers, or Playwright `storageState` files.
- Did not call external URLs, scanner targets, fuzzers, Supabase dashboards, `localhost:8000`, or the portal target ports during the replacement step.

## Screenshot Inventory

| Screenshot | Path | Page | What it proves | Status |
|---|---|---|---|---|
| Dashboard overview | `reports/modsecurity-live-proof/screenshots/dashboard-overview.png` | `/dashboard` | CyberTrace dashboard loads and shows current high-confidence, blocked, confidence, false-positive, attack trend, distribution, source IP, and target path evidence. | Created |
| Dashboard overview, 7-day Jun 23 hover | `reports/modsecurity-live-proof/screenshots/dashboard-overview-7d-jun23.png` | `/dashboard` | Dashboard trend view shows 7-day WAF/ML activity with blocked counts and source/target aggregates. | Created |
| Dashboard overview, 7-day Jun 24 hover | `reports/modsecurity-live-proof/screenshots/dashboard-overview-7d-jun24.png` | `/dashboard` | Dashboard trend view shows the later 7-day hover state and high-confidence blocked alert totals. | Created |
| Alerts table WAF event | `reports/modsecurity-live-proof/screenshots/alerts-table-waf-event.png` | `/alerts` | Alerts table shows WAF/ML alert rows with source IP, request path, prediction, confidence, action taken, and CRS score columns. | Created |
| Alert detail WAF event | `reports/modsecurity-live-proof/screenshots/alert-detail-waf-event.png` | `/alerts` detail drawer | Alert detail drawer opens for a visible WAF event and shows core details, WAF evidence, captured request, analyst actions, and intervention controls. | Created |
| Demo-target dashboard overview | `reports/modsecurity-live-proof/screenshots/demo-target-8089-dashboard-overview.png` | `/dashboard` | Dashboard overview shows blocked high-confidence activity and `/records/search` in top targeted paths for the final realistic demo-target proof. | Created |
| Demo-target alerts table | `reports/modsecurity-live-proof/screenshots/demo-target-8089-alerts-table.png` | `/alerts` | Alerts table shows `/records/search`, `SQL Injection`, `100% (HIGH)`, `Blocked`, and `crs_score=15.00` rows for the final realistic demo-target proof. | Created |
| Default WAF alert detail | `reports/modsecurity-live-proof/screenshots/main-8088-alert-detail.png` | `/alerts` detail drawer | Alert detail drawer shows captured request evidence for the default `8088` WAF path, including `localhost:8088`, CRS score `5.00`, and rule IDs `942100`, `949110`. | Created |
| Default WAF alert detail duplicate | `reports/modsecurity-live-proof/screenshots/main-8088-alert-detail-duplicate.png` | `/alerts` detail drawer | Duplicate of the default `8088` detail drawer screenshot saved with an accurate non-`8089` name. | Created |
| ML health overview | `reports/modsecurity-live-proof/screenshots/ml-health-overview.png` | `/ml-health` | ML health page shows serving health, request count, latency, policy bands, per-class F1, and prediction distribution. Queue-specific UI fields are not visible in this screenshot. | Created |

## Observed UI Evidence

- Dashboard loaded successfully after login.
- Alerts table loaded successfully.
- Alert rows were visible at capture time.
- Visible alert table evidence included `SQL Injection`, source IP `172.21.0.1`, request path `/api/health`, confidence `100% (HIGH)`, action `Blocked`, and CRS score `5.00`.
- Alert detail was visible for an `Other Attacks` WAF event.
- The alert detail drawer showed WAF evidence, including CRS score `10.00`, rule IDs `930120`, `932160`, `949110`, captured request metadata, analyst actions, and intervention options.
- Final demo-target alerts table evidence includes `/records/search`, `SQL Injection`, `100% (HIGH)`, `Blocked`, and CRS score `15.00`.
- Final demo-target dashboard overview evidence includes `/records/search` in the targeted-path summary.
- Latest alert detail drawer screenshots show the default `localhost:8088` WAF path with CRS score `5.00`; they are retained as default-path detail evidence, not as `8089` detail evidence.
- ML health overview screenshot is present, but queue-health fields are not visible in the provided capture.
- Sidebar model indicator showed `distilbert_v3` as stable during the capture.

## Limitations

- The screenshots prove the dashboard display state at capture time only.
- The capture used the documented local demo login path; real RBAC, 2FA, and production-grade login remain separate planned work.
- The latest `/ml-health` screenshot is an overview capture, not queue-specific UI evidence.
- The latest alert detail drawer screenshots show the default `8088` path; `8089` SQL Injection evidence is visible in the alerts table screenshot.
- This report does not prove email notifications, SSE/EventSource real-time alerting, production retention, or production WAF deployment.
- This report does not expose or store cookies, API keys, `.env` values, database URLs, Supabase credentials, session tokens, or real passwords.

## Result

PASS: The saved screenshots now cover the final local demo proof evidence expected for the current checklist: dashboard overview, `/records/search` alerts table with `crs_score=15`, default-path WAF detail drawer evidence, and ML health overview. Queue-specific ML health UI evidence is not claimed from the supplied screenshots.

## Artifact Summary

Report path:

- `reports/modsecurity-live-proof/dashboard-evidence.md`

Files created:

- `reports/modsecurity-live-proof/dashboard-evidence.md`
- Screenshot PNGs under `reports/modsecurity-live-proof/screenshots/`:
  - `dashboard-overview.png`
  - `dashboard-overview-7d-jun23.png`
  - `dashboard-overview-7d-jun24.png`
  - `alerts-table-waf-event.png`
  - `alert-detail-waf-event.png`
  - `demo-target-8089-dashboard-overview.png`
  - `demo-target-8089-alerts-table.png`
  - `main-8088-alert-detail.png`
  - `main-8088-alert-detail-duplicate.png`
  - `ml-health-overview.png`

Files edited:

- `PD2_PRIORITY_TRACKER.md`
- `docs/project-ops/STATUS.md`
- `docs/project-ops/LIVING_CHECKLIST.md`

Files removed from the earlier capture set:

- `frontend/e2e/dashboard-evidence.spec.ts`
- `reports/modsecurity-live-proof/screenshots/ml-health.png`

Tracker status:

- Done for local proof: dashboard, alerts table, default-path WAF alert detail, and ML health overview screenshots exist.
- Not claimed: queue-specific ML health UI screenshot.
