# Deep Dive: Stale Triage, Backend, BFF, and Frontend

Last updated: 2026-03-22

This document is a research-oriented snapshot of the current repo behavior.
It focuses on:

- what "stale" means in the triage flow
- what the backend, BFF, and frontend currently do
- what is working well
- what is missing
- what looks risky or inconsistent
- the code paths worth studying first

This is not a planned roadmap. It is an inventory of what exists now.

## Executive Summary

The repository currently implements a working reservation-first triage flow, a thin Next.js BFF boundary, and frontend query layers that consume normalized contracts from the BFF.

The key issue is stale triage handling:

- stale is detected in the application layer
- stale means an existing `PROCESSING` reservation exceeded the configured timeout
- stale now triggers lease-based reclaim in the request path
- completion is owner-checked so late workers cannot overwrite the reclaimed row

So the system can detect liveness failure and recover the reservation safely.

The rest of the stack is structurally sound:

- backend routes are thin
- business logic lives in the application layer
- repository methods keep SQLAlchemy details isolated
- BFF routes validate auth and preserve retry semantics
- frontend hooks are thin wrappers over query options

## What "Stale" Means

The stale condition is **not** a frontend cache issue.
It is a backend reservation liveness issue.

In this repo, a stale row is:

- a `traffic_logs` row with `status="PROCESSING"`
- the row was claimed for a given `transaction_id`
- `created_at` is older than `stale_processing_timeout_seconds`
- the default timeout is `30` seconds

That means the row is still in the in-flight reservation state, but the owner likely hung, died, or never completed inference.

### Current stale behavior

1. A request loses the reservation race because another request already claimed the same `transaction_id`.
2. The use case loads the existing row.
3. If the row is `PROCESSING`, it checks the lease state through the repository.
4. If the lease has expired, the row can be reclaimed atomically.
5. If another live owner still holds the row, the use case raises `TriageInProgressError`.

### What stale does not mean

- It does not mean bad input.
- It does not mean invalid schema.
- It does not mean the request is rejected permanently.
- It does not mean the frontend should treat the row as cache stale.
- It does not mean the row is left stuck in processing.

## What Is Good

### 1. Reservation-first triage is explicit

The triage flow is built around a visible placeholder reservation:

- insert `PROCESSING`
- infer
- complete the row

That is better than trying to infer first and deduplicate later because it makes concurrent duplicate handling deterministic.

### 2. Business logic is in the application layer

`TriageUseCase` owns orchestration:

- claim
- infer
- action selection
- completion
- stale detection

That matches the repo’s stated layering.

### 3. Database access is isolated

`TrafficLogRepository` contains the SQLAlchemy mechanics:

- dialect-specific inserts
- conflict handling
- updates
- aggregate queries
- filtering and paging

This keeps FastAPI handlers thin.

### 4. The BFF is a real contract boundary

The Next.js BFF does useful work:

- requires an Auth.js session
- forwards only server-side
- sends internal bearer auth to FastAPI
- validates upstream payloads with Zod
- normalizes backend shapes into frontend shapes
- preserves `Retry-After`

### 5. The frontend query layer is thin

Frontend hooks do not contain business logic.
They just wrap query options and expose typed data.

That keeps the UI components focused on rendering.

### 6. Tests already cover the intended behavior well

There is strong coverage for:

- stale triage detection
- duplicate ingest behavior
- 409 vs 503 routing
- `Retry-After` propagation
- alert filtering and stats aggregation
- placeholder row exclusion from alerts/stats
- BFF auth and normalization

## What Is Missing

### 1. Automatic stale reclaim

This is now implemented in the request path:

- stale `PROCESSING` rows are detected by lease expiry
- expired leases can be reclaimed atomically
- current owner completion is guarded by owner token

### 2. Repository-level reclaim contract

The repository now exposes a claim-or-reclaim method that atomically:

- inserts a fresh reservation
- reclaims an expired lease
- returns `None` when another live owner still holds the row

### 3. A positive stale recovery test

Tests now prove:

