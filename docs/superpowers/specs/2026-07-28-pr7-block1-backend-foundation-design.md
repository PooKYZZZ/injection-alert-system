# PR7 Block 1 Backend Foundation Design

## Goal

Build the additive backend source of truth for temporary CRITICAL WAF recommendations: durable effective state, atomic lifecycle mutation, a consistent snapshot, and an authenticated controlled-local snapshot endpoint. Block 2 runtime activation remains out of scope.

## Architecture

The existing `enforcement_recommendations` history remains immutable with respect to PR7 lifecycle. A new effective-state table references recommendation history and stores only the rows that became ACTIVE or their terminal provenance. A singleton control row owns the ordinary BIGINT desired-state revision. Mutation code runs inside PostgreSQL `READ COMMITTED` transactions and always locks the singleton row first; snapshot code uses a separate `REPEATABLE READ READ ONLY` transaction.

The application layers remain `domain -> application -> infrastructure -> presentation`. The domain owns lifecycle/value validation and canonical state representation, the application owns mutation/snapshot orchestration, infrastructure owns SQLAlchemy/PostgreSQL persistence, and the route owns authentication, response shaping, and safe HTTP errors.

## Data flow

`verified CRITICAL recommendation -> mutation use case -> singleton lock -> recommendation/effective-state transaction -> revisioned ACTIVE rows -> repeatable-read snapshot -> authenticated JSON endpoint`.

Source IPs use the existing canonicalization helper, mapped IPv6 collapses to IPv4, and malformed values are rejected. Snapshot checksums hash only the normative authoritative state object with explicit ordering and serialization; `generated_at` is excluded.

## Error handling and boundaries

Invalid lifecycle transitions, malformed addresses, invalid datetimes, capacity rejection, and oversized snapshots are typed safe failures. Authentication uses constant-time bearer comparison and never logs the secret. The endpoint is 404 when the accepted controlled-local mode is disabled and 503 for safe snapshot/database failure. No real Supabase migration, WAF rule rendering, synchronizer, reload, activation, or hosted/production enforcement is added.

## Testing

PostgreSQL is authoritative for migration constraints, partial uniqueness, locking, isolation, read-only transactions, concurrency, and rollback. Unit tests cover canonicalization, lifecycle/checksum validators, and HTTP authentication/size behavior. Migration tests cover upgrade, downgrade, re-upgrade, singleton initialization, constraints, and one-head integrity. Existing recommendation, PR5, and PR6 tests are rerun after the focused Block 1 suite.
