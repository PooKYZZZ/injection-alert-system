# CyberTrace — Full-Stack Implementation Plan

> **Version 2** — Updated after research audit against 2025 best practices for Next.js 15, TanStack Query v5, FastAPI async, Tailwind v4, and Anthropic multi-agent patterns.

**Project:** CyberTrace WAF-ML Security Dashboard  
**Stack:**
- Frontend: Next.js 15 · React 19 · Tailwind v4 · Recharts 3 · Motion · TanStack Query v5 · Zustand
- BFF: Next.js Route Handlers (TypeScript) in `frontend/app/api/*`
- Backend: FastAPI (Python) · SQLAlchemy async · PostgreSQL
- ML: DistilBERT v3 inference service (proxied through backend)

**Goal:** Close the design gap between the current live dashboard and the Google AI Studio reference version — covering all three layers: backend aggregation, BFF normalization, and frontend rendering.

---

## Priority System

- 🔴 **P0 — Critical bug** — broken behavior or semantic incorrectness. Fix before anything else.
- 🟠 **P1 — High impact** — visible on every page load, large improvement for minimal effort.
- 🟡 **P2 — Medium impact** — noticeable improvement, moderate effort.
- 🟢 **P3 — Polish** — small refinements, do last.

---

## What Each Layer Needs to Do

Before diving into tasks, here is the full picture of what is broken across the stack and which layer owns the fix:

| Problem visible on screen | Root cause layer | Fix layer |
|---|---|---|
| KPI delta ("↑ +3 vs prev 6h") not showing | Backend not returning prev window counts | Backend → BFF → Frontend |
| AVG ML CONFIDENCE shows dash | Backend `avg_confidence` returning `null` | Backend + BFF null handling |
| FALSE POSITIVE RATE shows "Not available" | Backend not computing or returning FPR | Backend → BFF schema → Frontend |
| Top Source IPs empty on fresh load | `top_source_ips` is `.optional()` in BFF schema, may be absent | Backend always returning it → BFF |
| Top Targeted Paths empty on fresh load | Same as above | Backend always returning it → BFF |
| Chart flat line on quiet windows | Frontend zero-state not handled | Frontend only |
| Chart has no area fills | Frontend Recharts config | Frontend only |
| KPI cards show "Calculating..." | Frontend loading state design | Frontend only |
| Token color bug (blocked = green) | Frontend globals.css | Frontend only |
| Font sizes too small | Frontend globals.css | Frontend only |
| No live polling — dashboard goes stale | TanStack Query missing `refetchInterval` | Frontend BFF query hook |
| No error boundary — 500s show blank panels | Missing `QueryErrorResetBoundary` | Frontend component tree |
| Time window switch flashes skeleton | Missing `placeholderData: keepPreviousData` | Frontend query hook |

---

## Phase 0: Backend — Add Missing Data to Stats Response

> The BFF can only normalize what the backend sends. These backend changes unlock everything in Phase 1 (BFF) and Phase 2 (KPI cards).

---

### 0.1 — Add previous-window counts to `get_stats_summary` ✅ 2026-03-22 02:28 PHT

**File:** `web_app/infrastructure/repositories/traffic_log_repository.py`

**Problem:** `get_stats_summary` returns counts for the current window only. There is no `previous_blocked_count`, `previous_allowed_count`, or `previous_throttled_count`. Without these the BFF and frontend cannot compute the delta indicators ("↑ +3 vs prev 6h") that are the primary signal on the KPI cards.

**How it works:** For a given window (e.g. `6h`), the "previous window" is the identical duration immediately before it — i.e. 6h ago to 12h ago. You run the same query twice with different time bounds.

**Implementation:**

```python
# web_app/infrastructure/repositories/traffic_log_repository.py

from datetime import datetime, timedelta, timezone
from typing import Optional

def _window_to_timedelta(window: Optional[str]) -> Optional[timedelta]:
    """Convert a window string to a timedelta. Returns None for all-time."""
    mapping = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }
    return mapping.get(window) if window else None


async def _get_counts_for_range(
    self,
    session: AsyncSession,
    start: Optional[datetime],
    end: Optional[datetime],
) -> dict:
    """Run a single count query for blocked/allowed/throttled in a time range."""
    filters = []
    if start:
        filters.append(TrafficLog.timestamp >= start)
    if end:
        filters.append(TrafficLog.timestamp < end)

    result = await session.execute(
        select(
            func.count().label("total"),
            func.sum(case((TrafficLog.action_taken == "BLOCKED", 1), else_=0)).label("blocked"),
            func.sum(case((TrafficLog.action_taken == "ALLOWED", 1), else_=0)).label("allowed"),
            func.sum(case((TrafficLog.action_taken == "THROTTLED", 1), else_=0)).label("throttled"),
        ).where(*filters)
    )
    row = result.one()
    return {
        "total": row.total or 0,
        "blocked": row.blocked or 0,
        "allowed": row.allowed or 0,
        "throttled": row.throttled or 0,
    }


async def get_stats_summary(self, window: Optional[str] = None) -> TrafficStatsSummary:
    import asyncio
    now = datetime.now(timezone.utc)
    delta = _window_to_timedelta(window)

    current_start = (now - delta) if delta else None

    if delta:
        prev_end = current_start
        prev_start = prev_end - delta
        # Run both queries in parallel — do NOT await sequentially, that blocks the event loop
        current, previous = await asyncio.gather(
            self._get_counts_for_range(self.session, start=current_start, end=None),
            self._get_counts_for_range(self.session, start=prev_start, end=prev_end),
        )
    else:
        current = await self._get_counts_for_range(self.session, start=None, end=None)
        previous = None  # No previous window for all-time queries

    # ... rest of existing aggregation (avg_confidence, attack distribution, etc.) ...

    return TrafficStatsSummary(
        # existing fields
        total_requests=current["total"],
        blocked_count=current["blocked"],
        allowed_count=current["allowed"],
        throttled_count=current["throttled"],
        # NEW fields
        prev_blocked_count=previous["blocked"] if previous else None,
        prev_allowed_count=previous["allowed"] if previous else None,
        prev_throttled_count=previous["throttled"] if previous else None,
        prev_total_requests=previous["total"] if previous else None,
        # ... other existing fields
    )
```