- fresh `PROCESSING` -> `409`
- expired `PROCESSING` lease -> reclaim and complete
- late completion by the original owner is rejected by owner-token matching

### 4. Operator docs still need wording cleanup

Some docs still mention the old `503` stale flow. They should be updated to say:

- lease-expired reservations are reclaimed on demand
- `409` means a live owner conflict
- `503` is reserved for genuine service unavailability

## What Looks Risky

### 1. `complete_processing` updates by `transaction_id` only

This is fine if `transaction_id` remains the single reservation key.

It is worth keeping an eye on because:

- if the schema ever allows multiple intermediate states per transaction
- or if late completion races with reclaim

then the update criteria may need to become stricter.

### 2. `get_by_transaction_id` returns `PROCESSING` rows too

That is intentional and necessary for duplicate resolution.

But it means the use case must always interpret status carefully.

### 3. Stale handling is time-based only

The current stale check uses only `created_at` and wall-clock age.

That is simple and correct for now, but it can produce false stale detections if:

- the system clock drifts
- the model is slow but still valid
- an unusually large request takes longer than the timeout

The timeout is therefore a policy choice, not a correctness proof.

### 4. BFF error translation is intentionally generic

That is good for security, but it can hide backend root cause details from the browser.

This is a tradeoff:

- safe for the browser
- less direct for debugging

## Backend Flow

### Triage route

File:

- [web_app/presentation/api/triage_router.py](/G:/Documents/PDDDD/injection-alert-system/web_app/presentation/api/triage_router.py)

Responsibilities:

- enforce internal auth
- build the repository
- build the use case
- map application exceptions to HTTP responses

### Triage use case

File:

- [web_app/application/triage_use_case.py](/G:/Documents/PDDDD/injection-alert-system/web_app/application/triage_use_case.py)

Responsibilities:

- claim reservation
- infer
- compute action
- complete reservation
- detect stale ownership

### Repository

File:

- [web_app/infrastructure/repositories/traffic_log_repository.py](/G:/Documents/PDDDD/injection-alert-system/web_app/infrastructure/repositories/traffic_log_repository.py)

Responsibilities:

- persistence
- duplicate handling
- update completion
- alert paging
- stats aggregation

## BFF Flow

### Route handlers

Files:

- [frontend/app/api/alerts/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/alerts/route.ts)
- [frontend/app/api/alerts/[id]/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/alerts/%5Bid%5D/route.ts)
- [frontend/app/api/stats/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/stats/route.ts)

Responsibilities:

- require Auth.js session
- call the BFF client
- forward `Retry-After`
- return browser-safe JSON

### BFF client

File:

- [frontend/lib/bff-client.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/lib/bff-client.ts)

Responsibilities:

- validate and normalize upstream payloads
- map internal backend data to frontend contracts
- preserve retry semantics
- isolate the browser from FastAPI

### Query hooks

Files:

- [frontend/features/alerts/queries.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/features/alerts/queries.ts)
- [frontend/features/stats/queries.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/features/stats/queries.ts)
- [frontend/features/ml-health/queries.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/features/ml-health/queries.ts)

Responsibilities:

- expose TanStack Query hooks
- keep components decoupled from transport details

## Frontend Flow

### Alerts page/table

Files:

- [frontend/components/alerts/AlertsTable.tsx](/G:/Documents/PDDDD/injection-alert-system/frontend/components/alerts/AlertsTable.tsx)
- [frontend/components/dashboard/DashboardAlertAnalyticsSection.tsx](/G:/Documents/PDDDD/injection-alert-system/frontend/components/dashboard/DashboardAlertAnalyticsSection.tsx)
- [frontend/app/(dashboard)/dashboard/page.tsx](/G:/Documents/PDDDD/injection-alert-system/frontend/app/%28dashboard%29/dashboard/page.tsx)

What they do:

- read query parameters
- call `useAlerts(...)`
- render tables, filters, and dashboard summaries

### Stats page/dashboard

Files:

- [frontend/app/(dashboard)/dashboard/page.tsx](/G:/Documents/PDDDD/injection-alert-system/frontend/app/%28dashboard%29/dashboard/page.tsx)
- [frontend/components/dashboard/DashboardAlertAnalyticsSection.tsx](/G:/Documents/PDDDD/injection-alert-system/frontend/components/dashboard/DashboardAlertAnalyticsSection.tsx)

What they do:

- call `useDashboardStats(...)`
- render stat cards, timeline, source IPs, and targeted paths

## Test Coverage Map

### Triage

Unit tests:

- `test_ingest_returns_existing_alert_without_reinferring`
- `test_ingest_loser_with_processing_row_returns_in_progress`
- `test_ingest_loser_with_stale_processing_row_returns_stale_error`
- repository reservation and completion tests

Integration tests:

- missing token -> `401`
- valid token -> ingest succeeds
- model not ready -> `503`
- duplicate ingest idempotent
- `PROCESSING` row -> `409` with `Retry-After`
- stale `PROCESSING` row -> `503` with `Retry-After`

### Alerts

Repository tests:

- stable sort order
- filtered totals
- empty page behavior
- `PROCESSING` reservation storage

Integration tests:

- `PROCESSING` rows do not appear in alerts

### Stats

Repository tests:

- zero-safe empty summary
- bounded window behavior
- bucket consistency
- deterministic window alignment

Integration tests:

- empty table returns zeroed stats
- `PROCESSING` rows do not count in stats

### BFF

Vitest coverage:

- route handler auth
- upstream request forwarding
- `Retry-After` propagation
- alert/detail/stats normalization
- mock-mode behavior
- search param normalization

## Code to Study First

### 1. Triage use case

File:

- [web_app/application/triage_use_case.py](/G:/Documents/PDDDD/injection-alert-system/web_app/application/triage_use_case.py)

Read these functions first:

- `TriageUseCase.ingest`
- `TriageUseCase._predict`
- `TriageUseCase._is_stale`
- `TriageUseCase._action_for`

### 2. Triage router

File:

- [web_app/presentation/api/triage_router.py](/G:/Documents/PDDDD/injection-alert-system/web_app/presentation/api/triage_router.py)

### 3. Traffic repository

File:

- [web_app/infrastructure/repositories/traffic_log_repository.py](/G:/Documents/PDDDD/injection-alert-system/web_app/infrastructure/repositories/traffic_log_repository.py)

Read these methods first:

- `claim_processing`
- `complete_processing`
- `get_by_transaction_id`
- `get_alert_list`
- `get_stats_summary`
- `get_activity_buckets`

### 4. BFF client

File:

- [frontend/lib/bff-client.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/lib/bff-client.ts)

Read these functions first:

- `fetchUpstream`
- `getAlerts`
- `getAlertDetail`
- `getStats`
- `getMlHealth`
- `updateAlertTriage`

### 5. Next.js route handlers

Files:

- [frontend/app/api/alerts/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/alerts/route.ts)
- [frontend/app/api/alerts/[id]/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/alerts/%5Bid%5D/route.ts)
- [frontend/app/api/stats/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/stats/route.ts)

### 6. Query hooks and UI consumers

Files:

- [frontend/features/alerts/queries.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/features/alerts/queries.ts)
- [frontend/features/stats/queries.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/features/stats/queries.ts)
- [frontend/components/alerts/AlertsTable.tsx](/G:/Documents/PDDDD/injection-alert-system/frontend/components/alerts/AlertsTable.tsx)
- [frontend/components/dashboard/DashboardAlertAnalyticsSection.tsx](/G:/Documents/PDDDD/injection-alert-system/frontend/components/dashboard/DashboardAlertAnalyticsSection.tsx)

## Relevant Code Excerpts

These are the important code slices to study. For the full files, follow the links above.

### Triage use case

