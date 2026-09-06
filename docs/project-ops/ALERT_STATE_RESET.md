# Alert-state reset runbook

This runbook resets the local demonstration alert state while preserving the
application, authentication, model, datasets, training results, and portal
data. It is intentionally narrow: it removes threat/detection history and
resets the in-memory services, but it does not destroy Docker volumes or run a
full database reset.

## What is stored where

| State | Store | Used by | Reset treatment |
| --- | --- | --- | --- |
| Detection and alert history | Supabase `traffic_logs` | Alerts, dashboard totals/charts, triage, ML statistics derived from live traffic | Delete all rows |
| Reviewer labels | Supabase `traffic_label_reviews` | Triage and retraining evidence | Delete all rows; it is tied to `traffic_logs` |
| Enforcement recommendations | Supabase `enforcement_recommendations` | Enforcement state and audit views | Delete all rows |
| Active enforcement windows/grants | Supabase `enforcement_request_windows`, `enforcement_challenge_grants` | LOW/MEDIUM/HIGH enforcement decisions | Delete all rows |
| Effective WAF state | Supabase `waf_effective_state` | WAF candidate/effective-state views | Delete all rows |
| Desired WAF singleton | Supabase `waf_enforcement_state` | Current desired WAF configuration and revision | Preserve; the clean singleton is not attack history |
| Telegram delivery and dedupe state | Supabase `notification_outbox` rows where `kind = 'threat_detected'` | Notification worker retry/deduplication and delivery status | Delete threat rows only |
| Authentication/security history | Supabase `security_events`, `auth_*`, and non-threat outbox rows | Login, MFA, account recovery, and account notifications | Preserve |
| Backend statistics cache/counters | Backend process memory | `/api/stats`, notification-worker status, SSE alert stream | Recreate the backend container |
| Browser alert/stat cache | Next.js/React Query process memory | Dashboard and Alerts pages | Reload the page; no persisted alert cache was found |
| WAF audit history | `logs/modsecurity/**` JSONL/access-log files | ModSecurity bridge correlation and local proof | Archive, then empty the exact runtime files |

The demo portal's Prisma SQLite database (`E:\AI\land-records-portal\prisma`)
is separate from the alert database and is not part of this reset. Model
artifacts, datasets, staging/archive directories, retraining results, source
configuration, and the named unused local Postgres volume are also preserved.

## Safety rules

1. Confirm the repository path and the Supabase project before running the
   deletion SQL. The current project is `ryfqleozfvrvavrxfbtq`; verify it in
   the Supabase dashboard first.
2. Prefer a Supabase backup/snapshot or export before repeated resets. The
   reset run on 2026-09-06 used a narrow transaction and pre/post counts, but
   did not create a `pg_dump` because the local images did not contain that
   utility.
3. Stop the backend, bridge, and WAF before deleting rows or clearing the WAF
   file, so no worker can write new state during the reset. Stopping all six
   services is also safe when using the normal startup command below.
4. Do not use `DROP DATABASE`, `TRUNCATE ... CASCADE`, Docker volume removal,
   or broad filesystem deletion for this procedure.

## Repeatable procedure

Run these commands from the repository root in PowerShell.

### 1. Stop writers

```powershell
Set-Location 'E:\AI\PDDDD\injection-alert-system'

docker stop --timeout 20 injection-alert-system-demo-target-bridge-1
docker stop --timeout 20 injection-alert-system-backend-1
docker stop --timeout 20 injection-alert-system-demo-target-modsecurity-1
```

Stopping the frontend, portal, and cloudflared containers too is optional. The
startup command uses `--force-recreate` for the full stack and will refresh
their in-memory state as well.

### 2. Archive and empty local WAF runtime logs

This preserves a recoverable copy outside the repository and keeps the log
files in place for the containers' bind mounts.

```powershell
$resetStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$resetArchive = Join-Path $env:TEMP ("cybertrace-alert-reset-$resetStamp")
New-Item -ItemType Directory -Path $resetArchive -Force | Out-Null

$resetLogPaths = @(
  'logs\modsecurity\modsec_audit.jsonl',
  'logs\modsecurity\demo-target\modsec_audit.jsonl',
  'logs\modsecurity\pr7\modsec_audit.jsonl',
  'logs\modsecurity\search-records-test\modsec_audit.jsonl',
  'logs\modsecurity\source-correlation-test\modsec_audit.jsonl',
  'logs\modsecurity\source-correlation-test\nginx_access.log'
)

foreach ($resetLogPath in $resetLogPaths) {
  if (Test-Path -LiteralPath $resetLogPath) {
    $resetDestination = Join-Path $resetArchive ($resetLogPath -replace '[\\/:]', '_')
    Copy-Item -LiteralPath $resetLogPath -Destination $resetDestination -Force
    Clear-Content -LiteralPath $resetLogPath
  }
}

Write-Output "Archived reset evidence under $resetArchive"
```

### 3. Delete only demo threat state in Supabase

Run the following as one transaction in the Supabase SQL Editor for the
verified project. The order follows the foreign-key dependencies and avoids
deleting authentication/security records or non-threat notifications.