**Update the Pydantic model:**

```python
# web_app/domain/models.py or wherever TrafficStatsSummary is defined

class TrafficStatsSummary(BaseModel):
    total_requests: int
    blocked_count: int
    allowed_count: int
    throttled_count: int
    avg_confidence: Optional[float]

    # NEW — previous window for delta computation
    prev_total_requests: Optional[int] = None
    prev_blocked_count: Optional[int] = None
    prev_allowed_count: Optional[int] = None
    prev_throttled_count: Optional[int] = None

    # ... rest of existing fields
```

**Update the FastAPI response model:**

```python
# web_app/presentation/api/routes.py

class StatsResponse(BaseModel):
    # existing
    total_requests: int
    blocked_count: int
    allowed_count: int
    throttled_count: Optional[int]
    avg_confidence: Optional[float]

    # NEW
    prev_total_requests: Optional[int] = None
    prev_blocked_count: Optional[int] = None
    prev_allowed_count: Optional[int] = None
    prev_throttled_count: Optional[int] = None
```

---

### 0.2 — Fix `avg_confidence` returning null ✅ 2026-03-22 02:28 PHT

**File:** `web_app/infrastructure/repositories/traffic_log_repository.py`

**Problem:** The BFF schema has `avg_confidence: z.number().nullable()` which means it is already expected to sometimes be null. When it is null, the frontend shows a dash. This happens when there are no rows in the current window — the SQL `AVG()` over an empty set returns NULL.

**Fix:** Return 0.0 instead of NULL when there are no rows, or return the all-time average as a fallback:

```python
# In your stats aggregation query
avg_confidence_result = await session.execute(
    select(func.avg(TrafficLog.confidence)).where(*window_filters)
)
raw_avg = avg_confidence_result.scalar()

# Use 0.0 as fallback instead of None — the frontend can distinguish "no data" by
# checking total_requests == 0 rather than by avg_confidence being null
avg_confidence = float(raw_avg) if raw_avg is not None else 0.0
```

**Alternatively**, if you want to preserve the null semantics (null means "no requests processed"), make the frontend handle it gracefully rather than showing a dash — see Phase 2.3 in the BFF section.

---

### 0.3 — Add false positive rate to the stats response ✅ 2026-03-22 02:28 PHT

**Problem:** FALSE POSITIVE RATE currently shows "Not available" because the backend does not compute or return it. False positive rate = requests classified as attack but actually benign (i.e., action was ALLOWED but prediction was an attack label).

**Implementation:**

```python
# In get_stats_summary — add this query alongside the existing aggregations

false_positive_result = await session.execute(
    select(func.count()).where(
        *window_filters,
        TrafficLog.action_taken == "ALLOWED",
        TrafficLog.prediction != "Normal",   # classified as attack but allowed through
    )
)
false_positive_count = false_positive_result.scalar() or 0

# FPR = false positives / total requests (expressed as percentage)
false_positive_rate = (
    round((false_positive_count / current["total"]) * 100, 2)
    if current["total"] > 0
    else 0.0
)
```

**Add to Pydantic model and StatsResponse:**

```python
false_positive_rate: float = 0.0   # percentage, e.g. 0.8 means 0.8%
false_positive_count: int = 0
```

> **Note:** Validate this definition of false positive with your team. In some WAF contexts, FPR is computed differently depending on whether you have ground-truth labels. The formula above uses action=ALLOWED + prediction=attack as a proxy. If your system has a manual triage outcome field, use that instead.

---

### 0.4 — Guarantee `top_source_ips` and `top_targeted_paths` are always returned ✅ 2026-03-22 02:28 PHT

**Problem:** Both fields are `.optional()` in the BFF Zod schema, meaning the backend may omit them. When they are absent the panels show the empty state even when there is real data. The backend should always return these arrays — empty array `[]` if no data, never absent.

**File:** `web_app/presentation/api/routes.py`

```python
# In the StatsResponse model — change Optional[List] to List with default
class StatsResponse(BaseModel):
    # ...
    top_source_ips: List[SourceIPEntry] = []         # was Optional
    top_targeted_paths: List[TargetPathEntry] = []   # was Optional
```

**File:** `web_app/infrastructure/repositories/traffic_log_repository.py`

```python
# In get_stats_summary — ensure the query always returns a list
top_ips_result = await session.execute(
    select(TrafficLog.source_ip, func.count().label("count"))
    .where(*window_filters)
    .group_by(TrafficLog.source_ip)
    .order_by(desc("count"))
    .limit(10)
)
top_source_ips = [
    {"ip": row.source_ip, "count": row.count, "action": ...}
    for row in top_ips_result.all()
]
# This always returns a list — [] if no rows, never None
```

---

### 0.5 — Add `high_alert_count` as a distinct field ✅ 2026-03-22 02:34 PHT