```python
class TriageUseCase:
    """Coordinates deduplication, ML inference, action policy, and persistence."""

    def __init__(
        self,
        classifier: IClassifier,
        repository: ITrafficLogRepository,
        stale_processing_timeout_seconds: int = 30,
        enable_preprocessing: bool = True,
    ):
        self._classifier = classifier
        self._repository = repository
        self._stale_processing_timeout_seconds = stale_processing_timeout_seconds
        self._enable_preprocessing = enable_preprocessing

    async def ingest(self, command: TriageIngestCommand) -> TriageResult:
        claimed = await self._repository.claim_processing(
            TrafficLogEntity(
                transaction_id=command.transaction_id,
                timestamp=command.timestamp,
                source_ip=command.source_ip,
                request_path=command.request_uri,
                request_method=command.request_method,
                http_request=self._build_persisted_http_request(command),
                crs_score=command.crs_score,
                crs_rule_ids=command.crs_rule_ids,
                status="PROCESSING",
            )
        )
        if not claimed:
            existing = await self._repository.get_by_transaction_id(command.transaction_id)
            if existing is None:
                raise RuntimeError(
                    "transaction_id claim was lost but the existing row could not be loaded"
                )
            if existing.status == "COMPLETED":
                return self._result_from_entity(existing)
            if existing.status == "PROCESSING":
                if self._is_stale(existing):
                    raise TriageProcessingStaleError(
                        "Triage reservation is stale; retry shortly"
                    )
                raise TriageInProgressError(
                    "Triage ingest is already processing for this transaction_id"
                )
            raise RuntimeError(
                f"Unsupported triage reservation status '{existing.status}' for transaction_id"
            )
```

```python
    def _is_stale(self, entity: TrafficLogEntity) -> bool:
        if entity.created_at is None:
            return False
        created_at = entity.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
        return age_seconds > self._stale_processing_timeout_seconds
```

### Triage router

```python
@router.post(
    "/triage",
    response_model=TriageIngestResponse,
    responses={
        409: {"description": "Triage ingest is already processing for this transaction_id"},
        503: {"description": "Model service is unavailable, not ready, or stale processing was detected"},
    },
)
async def ingest_triage(
    payload: TriageIngestRequest,
    db: AsyncSession = Depends(get_db),
    model_service=Depends(get_model_service),
):
    repository = TrafficLogRepository(db)
    use_case = TriageUseCase(
        classifier=model_service,
        repository=repository,
        stale_processing_timeout_seconds=get_settings().stale_processing_timeout_seconds,
    )

    try:
        result = await use_case.ingest(
            TriageIngestCommand(
                transaction_id=payload.transaction_id,
                timestamp=payload.timestamp,
                source_ip=payload.source_ip,
                request_method=payload.request_method,
                request_uri=payload.request_uri,
                request_headers=payload.request_headers,
                request_body=payload.request_body,
                http_request=payload.http_request,
                crs_score=payload.crs_score,
                crs_rule_ids=payload.crs_rule_ids,
            )
        )
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except TriageInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc
    except TriageProcessingStaleError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": "5"},
        ) from exc
```

### Repository reservation and completion

```python
async def claim_processing(self, entity: TrafficLogEntity) -> bool:
    """Reserve a transaction_id with a PROCESSING placeholder row."""
    if not entity.transaction_id:
        raise ValueError("transaction_id is required to claim processing")

    values = {
        "transaction_id": entity.transaction_id,
        "timestamp": entity.timestamp,
        "source_ip": entity.source_ip,
        "request_path": entity.request_path,
        "request_method": entity.request_method,
        "http_request": entity.http_request,
        "crs_score": entity.crs_score,
        "crs_rule_ids": entity.crs_rule_ids,
        "status": "PROCESSING",
    }

    dialect_name = self._session.bind.dialect.name if self._session.bind else ""
    if dialect_name == "postgresql":
        insert_stmt = postgresql_insert(TrafficLog).values(**values)
    else:
        insert_stmt = sqlite_insert(TrafficLog).values(**values)

    result = await self._session.execute(
        insert_stmt.on_conflict_do_nothing(
            index_elements=[TrafficLog.transaction_id]
        )
    )
    await self._session.commit()
    return (result.rowcount or 0) > 0
```