```sql
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DELETE FROM public.notification_outbox
WHERE kind = 'threat_detected';

DELETE FROM public.waf_effective_state;
DELETE FROM public.enforcement_recommendations;
DELETE FROM public.traffic_label_reviews;
DELETE FROM public.traffic_logs;
DELETE FROM public.enforcement_request_windows;
DELETE FROM public.enforcement_challenge_grants;

SELECT setval('public.traffic_logs_id_seq', 1, false);
SELECT setval('public.traffic_label_reviews_id_seq', 1, false);
SELECT setval('public.enforcement_recommendations_id_seq', 1, false);
SELECT setval('public.enforcement_request_windows_id_seq', 1, false);
SELECT setval('public.enforcement_challenge_grants_id_seq', 1, false);
SELECT setval('public.waf_effective_state_id_seq', 1, false);

COMMIT;
```

Before committing the transaction, cancel it if the affected table names or
project are not exactly the expected ones. For a post-reset count check, run:

```sql
SELECT json_build_object(
  'traffic_logs', (SELECT count(*) FROM public.traffic_logs),
  'traffic_label_reviews', (SELECT count(*) FROM public.traffic_label_reviews),
  'enforcement_recommendations', (SELECT count(*) FROM public.enforcement_recommendations),
  'enforcement_request_windows', (SELECT count(*) FROM public.enforcement_request_windows),
  'enforcement_challenge_grants', (SELECT count(*) FROM public.enforcement_challenge_grants),
  'waf_effective_state', (SELECT count(*) FROM public.waf_effective_state),
  'threat_detected_outbox', (SELECT count(*) FROM public.notification_outbox WHERE kind = 'threat_detected'),
  'non_threat_outbox', (SELECT count(*) FROM public.notification_outbox WHERE kind <> 'threat_detected'),
  'security_events', (SELECT count(*) FROM public.security_events)
) AS reset_verification;
```

Expected reset values are zero for the seven threat/demo-state fields listed
before `non_threat_outbox`; `non_threat_outbox` and `security_events` retain
their existing values when those features have been used.

### 4. Recreate the existing stack

```powershell
pwsh -NoProfile -File scripts/start_full_cloudflare_target.ps1 `
  -PortalContext 'E:\AI\land-records-portal' `
  -NoBuild
```

`-NoBuild` is sufficient when only alert data was reset. The startup script
uses the normal project Compose files and force-recreates the containers; it
does not remove volumes or change the model.

### 5. Verify the clean baseline

Check all six containers:

```powershell
$resetContainers = @(
  'injection-alert-system-backend-1',
  'injection-alert-system-frontend-1',
  'injection-alert-system-demo-portal-1',
  'injection-alert-system-demo-target-modsecurity-1',
  'injection-alert-system-demo-target-bridge-1',
  'injection-alert-system-cloudflared-1'
)

foreach ($resetContainer in $resetContainers) {
  docker inspect --format '{{.Name}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}|exit={{.State.ExitCode}}' $resetContainer
}

$resetFiles = Get-ChildItem -LiteralPath 'logs' -File -Recurse
'LOG_NONZERO_FILES=' + @($resetFiles | Where-Object Length -gt 0).Count
'LOG_TOTAL_BYTES=' + [int64](@($resetFiles | Measure-Object Length -Sum).Sum)
```

Then reload Dashboard and Alerts. The backend APIs must report:

```text
total_requests=0
blocked_count=0
allowed_count=0
throttled_count=0
alerts total=0 and items=[]
```

The ML model may still display its packaged evaluation metadata and model
version; those are not live alert-history counters. The Telegram chat may
still contain old messages because this procedure cannot erase Telegram's
external message history. It does remove the application's threat outbox and
dedupe state, and recreating the worker clears its in-memory send counters.

## First-event validation (optional)

Only after the zero baseline has been captured, send one controlled request to
the protected demo Search Records route. This intentionally creates one new
event and one Telegram notification:

```powershell
docker exec injection-alert-system-demo-portal-1 node -e 'fetch("http://demo-target-modsecurity:8080/records/search?query=%27+OR+%271%27%3D%271",{redirect:"manual",headers:{"User-Agent":"cybertrace-reset-first-event-validation/1.0","Cache-Control":"no-store"}}).then(async r=>{await r.arrayBuffer();console.log("route=/records/search status="+r.status)}).catch(e=>{console.error(e.message);process.exitCode=1})'
```

For the known local stack, the expected chain is:

1. Search Records returns `403` from ModSecurity.
2. The audit bridge forwards the event to FastAPI.
3. Alerts contains exactly one `SQL Injection` event with a `BLOCKED` action.
4. `notification_outbox` contains one `threat_detected`/`telegram` row with
   `status = 'sent'` after the worker delivers it.

This validation request is deliberately outside the clean baseline. Run the
reset procedure again afterward if the environment must finish with zero
alerts.

## Current-run evidence

On 2026-09-06 the procedure was executed against the current Supabase project.
The post-reset database/API checks reported zero detection rows, zero threat
outbox rows, empty Alerts, and zero dashboard counters. One controlled
Search Records SQL-injection request was then verified as `403`, `SQL
Injection`, `CRITICAL`, `BLOCKED`, and a sent Telegram outbox event. That
validation event was archived and removed by a second reset, after which the
zero baseline was verified again.