**Problem:** The HIGH ALERTS KPI card is presumably derived from `counts_by_label` on the frontend by summing non-Normal predictions. This is fragile — if a new attack label is added to the ML model, the frontend won't pick it up automatically.

**Fix:** Have the backend explicitly compute and return `high_alert_count`:

```python
# In get_stats_summary
high_alert_count = sum(
    count for label, count in counts_by_label.items()
    if label != "Normal"
)

# Add to StatsResponse
high_alert_count: int = 0
```

Then the frontend KPI card just reads `stats.high_alert_count` directly instead of re-computing it.

---

## Phase 1: BFF — Update Schema and Normalization

> The BFF sits between FastAPI and the frontend. Its job is to validate, normalize, and re-shape the backend response into exactly what the frontend needs. After Phase 0 adds new fields to the backend, Phase 1 surfaces them through the BFF.

---

### 1.1 — Add previous-window fields to `BackendStatsSchema` ✅ 2026-03-22 02:28 PHT

**File:** `frontend/lib/bff-client.ts`

```ts
const BackendStatsSchema = z.object({
  // existing fields
  total_requests: z.number(),
  counts_by_label: z.object({
    'SQL Injection': z.number(),
    'Code Injection': z.number(),
    'Other Attacks': z.number(),
    Normal: z.number(),
  }),
  avg_inference_latency_ms: z.number(),
  blocked_count: z.number(),
  allowed_count: z.number(),
  throttled_count: z.number().optional(),
  avg_confidence: z.number().nullable(),
  activity_buckets: z.array(BackendActivityBucketSchema),
  attack_distribution: z.record(z.string(), z.number()).optional(),
  top_source_ips: z.array(BackendSourceIPSchema).optional(),
  top_targeted_paths: z.array(BackendTargetPathSchema).optional(),

  // NEW — previous window fields (all optional, absent on all-time queries)
  prev_total_requests: z.number().optional(),
  prev_blocked_count: z.number().optional(),
  prev_allowed_count: z.number().optional(),
  prev_throttled_count: z.number().optional(),

  // NEW — from Phase 0.3
  false_positive_rate: z.number().optional(),
  false_positive_count: z.number().optional(),

  // NEW — from Phase 0.5
  high_alert_count: z.number().optional(),
})
```

---

### 1.2 — Update `DashboardStats` frontend type to include new fields ✅ 2026-03-22 02:28 PHT

**File:** `frontend/lib/bff-client.ts` (or wherever `DashboardStats` is typed)

```ts
export type DashboardStats = {
  // existing
  totalRequests: number
  blockedCount: number
  allowedCount: number
  throttledCount: number
  avgConfidence: number | null
  activityBuckets: ActivityBucket[]
  attackDistribution: Record<string, number>
  topSourceIPs: SourceIP[]
  topTargetedPaths: TargetPath[]

  // NEW
  prevTotalRequests: number | null
  prevBlockedCount: number | null
  prevAllowedCount: number | null
  prevThrottledCount: number | null
  falsePositiveRate: number | null
  falsePositiveCount: number | null
  highAlertCount: number
}
```

---

### 1.3 — Update normalization to map new fields ✅ 2026-03-22 02:28 PHT

**File:** `frontend/lib/bff-client.ts` — in the normalization step where you convert the backend payload to `DashboardStats`

```ts
// Add to your existing normalization:
const normalized: DashboardStats = {
  // ... existing fields ...

  // Previous window
  prevTotalRequests: payload.prev_total_requests ?? null,
  prevBlockedCount: payload.prev_blocked_count ?? null,
  prevAllowedCount: payload.prev_allowed_count ?? null,
  prevThrottledCount: payload.prev_throttled_count ?? null,

  // False positive rate
  falsePositiveRate: payload.false_positive_rate ?? null,
  falsePositiveCount: payload.false_positive_count ?? null,

  // High alert count — fall back to summing counts_by_label if backend doesn't send it yet
  highAlertCount:
    payload.high_alert_count ??
    Object.entries(payload.counts_by_label)
      .filter(([label]) => label !== 'Normal')
      .reduce((sum, [, count]) => sum + count, 0),

  // Fix: change top_source_ips and top_targeted_paths from optional to always-present
  topSourceIPs: payload.top_source_ips ?? [],
  topTargetedPaths: payload.top_targeted_paths ?? [],
}
```

---

### 1.4 — Fix `top_source_ips` and `top_targeted_paths` Zod schema ✅ 2026-03-22 02:28 PHT

**File:** `frontend/lib/bff-client.ts`

After Phase 0.4 ensures the backend always returns these arrays, update the Zod schema to reflect that they are no longer optional:

```ts
// Change from:
top_source_ips: z.array(BackendSourceIPSchema).optional(),
top_targeted_paths: z.array(BackendTargetPathSchema).optional(),

// Change to:
top_source_ips: z.array(BackendSourceIPSchema).default([]),
top_targeted_paths: z.array(BackendTargetPathSchema).default([]),
```

Using `.default([])` instead of `.optional()` means Zod will coerce a missing field to an empty array rather than `undefined`, which prevents the empty-state panels from triggering when data is genuinely present but temporarily slow.

---

### 1.5 — Handle `avg_confidence` null gracefully in normalization ✅ 2026-03-22 02:28 PHT

**File:** `frontend/lib/bff-client.ts`

Right now if `avg_confidence` is null, it passes through as null and the frontend shows a dash. Add a fallback in the normalization:

```ts
// If avg_confidence is null AND total_requests > 0, something is wrong upstream.
// If avg_confidence is null AND total_requests === 0, it's a genuine empty window.
avgConfidence: payload.avg_confidence,
avgConfidenceIsEmpty: payload.total_requests === 0,  // NEW flag — tells frontend "this is empty, not broken"
```

Add `avgConfidenceIsEmpty: boolean` to the `DashboardStats` type. The frontend card then uses this flag to show "No traffic in window" instead of a dash.

---

### 1.6 — Add `blockRate` to normalization ✅ 2026-03-22 02:28 PHT

**File:** `frontend/lib/bff-client.ts`

The BLOCKED KPI card shows a progress bar representing the block rate. Compute it in the BFF normalization so the frontend doesn't have to:

```ts
blockRate:
  payload.total_requests > 0
    ? Math.round((payload.blocked_count / payload.total_requests) * 100)
    : 0,
```

Add `blockRate: number` to `DashboardStats`.

---

### 1.7 — Fix `isPending` usage and add `refetchInterval` + `placeholderData` ✅ 2026-03-22 02:28 PHT

**File:** `frontend/features/stats/queries.ts`

**Problems identified from research audit:**

**Problem 1 — TanStack Query v5 API mismatch:** The plan's skeleton loader code likely uses `isLoading`. In TanStack Query v5, `isLoading` is replaced by `isPending` for queries that have never successfully resolved. Using `isLoading` in v5 returns `false` even when data is loading for the first time if the query has a previous cache entry — meaning your skeleton never shows on window switch. Fix every skeleton condition from `isLoading` to `isPending`.

**Problem 2 — No live polling:** A WAF security dashboard showing live attack data must auto-refresh. `staleTime: 30_000` only controls when the query becomes stale — it does not trigger a background refetch. Without `refetchInterval`, the dashboard goes stale after 30s and never updates until the user switches tabs or manually refreshes.

**Problem 3 — Window switch flashes skeleton:** When the user switches from 6h to 24h, TanStack Query discards the cached data and shows a skeleton while the new window loads. `placeholderData` keeps the previous window's data visible during the transition so the dashboard never flashes empty.

```ts
// frontend/features/stats/queries.ts
export function statsOptions(window?: string) {
  return queryOptions<DashboardStats>({
    queryKey: ['stats', window ?? 'all'],
    queryFn: async () => {
      const url = window ? `/api/stats?window=${window}` : '/api/stats'
      const r = await fetch(url)
      if (!r.ok) throw new Error(`/api/stats responded with ${r.status}`)
      return r.json()
    },
    staleTime: 15_000,         // data is fresh for 15s
    refetchInterval: 15_000,   // background refetch every 15s — keeps dashboard live
    placeholderData: (prev) => prev,  // keep previous window data during transition
  })
}
```

**Update all skeleton conditions in components:**
```tsx
// WRONG (v4 pattern — broken in v5 on window switch)
const { data, isLoading } = useQuery(statsOptions(window))
if (isLoading) return <Skeleton />

// CORRECT (v5 pattern)
const { data, isPending } = useQuery(statsOptions(window))
if (isPending) return <Skeleton />
```

---

### 1.8 — Add `QueryErrorResetBoundary` and error UI to dashboard panels ✅ 2026-03-22 02:34 PHT

**File:** Dashboard page component and panel components

**Problem:** The plan handles loading states and empty states but has no error state. When the BFF returns a 500, or the FastAPI backend times out, TanStack Query enters an error state and `data` is `undefined`. Without an error boundary, panels render blank or crash silently.

**Implementation:**

```tsx
// In your dashboard page or panel wrapper
import { QueryErrorResetBoundary } from '@tanstack/react-query'
import { ErrorBoundary } from 'react-error-boundary'

function PanelErrorFallback({ error, resetErrorBoundary }: { error: Error, resetErrorBoundary: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-6">
      <p className="text-[11px] text-[var(--color-severity-high-text)]">Failed to load</p>
      <p className="text-[10px] text-[var(--color-text-muted)]">{error.message}</p>
      <button
        onClick={resetErrorBoundary}
        className="text-[11px] text-[var(--color-accent-blue)] hover:underline mt-1"
      >
        Retry
      </button>
    </div>
  )
}

// Wrap each panel independently so one failure doesn't kill the whole dashboard
<QueryErrorResetBoundary>
  {({ reset }) => (
    <ErrorBoundary onReset={reset} FallbackComponent={PanelErrorFallback}>
      <TopSourceIPsPanel />
    </ErrorBoundary>
  )}
</QueryErrorResetBoundary>
```

**Note:** Wrap each panel independently. Do not wrap the entire dashboard in one boundary — a single boundary means one panel failure takes down all panels.

---

## Phase 2: Frontend — Fix the Token System (globals.css)

> These are foundational. Every component inherits from here. Fix these before touching any components.

---

### 2.1 — Fix the `--color-status-blocked` semantic bug ✅ 2026-03-22 02:34 PHT

**File:** `frontend/app/globals.css`

**Problem:** `--color-status-blocked` resolves to `--color-severity-safe-accent` which is `#4ade80` — bright green. This is a live semantic inversion — blocked events render green.

```css
/* Current — WRONG */
--color-status-blocked: var(--color-severity-safe-accent);

/* Fix */
--color-status-blocked: var(--color-severity-high-accent); /* #ef4444 — red */
```

**Verify:** `grep -rn "color-status-blocked" app/ components/` then confirm every usage now renders red.

