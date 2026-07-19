# Telegram Threat Alerts Design

## Objective

Add Telegram as a durable, failure-isolated notification channel for persisted
non-Normal detections whose confidence tier is `HIGH` or `CRITICAL`. Telegram
must never become a dependency of detection persistence, the HTTP response, or
the SSE/dashboard path.

## Scope and constraints

This is a backend-only feature slice. It reuses the existing PostgreSQL
`notification_outbox`, notification worker, lease/retry lifecycle, HTTPX
dependency, structured logging, and post-persistence threat-notification hook.
It adds no broker, Telegram framework, polling, webhook, interactive command,
subscription management, enforcement, model, or frontend work.

The backend transport values for `action_taken` and all confidence thresholds
remain unchanged. `HIGH` and `CRITICAL` are confidence tiers, not a new severity
model.

## Architecture

The WAF ingest use case persists and commits the alert before notification
orchestration runs. The presentation route then independently attempts the
existing email enqueue and the new Telegram enqueue. An enqueue exception or an
unavailable Telegram configuration is recorded safely and cannot change the
successful detection response.

Telegram jobs use the existing outbox and worker. The worker continues to own
claiming, leases, deadlines, bounded retry, completion, failure transitions,
and ambiguous-completion handling. A small channel-aware delivery boundary owns
email rendering/provider delivery and Telegram rendering/provider delivery.
This keeps provider-specific behavior out of the lifecycle code without
creating a generic plugin framework.

## Configuration and degradation

The server-only settings are:

- `THREAT_TELEGRAM_ENABLED=false`
- `TELEGRAM_BOT_TOKEN=`
- `TELEGRAM_CHAT_ID=`
- `TELEGRAM_LIVE_TEST_ENABLED=false` for an explicitly guarded provider smoke

When disabled, Telegram credentials are optional and no Telegram job or network
request is created. When enabled with incomplete credentials, Telegram is
unavailable, a safe structured error is emitted, no Telegram job is enqueued,
and the backend and existing email channel continue operating. Startup never
calls Telegram to validate availability. The normalized key
`telegrambottoken` is treated as sensitive by structured-log redaction.

## Outbox contract and migration

An additive Alembic migration descends from `20260715_000021`. It widens the
active channel constraint from email-only to `email | telegram`, adds a database
constraint that permits Telegram only for `threat_detected`, extends the
claimable index to cover both channels, and introduces a versioned claim RPC
that returns `channel`. Existing V6.1 functions remain available for migration
compatibility. The downgrade safely restores the email-only contract and must
not silently preserve incompatible Telegram rows.

`PendingNotification` and `OutboxJob` gain a typed channel field, defaulted or
positioned compatibly for existing email producers. Repository enqueue writes
the notification's channel rather than hard-coding `email`.

Telegram jobs use a channel-specific database-authoritative dedupe key:
`threat/{alert_id}/telegram`. Existing email keys and behavior remain intact.
The design prevents duplicate jobs and ordinary concurrent double-processing,
but does not claim exactly-once external Telegram delivery.

## Eligibility and safe payload

Telegram eligibility requires all of the following:

- Telegram is enabled and completely configured.
- The persisted alert ID is available.
- The prediction is not `Normal`.
- The confidence tier is exactly `HIGH` or `CRITICAL`.

`LOW` and `MEDIUM` never create Telegram jobs. Email retains its existing
eligibility and configuration policy.

The safe Telegram outbox payload contains only alert ID, timestamp, attack
category, confidence tier, numeric confidence percentage, HTTP method,
sanitized path without query or fragment, and an authenticated dashboard link.
It excludes source IP, headers, cookies, credentials, request/query bodies,
raw model input, sessions, and WAF payloads. Telegram threat jobs expire after
30 minutes; the dashboard remains the historical source of truth.

## Telegram delivery boundary