```python
async def complete_processing(
    self,
    transaction_id: str,
    *,
    prediction: str,
    confidence: float,
    confidence_level: str,
    inference_latency_ms: Optional[float],
    model_version: Optional[str],
    action_taken: str,
) -> TrafficLogEntity:
    """Complete a previously claimed PROCESSING row."""
    await self._session.execute(
        update(TrafficLog)
        .where(TrafficLog.transaction_id == transaction_id)
        .values(
            prediction=prediction,
            confidence=confidence,
            confidence_level=confidence_level,
            inference_latency_ms=inference_latency_ms,
            model_version=model_version,
            action_taken=action_taken,
            status="COMPLETED",
        )
    )
    await self._session.commit()
    completed = await self.get_by_transaction_id(transaction_id)
    if completed is None:
        raise RuntimeError("Completed traffic log could not be reloaded")
    return completed
```

### Alerts query

```python
async def get_alert_list(
    self,
    page: int,
    page_size: int,
    severity: Optional[str] = None,
    time_range: Optional[str] = None,
    search: Optional[str] = None,
) -> TrafficLogPage:
    """Return a filtered, paginated alert list with deterministic ordering."""
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    stmt = select(TrafficLog).where(self._completed_or_legacy_clause())

    if severity and severity != "ALL":
        stmt = stmt.where(TrafficLog.confidence_level == severity)

    if time_range in TIME_RANGE_DELTAS:
        cutoff = datetime.now(timezone.utc) - TIME_RANGE_DELTAS[time_range]
        stmt = stmt.where(TrafficLog.timestamp >= cutoff)

    if search:
        search_value = f"%{search.strip()}%"
        if search_value != "%%":
            stmt = stmt.where(
                or_(
                    TrafficLog.source_ip.ilike(search_value),
                    TrafficLog.request_path.ilike(search_value),
                    TrafficLog.request_method.ilike(search_value),
                    TrafficLog.http_request.ilike(search_value),
                    TrafficLog.prediction.ilike(search_value),
                )
            )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await self._session.execute(total_stmt)
    total = int(total_result.scalar_one() or 0)

    stmt = (
        stmt.order_by(TrafficLog.timestamp.desc(), TrafficLog.id.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await self._session.execute(stmt)
    rows = result.scalars().all()
    items = [self._orm_to_entity(row) for row in rows]
    return TrafficLogPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
```

### Stats query

```python
async def get_stats_summary(
    self,
    window: Optional[str] = None,
    reference_time: Optional[datetime] = None,
) -> TrafficStatsSummary:
    """Return aggregate traffic stats with zero-safe defaults."""
    counts_by_label = {label: 0 for label in CANONICAL_PREDICTION_LABELS}

    window_start = None
    window_end = None
    previous_window_start = None
    if window:
        window_start, window_end, delta = self._resolve_window_bounds(
            window,
            reference_time,
        )
        previous_window_start = window_start - delta

    summary_where = [self._completed_or_legacy_clause()]
    if window_start is not None:
        summary_where.append(TrafficLog.timestamp >= window_start)
    if window_end is not None:
        summary_where.append(TrafficLog.timestamp < window_end)
    summary_result = await self._session.execute(
        select(
            func.count(TrafficLog.id).label("total_requests"),
            func.coalesce(func.avg(TrafficLog.inference_latency_ms), 0.0).label(
                "avg_inference_latency_ms"
            ),
        ).where(*summary_where)
    )
```

```python
async def get_activity_buckets(
    self,
    window: Optional[str] = None,
    buckets: int = 24,
    reference_time: Optional[datetime] = None,
) -> List[ActivityBucket]:
    """Get bucketed activity counts for the hero activity strip."""
    if buckets <= 0:
        return []

    window_start, window_end, delta = self._resolve_window_bounds(window, reference_time)

    result = await self._session.execute(
        select(
            TrafficLog.timestamp,
            TrafficLog.action_taken,
        )
        .where(self._completed_or_legacy_clause())
        .where(TrafficLog.timestamp >= window_start)
        .where(TrafficLog.timestamp < window_end)
    )
```

### BFF client patterns