> **Tailwind v4 note:** Because you define tokens in `@theme`, Tailwind v4 auto-generates utility classes from them. `--color-severity-high-accent` in `@theme` means you can write `text-severity-high-accent` directly instead of `text-[var(--color-severity-high-accent)]`. Both work, but the generated utility is cleaner and more scannable. Prefer the generated utility wherever the token name is self-descriptive.

---

### 2.2 — Fix font size minimums ✅ 2026-03-22 02:34 PHT

**File:** `frontend/app/globals.css`

```css
/* Current — too small */
--font-size-label: 9px;
--font-size-micro: 9px;

/* Fix */
--font-size-label: 11px;
--font-size-micro: 10px;

/* Add missing scale */
--font-size-body: 13px;
--font-size-sm: 12px;
--font-size-xs: 11px;
--font-size-2xs: 10px;
--font-size-kpi: 28px;
--font-size-kpi-sm: 22px;
--font-size-section-head: 11px;
```

---

### 2.3 — Fix `--color-primary` conflict ✅ 2026-03-22 02:34 PHT

**File:** `frontend/app/globals.css`

```css
/* Current — primary action color is same as highest threat severity */
--color-primary: var(--color-severity-high-accent);

/* Fix — decouple action colors from severity semantics */
--color-primary: var(--color-accent-purple);
--color-primary-bg: var(--color-accent-purple-bg);
--color-primary-dark: #c4b5fd;
```

---

### 2.4 — Add missing semantic tokens ✅ 2026-03-22 02:34 PHT

**File:** `frontend/app/globals.css`

```css
/* Chart colors */
--color-chart-blocked: var(--color-severity-high-accent);
--color-chart-throttled: var(--color-accent-amber);
--color-chart-allowed: var(--color-severity-safe-accent);

/* Skeleton */
--color-skeleton-base: var(--color-bg-elevated);
--color-skeleton-shine: var(--color-bg-panel);

/* Delta indicators */
--color-delta-positive: var(--color-severity-high-accent);   /* going up = worse */
--color-delta-negative: var(--color-severity-safe-accent);   /* going down = better */
--color-delta-neutral: var(--color-text-muted);

/* Empty state */
--color-empty-state-icon: var(--color-text-muted);
--color-empty-state-text: var(--color-text-secondary);

/* KPI card borders */
--color-kpi-border-high: var(--color-severity-high-border);
--color-kpi-border-blocked: var(--color-severity-blocked-border);
--color-kpi-border-safe: var(--color-severity-safe-border);
--color-kpi-border-default: var(--color-bg-elevated);
```

---

### 2.5 — Expose skeleton as a reusable utility class ✅ 2026-03-22 02:34 PHT

**File:** `frontend/app/globals.css`

```css
@layer utilities {
  .skeleton {
    background: var(--color-skeleton-base);
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: 4px;
  }
}
```

---

## Phase 3: Frontend — KPI Stat Cards

> After Phase 0 and Phase 1, the frontend now has `prevBlockedCount`, `falsePositiveRate`, `highAlertCount`, and `blockRate` available. This phase wires them into the cards.

---

### 3.1 — Add delta indicators to every KPI card ✅ 2026-03-22 02:34 PHT

**File:** Your KPI card component

Now that `prevBlockedCount`, `prevAllowedCount`, `prevThrottledCount` are available on `DashboardStats`, compute and render deltas:

```tsx
interface KpiCardProps {
  label: string
  value: number | string
  previousValue?: number | null
  colorScheme: 'high' | 'blocked' | 'safe' | 'benign' | 'neutral'
  subtext?: string
  isLoading?: boolean
  deltaInverted?: boolean   // true for ALLOWED — going up is good
  progressBar?: number      // 0–100, renders a thin bar below the number
}

function computeDelta(current: number, previous: number | null | undefined) {
  if (previous == null) return null
  const diff = current - previous
  const direction: 'up' | 'down' | 'neutral' =
    diff > 0 ? 'up' : diff < 0 ? 'down' : 'neutral'
  return { diff: Math.abs(diff), direction }
}

// In the card JSX — delta line below the main number:
const delta = computeDelta(value as number, previousValue)
const deltaIsGood =
  (delta?.direction === 'down' && !deltaInverted) ||
  (delta?.direction === 'up' && deltaInverted)

{delta && delta.direction !== 'neutral' && (
  <p className={cn(
    'text-[11px] font-medium mt-1 flex items-center gap-1',
    deltaIsGood
      ? 'text-[var(--color-delta-negative)]'
      : 'text-[var(--color-delta-positive)]'
  )}>
    {delta.direction === 'up' ? '↑' : '↓'}
    {delta.diff} vs prev window
  </p>
)}
```

**Wire up in the dashboard:**

```tsx
// HIGH ALERTS card
<KpiCard
  label="High Alerts"
  value={stats.highAlertCount}
  previousValue={
    stats.prevTotalRequests != null
      ? (stats.prevTotalRequests - (stats.prevAllowedCount ?? 0))
      : null
  }
  colorScheme="high"
  deltaInverted={false}   // up = bad
/>

// BLOCKED card
<KpiCard
  label="Blocked"
  value={stats.blockedCount}
  previousValue={stats.prevBlockedCount}
  colorScheme="blocked"
  subtext={`${stats.blockRate}% block rate`}
  progressBar={stats.blockRate}
  deltaInverted={false}   // up = bad
/>

// ALLOWED card
<KpiCard
  label="Allowed"
  value={stats.allowedCount}
  previousValue={stats.prevAllowedCount}
  colorScheme="safe"
  subtext="Benign / LOW conf"
  deltaInverted={true}    // up = good
/>

// THROTTLED card
<KpiCard
  label="Throttled"
  value={stats.throttledCount ?? 0}
  previousValue={stats.prevThrottledCount}
  colorScheme="benign"
  deltaInverted={false}
/>

// AVG ML CONFIDENCE card
<KpiCard
  label="Avg ML Confidence"
  value={
    stats.avgConfidenceIsEmpty
      ? '—'
      : `${Math.round((stats.avgConfidence ?? 0) * 100)}%`
  }
  subtext={stats.avgConfidenceIsEmpty ? 'No traffic in window' : 'Model stable'}
  colorScheme="neutral"
/>

// FALSE POSITIVE RATE card
<KpiCard
  label="False Positive Rate"
  value={stats.falsePositiveRate != null ? `${stats.falsePositiveRate}%` : '—'}
  subtext={stats.falsePositiveRate != null ? 'Below threshold' : 'No data'}
  colorScheme="neutral"
/>
```