The provider uses `httpx.AsyncClient` to make a JSON `POST` to Telegram Bot API
`sendMessage`. The request contains `chat_id`, plain-text `text`, and disabled
link previews. It uses explicit connect, read, write, and pool timeouts. The bot
token is present only in the environment and authenticated URL; neither the URL,
chat ID, message body, nor raw Telegram response is logged.

The message wording is `HIGH-CONFIDENCE THREAT` or `CRITICAL-CONFIDENCE THREAT`
and labels the value as `Confidence tier`. It contains the safe payload fields
and no Markdown/HTML parse mode.

On success the provider returns Telegram's `message_id`, which the existing
completion transition stores as the provider message ID.

## Failure handling

Provider failures use one shared error contract containing a stable error class,
retryability, an optional provider retry delay, and ambiguous-delivery state.
The existing email error remains compatible with it.

- Connection establishment/pool failures and Telegram 5xx responses are
  retryable with the existing capped exponential backoff and jitter.
- Telegram 429 is retryable and honors a valid bounded `retry_after` value.
- 400, 401, 403, invalid destination/configuration, and malformed requests are
  permanent failures.
- Read/write timeouts after delivery may have begun and malformed success
  responses are ambiguous; they are not blindly retried.
- Provider acceptance followed by failed database completion retains the
  existing ambiguous-completion warning and reconciliation limitation.

The current maximum-attempt lifecycle remains unchanged. Retry scheduling never
sleeps inside a request or test.

## Observability

Structured events distinguish Telegram queue creation, duplicate suppression,
sent delivery, permanent failure, retry scheduling, and ambiguous delivery.
They use stable categories and non-sensitive identifiers. Logs never include
the bot token, chat ID, authenticated Telegram URL, message text, request body,
or raw provider error description.

## Guarded smoke

`scripts/run_telegram_smoke.py` follows the existing Resend smoke pattern. It
refuses to send unless live testing is explicitly enabled, reads credentials
only from settings/environment, never prints them, sends a harmless synthetic
message, and reports a bounded pass/fail result. It verifies provider
configuration only and does not replace the real WAF-to-outbox thesis proof.

## Testing and acceptance

Implementation follows red-green-refactor cycles. Automated tests cover:

- disabled, configured, and degraded Telegram settings;
- token redaction;
- HIGH/CRITICAL eligibility and LOW/MEDIUM/Normal exclusion;
- safe plain-text formatting and path sanitization;
- Telegram 200, 429, 4xx, 5xx, connection failure, ambiguous timeout, and
  malformed response handling without live network access;
- channel-aware enqueue, claim, dispatch, deadline, retry-delay override,
  completion, and failure transitions;
- database constraints, upgrade/downgrade/re-upgrade, channel coexistence,
  claim return shape, and concurrent deduplication on disposable PostgreSQL;
- Telegram provider failure while the alert remains persisted and visible;
- all existing email, WAF ingest, notification-worker, migration, integration,
  and full backend regressions.

Docs and `.env.example` describe setup, operation, failure isolation, the
post-commit enqueue crash window, and the absence of an exactly-once guarantee.
No live Telegram delivery or hosted proof is claimed unless it is actually run
with explicit credentials and separately recorded.

## Governance decision

Primary change kind: `new feature slice`.

Secondary change kind: `boundary extraction` for channel-aware delivery.

Scope: the smallest complete backend vertical slice spanning configuration,
outbox schema/repository, provider delivery, WAF orchestration, tests, smoke,
and matching operator documentation.

Extraction outcome: one local Telegram module plus one narrow delivery boundary;
existing lifecycle ownership remains in the worker.

Contract note: the database and internal notification contracts are widened
additively while existing email behavior and V6.1 compatibility are preserved.

Convention decision: retain the current async HTTPX, Pydantic settings,
PostgreSQL RPC, structured logging, and provider fake patterns.

Validation: focused unit tests first, PostgreSQL migration/integration proof,
then the canonical full backend suite, dependency check, and `git diff --check`.

Escalation note: none remains after explicit design approval.