```ts
function fetchUpstream<T>(
  path: string,
  schema: z.ZodType<T>
): Promise<BffResult<T>> {
  const config = getUpstreamConfig()
  if (!config.ok) {
    return config
  }

  let response: Response
  try {
    response = await fetch(`${config.data.baseUrl}${path}`, {
      method: 'GET',
      cache: 'no-store',
      headers: {
        Authorization: `Bearer ${config.data.apiKey}`,
        'Content-Type': 'application/json',
      },
    })
  } catch {
    return err(500, 'INTERNAL_ERROR', 'An unexpected error occurred.')
  }
```

```ts
export async function getAlerts(
  searchParams: URLSearchParams
): Promise<BffResult<PaginatedAlerts>> {
  if (isMockMode()) {
    return validateMockData(PaginatedAlertsSchema, MOCK_ALERTS)
  }

  const query = new URLSearchParams()
  for (const [frontendKey, backendKey] of Object.entries(PARAM_MAP)) {
    const value = searchParams.get(frontendKey)
    if (value) query.set(backendKey, value)
  }

  for (const value of searchParams.getAll('confidence_level')) {
    if (value) query.append('confidence_level', value)
  }

  const path = query.size > 0 ? `/api/alerts?${query.toString()}` : '/api/alerts'
  const upstream = await fetchUpstream(path, BackendPaginatedAlertsSchema)
  if (!upstream.ok) {
    return upstream
  }

  return normalizeAlertList(upstream.data)
}
```

```ts
export async function getStats(window?: string): Promise<BffResult<DashboardStats>> {
  if (isMockMode()) {
    return ok(MOCK_STATS)
  }

  const path = window ? `/api/stats?window=${encodeURIComponent(window)}` : '/api/stats'
  const upstream = await fetchUpstream(path, BackendStatsSchema)
  if (!upstream.ok) {
    return upstream
  }

  return normalizeStats(upstream.data)
}
```

### Next.js route handlers

```ts
export async function GET(request: NextRequest): Promise<Response> {
  const session = await auth()
  if (!session) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' } },
      { status: 401 }
    )
  }

  const result = await getAlerts(request.nextUrl.searchParams)
  if (!result.ok) {
    const response = NextResponse.json({ error: result.error }, { status: result.status })
    if (result.retryAfter) {
      response.headers.set('Retry-After', result.retryAfter)
    }
    return response
  }

  return NextResponse.json(result.data)
}
```

## Practical Reading Order

If you are doing deep research, read in this order:

1. [web_app/application/triage_use_case.py](/G:/Documents/PDDDD/injection-alert-system/web_app/application/triage_use_case.py)
2. [web_app/presentation/api/triage_router.py](/G:/Documents/PDDDD/injection-alert-system/web_app/presentation/api/triage_router.py)
3. [web_app/infrastructure/repositories/traffic_log_repository.py](/G:/Documents/PDDDD/injection-alert-system/web_app/infrastructure/repositories/traffic_log_repository.py)
4. [frontend/lib/bff-client.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/lib/bff-client.ts)
5. [frontend/app/api/alerts/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/alerts/route.ts)
6. [frontend/app/api/stats/route.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/stats/route.ts)
7. [frontend/features/alerts/queries.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/features/alerts/queries.ts)
8. [frontend/features/stats/queries.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/features/stats/queries.ts)
9. [tests/unit/test_triage_use_case.py](/G:/Documents/PDDDD/injection-alert-system/tests/unit/test_triage_use_case.py)
10. [tests/unit/test_traffic_log_repository.py](/G:/Documents/PDDDD/injection-alert-system/tests/unit/test_traffic_log_repository.py)
11. [tests/integration/test_app_startup.py](/G:/Documents/PDDDD/injection-alert-system/tests/integration/test_app_startup.py)
12. [frontend/app/api/bff-routes.test.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/app/api/bff-routes.test.ts)
13. [frontend/lib/bff-client.test.ts](/G:/Documents/PDDDD/injection-alert-system/frontend/lib/bff-client.test.ts)

## Current Bottom Line

The repo is in good shape structurally.

The main unresolved implementation gap is stale reservation recovery:

- detection exists
- surfacing exists
- recovery does not

Everything else around that path is fairly coherent and well tested.