---

### 3.2 — Fix loading state — skeleton instead of "Calculating..." ✅ 2026-03-22 02:34 PHT

```tsx
if (isLoading) {
  return (
    <div className="rounded-lg border border-[var(--color-kpi-border-default)] bg-[var(--color-bg-panel)] p-4">
      <div className="skeleton h-[10px] w-20 mb-3 rounded" />
      <div className="skeleton h-[28px] w-12 mb-2 rounded" />
      <div className="skeleton h-[10px] w-28 rounded" />
    </div>
  )
}
```

---

### 3.3 — Add progress bar to BLOCKED card ✅ 2026-03-22 02:34 PHT

```tsx
{typeof progressBar === 'number' && (
  <div className="mt-2.5 h-[2px] w-full rounded-full bg-[var(--color-bg-inset)]">
    <div
      className="h-full rounded-full transition-all duration-700"
      style={{
        width: `${Math.min(progressBar, 100)}%`,
        background: 'var(--color-accent-purple)',
      }}
    />
  </div>
)}
```

---

### 3.4 — Animate numbers on data arrival ✅ 2026-03-22 02:34 PHT

```tsx
import { useEffect, useRef } from 'react'
import { animate } from 'motion'

function AnimatedNumber({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const controls = animate(0, value, {
      duration: 0.6,
      ease: 'easeOut',
      onUpdate(v) {
        if (ref.current) ref.current.textContent = Math.round(v).toString()
      },
    })
    return () => controls.stop()
  }, [value])
  return <span ref={ref}>{value}</span>
}
```

---

## Phase 4: Frontend — Chart Overhaul

---

### 4.1 — Switch to Area chart with gradient fills ✅ 2026-03-22 02:34 PHT

**File:** Your chart component

```tsx
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'

<ResponsiveContainer width="100%" height={160}>
  <AreaChart data={chartData} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
    <defs>
      <linearGradient id="gradBlocked" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15} />
        <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
      </linearGradient>
      <linearGradient id="gradThrottled" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#f97316" stopOpacity={0.15} />
        <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
      </linearGradient>
      <linearGradient id="gradAllowed" x1="0" y1="0" x2="0" y2="1">
        <stop offset="5%" stopColor="#4ade80" stopOpacity={0.15} />
        <stop offset="95%" stopColor="#4ade80" stopOpacity={0} />
      </linearGradient>
    </defs>

    <CartesianGrid
      strokeDasharray="3 3"
      stroke="rgba(255,255,255,0.04)"
      vertical={false}
    />
    <XAxis
      dataKey="time"
      tick={{ fontSize: 10, fill: '#475569' }}
      tickLine={false}
      axisLine={false}
      interval="preserveStartEnd"
      tickCount={6}
    />
    <YAxis
      tick={{ fontSize: 10, fill: '#475569' }}
      tickLine={false}
      axisLine={false}
      allowDecimals={false}
      width={24}
    />
    <Tooltip
      contentStyle={{
        background: '#1a2236',
        border: '1px solid #2d3748',
        borderRadius: 8,
        fontSize: 12,
        padding: '8px 12px',
      }}
      labelStyle={{ color: '#94a3b8', marginBottom: 4 }}
    />
    <Area type="monotone" dataKey="blocked"   stroke="#ef4444" strokeWidth={1.5} fill="url(#gradBlocked)"   dot={false} activeDot={{ r: 3 }} />
    <Area type="monotone" dataKey="throttled" stroke="#f97316" strokeWidth={1.5} fill="url(#gradThrottled)" dot={false} activeDot={{ r: 3 }} />
    <Area type="monotone" dataKey="allowed"   stroke="#4ade80" strokeWidth={1.5} fill="url(#gradAllowed)"   dot={false} activeDot={{ r: 3 }} />
  </AreaChart>
</ResponsiveContainer>
```

---

### 4.2 — Add empty state overlay when all data points are zero ✅ 2026-03-22 02:34 PHT

```tsx
const isEmpty = chartData.every(
  (d) => (d.blocked ?? 0) + (d.throttled ?? 0) + (d.allowed ?? 0) === 0
)

<div className="relative">
  <ResponsiveContainer width="100%" height={160}>
    {/* chart */}
  </ResponsiveContainer>

  {isEmpty && !isPending && (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
      <p className="text-[11px] text-[var(--color-text-muted)]">No events in this window</p>
      <p className="text-[10px] text-[var(--color-text-ghost)]">Traffic was quiet during this period</p>
    </div>
  )}
</div>
```

---

### 4.3 — Add chart skeleton loader ✅ 2026-03-22 02:34 PHT

```tsx
if (isPending) {   // v5: isPending not isLoading
  return (
    <div className="h-[160px] w-full flex items-end gap-px px-2 pb-2">
      {Array.from({ length: 24 }).map((_, i) => (
        <div
          key={i}
          className="skeleton flex-1 rounded-t"
          style={{ height: `${15 + Math.sin(i * 0.5) * 30 + Math.random() * 20}%` }}
        />
      ))}
    </div>
  )
}
```

---

### 4.4 — Add time window transition animation ✅ 2026-03-22 02:34 PHT

```tsx
import { AnimatePresence, motion } from 'motion/react'

<AnimatePresence mode="wait">
  <motion.div
    key={selectedWindow}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    transition={{ duration: 0.2 }}
  >
    <AttackEventChart data={chartData} />
  </motion.div>
</AnimatePresence>
```

---

## Phase 5: Frontend — Purge Hardcoded Hex Values

---

### 5.1 — Audit all hardcoded hex values ✅ 2026-03-22 02:34 PHT

```bash
grep -rn '#[0-9a-fA-F]\{3,6\}' app/ components/ --include="*.tsx" --include="*.ts" \
  | grep -v "globals.css" | grep -v ".test."
```

**Priority replacement map:**

| Hardcoded | Token |
|---|---|
| `#ef4444`, `#f87171` | `var(--color-severity-high-accent)` / `-text` |
| `#f97316`, `#fb923c` | `var(--color-severity-blocked-accent)` / `-text` |
| `#4ade80` | `var(--color-severity-safe-accent)` |
| `#a78bfa` | `var(--color-accent-purple)` |
| `#7eb8f7` | `var(--color-accent-blue)` |
| `#f1f5f9` | `var(--color-text-primary)` |
| `#94a3b8` | `var(--color-text-secondary)` |
| `#475569` | `var(--color-text-muted)` |
| `#060b14` | `var(--color-bg-base)` |
| `#0c1120` | `var(--color-bg-page)` |
| `#111827` | `var(--color-bg-panel)` |
| `#1a2236` | `var(--color-bg-elevated)` |
| `#1e2a3d` | `var(--color-text-ghost)` |

---

### 5.2 — Fix login page DOM mutation anti-pattern ✅ 2026-03-22 02:34 PHT

**File:** `frontend/app/(auth)/login/page.tsx`

```tsx
// Add state
const [isFocused, setIsFocused] = useState(false)

// Replace the input
<input
  id="password"
  type="password"
  value={password}
  onChange={(e) => setPassword(e.target.value)}
  onKeyDown={(e) => e.key === 'Enter' && !pending && handleSubmit()}
  onFocus={() => setIsFocused(true)}
  onBlur={() => setIsFocused(false)}
  className={cn(
    'w-full px-3 py-2.5 rounded-lg text-[13px] outline-none transition-all',
    'bg-[var(--color-bg-page)] text-[var(--color-text-primary)]',
    isFocused
      ? 'border border-[var(--color-accent-purple)] shadow-[0_0_0_3px_rgba(167,139,250,0.1)]'
      : 'border border-[var(--color-text-ghost)]'
  )}
/>
```

---

## Phase 6: Frontend — Empty States, Skeletons, Typography, Spacing

> These are covered in detail in the original plan. Summary for completeness:

- ✅ **6.1** — Build reusable `EmptyState` component (`components/ui/EmptyState.tsx`) used by Top Source IPs, Top Targeted Paths, and the chart.
- ✅ **6.2** — Add alert table skeleton (`AlertTableSkeleton`) matching real row layout.
- ✅ **6.3** — Section heading standardization: `text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]`
- ✅ **6.4** — KPI card three-tier hierarchy: label (11px muted uppercase) → number (28px colored) → delta/subtext (11px)
- ✅ **6.5** — Standardize panel padding: `p-4` internal, `gap-4` between panels.
- ✅ **6.6** — Fix bar alignment in Attack Type Dist. and ML Confidence Bands using a 3-column grid.
- ✅ **6.7** — Motion staggered card entrance and number count-up animations.

---

## Implementation Order — Full-Stack Sprint Breakdown

### Sprint 0 — Backend (unblocks everything else)
1. Phase 0.1 — Add previous-window counts to `get_stats_summary` (use `asyncio.gather` for parallel queries)
2. Phase 0.2 — Fix `avg_confidence` returning null
3. Phase 0.3 — Add false positive rate to stats response
4. Phase 0.4 — Guarantee `top_source_ips` and `top_targeted_paths` always returned
5. Phase 0.5 — Add `high_alert_count` as explicit field

### Sprint 1 — BFF (unblocks frontend cards)
6. Phase 1.1 — Add previous-window fields to `BackendStatsSchema`
7. Phase 1.2 — Update `DashboardStats` type
8. Phase 1.3 — Update normalization to map new fields
9. Phase 1.4 — Fix `top_source_ips` / `top_targeted_paths` Zod schema
10. Phase 1.5 — Handle `avg_confidence` null with `avgConfidenceIsEmpty` flag
11. Phase 1.6 — Add `blockRate` to normalization
12. **Phase 1.7 — Fix `isPending`, add `refetchInterval: 15_000` + `placeholderData` (P0)**
13. **Phase 1.8 — Add `QueryErrorResetBoundary` + panel error UI (P0)**

### Sprint 2 — Frontend Foundation (fix before any components)
14. Phase 2.1 — Fix `--color-status-blocked` token bug
15. Phase 2.2 — Fix font size minimums
16. Phase 2.3 — Fix `--color-primary` conflict
17. Phase 2.4 — Add missing semantic tokens
18. Phase 2.5 — Expose skeleton utility class

### Sprint 3 — Frontend Data States (most visible improvement)
19. Phase 3.2 — KPI card skeleton loaders (use `isPending` not `isLoading`)
20. Phase 4.2 — Chart empty state overlay (use `isPending` not `isLoading`)
21. Phase 4.3 — Chart skeleton loader (use `isPending` not `isLoading`)
22. Phase 6.1 — EmptyState component
23. Phase 6.2 — Alert table skeleton

### Sprint 4 — Frontend Cards & Chart (highest visual impact)
24. Phase 4.1 — Area chart with gradient fills
25. Phase 3.1 — KPI delta indicators (requires Sprint 0+1 to be done)
26. Phase 3.3 — Progress bar on BLOCKED card
27. Phase 6.6 — Bar alignment in Attack Type Dist.

### Sprint 5 — Code Quality
28. Phase 5.1 — Purge hardcoded hex values (use Tailwind v4 auto-generated utilities where possible)
29. Phase 5.2 — Fix login DOM mutation

### Sprint 6 — Polish
30. Phase 3.4 — Number count-up animation
31. Phase 4.4 — Chart time window transition
32. Phase 6.3 — Section heading standardization
33. Phase 6.4 — KPI card three-tier hierarchy
34. Phase 6.5 — Standardize panel padding
35. Phase 6.7 — Motion staggered card entrance

---

## Dependency Map

```
Phase 0.1 (backend prev window — uses asyncio.gather)
  └── Phase 1.1 (BFF schema)
        └── Phase 1.2 (DashboardStats type)
              └── Phase 1.3 (normalization)
                    └── Phase 3.1 (KPI delta indicators)

Phase 0.2 (avg_confidence null fix)
  └── Phase 1.5 (avgConfidenceIsEmpty flag)
        └── Phase 3.1 (AVG ML CONFIDENCE card)

Phase 0.3 (backend FPR)
  └── Phase 1.1 → Phase 1.3
        └── Phase 3.1 (FALSE POSITIVE RATE card)

Phase 0.4 (backend always returns IPs/paths)
  └── Phase 1.4 (BFF Zod schema fix)
        └── Phase 6.1 (EmptyState — only shows when truly empty)

Phase 0.5 (high_alert_count)
  └── Phase 1.3 (normalization fallback)
        └── Phase 3.1 (HIGH ALERTS card)

Phase 1.6 (blockRate in normalization)
  └── Phase 3.3 (progress bar on BLOCKED card)

Phase 1.7 (isPending + refetchInterval + placeholderData)
  └── Phase 3.2, 4.2, 4.3 (all skeleton/empty state components must use isPending)

Phase 1.8 (QueryErrorResetBoundary)
  └── All panel components (wrap each independently after component work is done)

Phase 2.1–2.5 (token fixes) → All frontend component phases — must be done first
Phase 2.5 (skeleton utility class) → Phase 3.2, 4.3, 6.2
```

---

## Testing Checklist

### Backend
- [ ] `GET /stats?window=6h` returns `prev_blocked_count`, `prev_allowed_count`, `prev_throttled_count`
- [ ] Phase 0.1 queries run in parallel — verify with query timing logs, not two sequential awaits
- [ ] `GET /stats?window=1h` with no traffic returns `avg_confidence: 0.0` not `null`
- [ ] `GET /stats` (no window) returns `prev_*` fields as `null` or absent — no crash
- [ ] `GET /stats` always includes `top_source_ips` and `top_targeted_paths` as arrays (never absent)
- [ ] `false_positive_rate` and `false_positive_count` present in response
- [ ] `high_alert_count` present in response

### BFF
- [ ] Zod parse does not throw when all new fields are present
- [ ] Zod parse does not throw when `prev_*` fields are absent (all-time query)
- [ ] `top_source_ips` and `top_targeted_paths` default to `[]` when backend omits them
- [ ] `avgConfidenceIsEmpty` is `true` when `total_requests === 0`
- [ ] `blockRate` is a number 0–100, never NaN
- [ ] Dashboard network tab shows a new request every 15s (refetchInterval working)
- [ ] Switching time windows does NOT flash a skeleton — previous data stays visible during fetch (placeholderData working)
- [ ] When BFF returns 500, each panel shows its own error UI with a retry button — not a blank panel

### Frontend
- [ ] All skeleton conditions use `isPending` not `isLoading` — grep: `grep -rn "isLoading" app/ components/`
- [ ] KPI delta lines appear when window is selected (not on all-time)
- [ ] BLOCKED card shows purple progress bar
- [ ] FALSE POSITIVE RATE card shows a real percentage, not "Not available"
- [ ] AVG ML CONFIDENCE shows "No traffic in window" on empty windows, not a dash
- [ ] Chart shows area fills with gradient under each line
- [ ] Chart shows "No events in this window" overlay on flat windows
- [ ] Loading states show skeletons, not "Calculating..."
- [ ] Top Source IPs and Top Targeted Paths panels are populated correctly
- [ ] `--color-status-blocked` resolves to red (#ef4444) in DevTools computed styles
- [ ] No text below 10px in the UI
- [ ] No hardcoded hex values in component files — grep: `grep -rn '#[0-9a-fA-F]\{3,6\}' app/ components/ --include="*.tsx"`
- [ ] Tailwind v4 generated utilities used where available (e.g. `text-text-secondary` not `text-[var(--color-text-secondary)]`)
- [ ] Switching time windows (1h → 6h) triggers a new network request, not a stale cache hit
