# Frontend Implementation Plan — WAF-ML SOC Dashboard
> Research-grounded. Based on Next.js 15 App Router docs, TanStack Query v5 best practices (tkdodo.eu), shadcn/ui installation guides, and Next.js security advisory CVE-2025-29927.
> Last updated: 2026-03-08 (v2 — post-review corrections applied)

---

## Reference Design Files

The target UI is fully defined by the files in:
```
G:\Documents\PDDDD\injection-alert-system\stitch_waf_ml_soc_dashboard_overview\
```
- **`code.html`** — Complete Tailwind/HTML implementation of the SOC dashboard, built in Google Stitch. Contains every component, color token, layout structure, and table row needed to derive types and visual specs.
- **`*.png`** — Rendered screenshot showing the exact target layout.

**Attach both files to the AI in every session that involves layout, data shape, or visual components.** They are the single source of truth for the design.

---

## 0. Pre-work: Corrections to the Draft Plan

The following are hard corrections derived from official docs — not stylistic preferences:

| Issue in Draft Plan | Correct Approach | Source |
|---|---|---|
| Query keys in `lib/queryKeys.ts` | Colocate per feature in `features/alerts/queries.ts` | tkdodo.eu #8 |
| All hooks in `hooks/` folder | Colocate queries next to their feature | Next.js colocation docs |
| `Sidebar.tsx` as single component | Extract only `NavItem` as `'use client'` (active state) | Next.js bundle size guidance |
| Zustand stores filter/severity state | URL search params own filter state (shareable) | — |
| Mock data inside components | Mock at Route Handler level — component code never changes | PD1→PD2 swap strategy |
| Session 8 (hooks) after components | Hooks/queries before components that consume them | Dependency order |
| No `loading.tsx` files | Each route needs `loading.tsx` skeleton | Next.js `loading.js` convention |
| No `error.tsx` files | Add `error.tsx` per route — error boundary for API failures | Next.js `error.js` convention |
| Providers missing `'use client'` | `app/providers.tsx` = single `'use client'` wrapper | Next.js context provider docs |
| `tailwind.config.ts` in file tree | Tailwind v4 is CSS-first — no config file; all tokens in `globals.css @theme` block | Tailwind v4 docs |
| `AlertsTableRow.tsx` marked `'use client'` | Inherits directive from parent `AlertsTable.tsx` — no explicit directive needed | Next.js directive inheritance |
| `QueryClient` created bare inside component | Use `useState(() => new QueryClient())` lazy init — or clarify why that's already correct | TanStack Query v5 docs |
| Raw `queryKey` arrays in hook bodies | Use `queryOptions()` factory for type-safe key + fetcher colocation | TanStack Query v5 |
| `isLoading` in hook usage | Renamed to `isPending` in TanStack Query v5 — `isLoading` silently does nothing | v5 migration guide |
| No `middleware.ts` | Required for route auth protection + pins CVE-2025-29927 fix (CVSS 9.1) | Next.js security advisory |
| `tailwindcss-animate` in shadcn init | Deprecated March 2025 — use `tw-animate-css` instead | shadcn/ui changelog |
| middleware.ts matcher missing /api | Matcher must cover `/api/((?!auth).*)` — Route Handlers were completely unprotected | CVE-2025-29927 + NextAuth docs |
| No `auth()` in Route Handlers | Every Route Handler must call `auth()` and return 401 if no session | Auth.js v5 docs |
| `app/api/auth/[...nextauth]/route.ts` missing | Required for NextAuth login flow — without it login does not work | Auth.js v5 docs |
| No `React.cache()` for auth | Duplicate session DB reads per request in RSC — use `getSession()` from `lib/auth-session.ts` | React cache() docs |
| `gcTime` undocumented | Setting `gcTime: 0` causes hydration errors with HydrationBoundary | TanStack Query v5 docs |
| `not-found.tsx` missing | Unmatched routes show blank screen — add `app/not-found.tsx` | Next.js conventions |

---

## 1. Stack & Constraints (Locked)

```
Runtime:     Next.js >=15.2.3  ← REQUIRED: pins fix for CVE-2025-29927 (CVSS 9.1,
             middleware auth bypass). Pin this in package.json. App Router, React 19.
Language:    TypeScript strict mode ("strict": true)
Styling:     Tailwind CSS v4 only — no inline styles, no CSS modules.
             Config is CSS-first: all tokens live in globals.css @theme block.
             No tailwind.config.ts file. Use tw-animate-css, not
             tailwindcss-animate.
Components:  shadcn/ui (Radix primitives + CVA).
             Use tw-animate-css — tailwindcss-animate is deprecated since March 2025.
Server state: TanStack Query v5.
             Use isPending not isLoading (isLoading removed in v5).
             Use queryOptions() factory — not raw queryKey objects.
Client state: Zustand v5 (UI-ephemeral only)
Filter state: URL search params (useSearchParams + useRouter)
Backend:     FastAPI via Next.js Route Handlers (BFF pattern)
Auth:        NextAuth v5 — requires splitting into auth.config.ts (edge-safe, used in
             middleware) + auth.ts (full config with adapter, used in RSC + Route Handlers)
```

### Color Tokens (Tailwind config)
```
sidebar-bg:    #1e3a5f     primary:    #e03131
surface-light: #f4f7fb     border:     #e2e8f0
text-main:     #0f172a     text-muted: #64748b
status-high:   #dc2626     status-medium: #f97316
status-low:    #6b7280     status-blocked: #dc2626
status-throttled: #f97316  status-logged: #6b7280
status-ratelimited: #8b5cf6
```

### Confidence Thresholds
```
LOW    < 50%    (grey)
MEDIUM 50–80%   (orange)
HIGH   > 80%    (red)
```

### Environment Variables
```
# Server-only (never NEXT_PUBLIC_ prefix — never accessible to client)
FASTAPI_BASE_URL=http://fastapi:8000      # internal Docker network
INTERNAL_API_KEY=...                      # FastAPI auth header
NEXTAUTH_SECRET=...                       # NextAuth v5 signing key

# Public (safe to expose)
NEXT_PUBLIC_APP_ENV=development           # 'development' | 'production'
NEXT_PUBLIC_APP_VERSION=1.0.0
```
> ⚠️ Install the `server-only` package and add `import 'server-only'`
> at the top of any file that reads server-only env vars. This causes
> a build-time error if that file is accidentally imported by a client
> component.

---

## 2. Directory Structure (Final)

```
frontend/
├── app/
│   ├── layout.tsx                      # RSC root layout — renders Providers + shell
│   ├── providers.tsx                   # 'use client' — QueryClient + Zustand providers
│   ├── globals.css                     # Tailwind base + CSS vars
│   ├── page.tsx                        # redirect('/dashboard')
│   ├── not-found.tsx                   # Global 404 — renders when analyst
│   │                                   # navigates to /alerts/invalid-id
│   │                                   # or any unmatched route
│   ├── global-error.tsx                # 'use client' — renders <html><body> — last-resort
│   │                                   # error boundary if app/layout.tsx itself throws
│   │
│   ├── (dashboard)/                    # Route group — shares DashboardShell layout
│   │   ├── layout.tsx                  # Sidebar + TopBar shell (RSC)
│   │   ├── dashboard/
│   │   │   ├── page.tsx                # RSC — SOC Overview assembly
│   │   │   ├── loading.tsx             # Skeleton fallback (Suspense boundary)
│   │   │   └── error.tsx               # 'use client' — error boundary for API failures
│   │   ├── alerts/
│   │   │   ├── page.tsx
│   │   │   ├── loading.tsx
│   │   │   └── error.tsx
│   │   └── ml-health/
│   │       ├── page.tsx
│   │       ├── loading.tsx
│   │       └── error.tsx
│   │
│   ├── (auth)/                         # Route group — no shell layout
│   │   └── login/
│   │       └── page.tsx
│   │
│   └── api/                            # Next.js Route Handlers (BFF proxy layer)
│       ├── alerts/
│       │   └── route.ts                # GET /api/alerts → FastAPI (or mock)
│       ├── alerts/[id]/
│       │   └── route.ts                # GET /api/alerts/:id
│       ├── stats/
│       │   └── route.ts                # GET /api/stats
│       ├── ml-health/
│       │   └── route.ts                # GET /api/ml-health
│       └── auth/
│           └── [...nextauth]/
│               └── route.ts            # NextAuth v5 — handles OAuth flow,
│                                       # token exchange, session creation,
│                                       # CSRF protection automatically.
│                                       # Required for login to work at all.
│
├── components/
│   ├── layout/
│   │   ├── DashboardShell.tsx          # RSC — structural wrapper
│   │   ├── Sidebar.tsx                 # RSC — static nav shell
│   │   ├── SidebarNavItem.tsx          # 'use client' — usePathname for active state
│   │   ├── MLHealthWidget.tsx          # 'use client' — reads from useMLHealth hook
│   │   └── TopBar.tsx                  # 'use client' — search input, severity pills
│   │
│   ├── dashboard/
│   │   ├── AlertBanner.tsx             # 'use client' — dismissable
│   │   ├── MetricCards.tsx             # 'use client' — useDashboardStats(), hydrated from server prefetch
│   │   ├── CRSComparisonPanel.tsx      # 'use client' — useDashboardStats()
│   │   ├── AlertsTable/
│   │   │   ├── AlertsTable.tsx         # 'use client' — selection state, row clicks
│   │   │   ├── AlertsTableRow.tsx      # inherits 'use client' from parent — no directive
│   │   │   └── BulkActionBar.tsx       # 'use client' — bulk action buttons
│   │   ├── IncidentDetailPanel.tsx     # 'use client' — reads activeIncidentId
│   │   ├── AttackDistribution.tsx      # RSC — static chart (bar chart, no lib needed)
│   │   └── ConfidenceHistogram.tsx     # RSC — static chart
│   │
│   └── ui/                             # Atomic, fully stateless
│       ├── SeverityBadge.tsx           # RSC — CVA variants: critical/high/medium/low
│       ├── ConfidenceBar.tsx           # RSC — progress bar + % label
│       ├── ActionLabel.tsx             # RSC — CVA: blocked/throttled/logged/ratelimited
│       └── ShapChart.tsx               # RSC — horizontal feature importance bars
│
├── features/                           # Feature-colocated: queries + types together
│   ├── alerts/
│   │   ├── queries.ts                  # queryKeys factory + useAlerts, useAlert hooks
│   │   └── types.ts                    # Alert, AlertSeverity, AlertAction, ShapFeature, SourceIntel, PaginatedAlerts
│   ├── stats/
│   │   ├── queries.ts                  # queryKeys + useDashboardStats hook
│   │   └── types.ts                    # DashboardStats interface
│   └── ml-health/
│       ├── queries.ts                  # queryKeys + useMLHealth hook
│       └── types.ts                    # MLHealthData interface
│
├── store/
│   └── dashboardStore.ts               # Zustand: selectedAlertIds, activeIncidentId
│                                       # (UI state ONLY — no server state here)
│
├── lib/
│   ├── constants.ts                    # NAV_ITEMS, CONFIDENCE_THRESHOLDS
│   ├── utils.ts                        # cn(), getConfidenceLevel(), formatMs(), etc.
│   └── auth-session.ts                 # React.cache() memoized auth helper —
│                                       # prevents duplicate session DB reads
│                                       # per request in RSC pages
│
├── mocks/                              # PD1 mock data — deleted/ignored in PD2
│   ├── alerts.ts                       # MOCK_ALERTS array typed against features/alerts/types
│   ├── stats.ts                        # MOCK_STATS
│   └── ml-health.ts                    # MOCK_ML_HEALTH
│
├── public/
│   └── favicon.ico
│
├── .env.local                          # NEXT_PUBLIC_APP_ENV, FASTAPI_BASE_URL (server-only)
├── components.json                     # shadcn/ui config
├── tsconfig.json                       # "strict": true, paths: {"@/*": ["./*"]}
├── next.config.ts
├── middleware.ts                       # Route protection — matcher covers /dashboard/* AND /api/*
├── auth.config.ts                      # Edge-safe NextAuth v5 config (used by middleware)
└── auth.ts                             # Full NextAuth v5 config (used in RSC + Route Handlers)
(no tailwind.config.ts — Tailwind v4 is CSS-first; tokens defined in globals.css @theme block)
```

> The contents of `app/api/auth/[...nextauth]/route.ts` are exactly:
> ```typescript
> import { handlers } from '@/auth'
> export const { GET, POST } = handlers
> ```
> Do not add any other logic to this file.

> ⚠️ Security: Pin Next.js to >=15.2.3 in package.json to mitigate
> CVE-2025-29927 (CVSS 9.1 — middleware auth bypass via
> x-middleware-subrequest header). Middleware matcher MUST include
> /api/* — omitting it leaves all BFF Route Handlers unprotected.
>
> Minimum middleware.ts matcher:
> ```typescript
> export const config = {
>   matcher: [
>     '/dashboard/:path*',
>     '/alerts/:path*',
>     '/ml-health/:path*',
>     '/api/:path*',
>   ]
> }
> ```

---

## 3. Server vs Client Component Map

This is the most important architectural decision. Get this wrong and you add unnecessary JS to the bundle.

```
RSC (Server Component — default)         'use client' (Client Component — explicit)
─────────────────────────────────        ──────────────────────────────────────────
app/layout.tsx                           app/providers.tsx
(dashboard)/layout.tsx                   SidebarNavItem.tsx     ← usePathname()
(dashboard)/dashboard/page.tsx           MLHealthWidget.tsx     ← useMLHealth() hook
AttackDistribution.tsx                   MetricCards.tsx        ← useDashboardStats() hook
ConfidenceHistogram.tsx                  CRSComparisonPanel.tsx ← useDashboardStats() hook
SeverityBadge.tsx                        TopBar.tsx             ← useState (search)
ConfidenceBar.tsx                        AlertBanner.tsx        ← useState (dismiss)
ActionLabel.tsx                          AlertsTable.tsx        ← useAlerts, Zustand
ShapChart.tsx                            AlertsTableRow.tsx     ← inherits 'use client' from AlertsTable parent
Sidebar.tsx (static shell)               (no directive needed — do NOT add 'use client')
                                         BulkActionBar.tsx      ← onClick handlers
                                         IncidentDetailPanel.tsx ← Zustand activeId
```

**Rule of thumb applied**: Push `'use client'` as deep as possible. `Sidebar` is mostly markup — only `SidebarNavItem` needs `usePathname()`, so only that sub-component gets the directive.

---

## 4. State Architecture

### 4.1 Zustand — UI-Ephemeral State Only
```typescript
// store/dashboardStore.ts
interface DashboardStore {
  selectedAlertIds: Set<string>
  activeIncidentId: string | null
  toggleAlertSelection: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  setActiveIncident: (id: string | null) => void
}
```
**Does NOT own**: filter severity, time range, search query — those live in URL.

> ⚠️ **useShallow required for all array/object selectors.** Default Zustand equality
> is reference equality — a new array reference on any store write causes all
> consumers to re-render even when content is unchanged. Use `useShallow` from
> `zustand/react/shallow` in every component that selects `selectedAlertIds`:
> ```typescript
> import { useShallow } from 'zustand/react/shallow'
> const selectedIds = useDashboardStore(useShallow(s => s.selectedAlertIds))
> ```
>
> ⚠️ **Clear selection on filter change.** When URL filters change, the alert list
> re-queries and `selectedAlertIds` retains IDs not visible in the new result set.
> `AlertsTable.tsx` must include:
> ```typescript
> useEffect(() => { clearSelection() }, [filters.severity, filters.timeRange, filters.search])
> ```

### 4.2 URL Search Params — Filter State
```
/dashboard?severity=HIGH&timeRange=24h&search=192.168
```
- `TopBar.tsx` reads/writes with `useSearchParams()` + `useRouter().push()`
- Makes filters shareable, bookmarkable, back-button compatible
- TanStack Query reads filters from URL → drives re-fetch automatically

### 4.3 TanStack Query — Server State
- Query key factory pattern, colocated in `features/*/queries.ts`
- `staleTime: 30_000` (30s) for dashboard stats
- `staleTime: 0` for alerts table (always fresh)
- Polling: `refetchInterval: 10_000` on alerts in production (disabled in PD1)

### 4.4 Providers Wrapper (Required for RSC compatibility)
```typescript
// app/providers.tsx
'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  // ✅ useState lazy init — creates ONE client per component mount, stable across re-renders
  // ❌ NOT: const queryClient = new QueryClient()  — new empty cache on every render
  // ❌ NOT: module-level const queryClient = new QueryClient()  — shared across SSR requests
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1 } }
  }))
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
```
Then in `app/layout.tsx` (RSC):
```typescript
import { Providers } from './providers'
export default function RootLayout({ children }) {
  return <html><body><Providers>{children}</Providers></body></html>
}
```

---

## 5. Data Flow: PD1 → PD2 Swap Strategy

The key insight: **mock at the Route Handler level, not inside components or hooks**.

### PD1 (Mock — current sprint)
```
Browser → fetch('/api/alerts') → app/api/alerts/route.ts → return MOCK_ALERTS
```
```typescript
// app/api/alerts/route.ts  (PD1)
import { MOCK_ALERTS } from '@/mocks/alerts'
export async function GET() {
  return Response.json(MOCK_ALERTS)
}
```

### PD2 (Real — next sprint)
```
Browser → fetch('/api/alerts') → app/api/alerts/route.ts → FastAPI /api/v1/alerts
```
```typescript
// app/api/alerts/route.ts  (PD2)
import 'server-only'
export async function GET(request: Request) {
  const res = await fetch(`${process.env.FASTAPI_BASE_URL}/api/v1/alerts`, {
    headers: { Authorization: `Bearer ${process.env.INTERNAL_API_KEY}` }
  })
  return Response.json(await res.json())
}
```

**Component code never changes between PD1 and PD2.** Only the Route Handler implementation swaps.

---

## 6. Query Key Factory Pattern

Use the `queryOptions()` factory introduced in TanStack Query v5. It colocates the key and fetcher into a single typed object, which can be consumed by both hooks and RSC-side prefetching without any key/fetcher drift.

> ⚠️ **NEVER put a raw object in a query key.** Two objects `{ severity: 'HIGH' }` with
> identical values have different reference identities across renders, producing
> duplicate cache entries and refetch storms. Always serialize with `toQueryString()`.
> The canonical implementation below is also used verbatim in Session 3.

```typescript
// features/alerts/queries.ts — canonical implementation (use verbatim in Session 3)
import { queryOptions, useQuery } from '@tanstack/react-query'
import { toQueryString, type DashboardFilters } from '@/lib/searchParams'
import type { Alert, PaginatedAlerts } from './types'

// Keys use plain string serialization — deterministic, no reference-identity issues
export const alertKeys = {
  all:    ['alerts']                                                     as const,
  list:   (filtersKey: string) => ['alerts', 'list', filtersKey]        as const,
  detail: (id: string)         => ['alerts', 'detail', id]              as const,
}

export const alertListOptions = (filters: DashboardFilters) =>
  queryOptions<PaginatedAlerts>({
    queryKey: alertKeys.list(toQueryString(filters)),
    queryFn:  () => fetch(`/api/alerts?${toQueryString(filters)}`).then(r => r.json()),
    staleTime: 0,
  })

export const alertDetailOptions = (id: string) =>
  queryOptions<Alert>({
    queryKey: alertKeys.detail(id),
    queryFn:  () => fetch(`/api/alerts/${id}`).then(r => r.json()),
    enabled:  !!id,
  })

// Hooks are thin wrappers — consume the options objects
export const useAlerts = (filters: DashboardFilters) => useQuery(alertListOptions(filters))
export const useAlert  = (id: string)                 => useQuery(alertDetailOptions(id))
```

This pattern pays off in Session 8 (RSC page prefetching) where you can write:
```typescript
// app/(dashboard)/dashboard/page.tsx  — RSC
await queryClient.prefetchQuery(alertListOptions({ severity: 'ALL', timeRange: '24h' }))
// ↑ Identical key + fetcher as the client hook — zero duplication, zero drift
```

---

## 7. Build Order — 8 Sessions

> Sessions restructured based on correct dependency graph.

---

### Session 1 — Foundation Types & Mocks
**Output**: `auth.config.ts`, `auth.ts`, `features/*/types.ts`, `mocks/*.ts`, `lib/constants.ts`, `lib/utils.ts`, `lib/searchParams.ts`

> ⚠️ Produce `auth.config.ts` and `auth.ts` **first** in this session.
> `lib/auth-session.ts` (below) imports `{ auth }` from `@/auth`, and every
> Session 2 Route Handler does the same. Without these two files the
> `npx tsc --noEmit` checkpoint at the end of this session fails immediately
> with module-not-found on `@/auth`.

**Files**:
```
auth.config.ts                  ← Edge-safe NextAuth v5 config stub — imported by middleware.ts
auth.ts                         ← Full NextAuth v5 config stub — exports handlers, auth, signIn, signOut
features/alerts/types.ts        ← Alert, AlertSeverity, AlertAction, ShapFeature, SourceIntel, PaginatedAlerts
features/stats/types.ts         ← DashboardStats, CRSComparisonMetrics
features/ml-health/types.ts     ← MLHealthData, ConfidenceThresholds
mocks/alerts.ts                 ← MOCK_ALERTS typed as PaginatedAlerts: { items: Alert[], total: 6, page: 1, pageSize: 20 }
                                   ⚠️ Must match AlertsResponseSchema paginated shape — hooks always expect PaginatedAlerts
mocks/stats.ts                  ← Typed mock stats matching HTML metric cards
mocks/ml-health.ts              ← Typed mock model health data
lib/constants.ts                ← NAV_ITEMS array, CONFIDENCE_THRESHOLDS, COLOR_MAP
lib/utils.ts                    ← cn(), getConfidenceLevel(), formatMs(), etc.
lib/searchParams.ts             ← normalizeSearchParams() helper + Filters type
lib/auth-session.ts             ← React.cache() wrapped auth() for RSC use
```

```typescript
// auth.config.ts — Edge-safe. No Node-only imports (no Prisma, bcrypt, DB adapters).
// Imported by middleware.ts which runs on the Edge runtime. Keep this file lean.
import type { NextAuthConfig } from 'next-auth'

export const authConfig = {
  providers: [],           // ← Add CredentialsProvider or OAuth provider here in PD2
  pages: { signIn: '/login' },
} satisfies NextAuthConfig
```

```typescript
// auth.ts — Full NextAuth v5 config. Node-only — NEVER import this in middleware.ts.
// Exports handlers (for /api/auth/[...nextauth]/route.ts), auth(), signIn(), signOut().
import NextAuth from 'next-auth'
import { authConfig } from './auth.config'

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  // In PD2 add: adapter: PrismaAdapter(prisma),
  session: { strategy: 'jwt' },   // JWT works without a DB adapter for PD1 demo
})
```

```typescript
// lib/auth-session.ts
import 'server-only'
import { cache } from 'react'
import { auth } from '@/auth'

// Memoizes auth() for the duration of a single server render pass.
// Use this in RSC layouts and pages instead of calling auth() directly.
// Prevents duplicate session DB reads when multiple RSC components
// on the same page need the session (e.g., layout + page both check role).
export const getSession = cache(async () => {
  const session = await auth()
  return session
})
```

> Use `getSession()` in all RSC components that need the session
> (layout.tsx, page.tsx). Use `auth()` directly only in Route Handlers.
> Never call `auth()` directly in RSC — always use `getSession()`.

```typescript
// lib/searchParams.ts
export type SeverityFilter = 'ALL' | 'LOW' | 'MEDIUM' | 'HIGH'
export type TimeRange = '1h' | '6h' | '24h' | '7d'

export interface DashboardFilters {
  severity: SeverityFilter
  timeRange: TimeRange
  search: string
}

export const DEFAULT_FILTERS: DashboardFilters = {
  severity: 'ALL',
  timeRange: '24h',
  search: '',
}

// Next.js 15: searchParams is a Promise in RSC pages — must be awaited
export async function normalizeSearchParams(
  searchParams: Promise<Record<string, string | string[] | undefined>>
): Promise<DashboardFilters> {
  const params = await searchParams
  return {
    severity: (['ALL','LOW','MEDIUM','HIGH'].includes(params.severity as string)
      ? params.severity as SeverityFilter
      : DEFAULT_FILTERS.severity),
    timeRange: (['1h','6h','24h','7d'].includes(params.timeRange as string)
      ? params.timeRange as TimeRange
      : DEFAULT_FILTERS.timeRange),
    search: typeof params.search === 'string' ? params.search : '',
  }
}

// Use this for TanStack Query keys — plain objects are non-deterministic
export function toQueryString(filters: DashboardFilters): string {
  return new URLSearchParams({
    severity: filters.severity,
    timeRange: filters.timeRange,
    search: filters.search,
  }).toString()
}
```

**Reference design files** (attach to every AI session involving layout, data shape, or visuals):
```
G:\Documents\PDDDD\injection-alert-system\stitch_waf_ml_soc_dashboard_overview\code.html
G:\Documents\PDDDD\injection-alert-system\stitch_waf_ml_soc_dashboard_overview\*.png
```

**What to give the AI**: The `code.html` table rows + the PNG screenshot. Say: "Extract TypeScript interfaces from this HTML. No JSX."

---

### Session 2 — Route Handlers (BFF Layer)
**Output**: `app/api/*/route.ts` with PD1 mock returns

**Files**:
```
app/api/alerts/route.ts         ← GET, returns MOCK_ALERTS
app/api/alerts/[id]/route.ts    ← GET, returns single alert by id
app/api/stats/route.ts          ← GET, returns MOCK_STATS
app/api/ml-health/route.ts      ← GET, returns MOCK_ML_HEALTH
```

> ⚠️ Every Route Handler MUST validate external responses with Zod
> before returning data to the client. Never trust FastAPI responses
> directly. Fail fast with a structured 502 if validation fails.
> For PD1, Route Handlers return mock data synchronously — no network
> required, guaranteed to render during demo.

```typescript
// app/api/alerts/route.ts — canonical Route Handler pattern
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { auth } from '@/auth'
import { MOCK_ALERTS } from '@/mocks/alerts'

const AlertSchema = z.object({
  alert_id: z.string(),
  prediction: z.string(),
  confidence: z.number().min(0).max(1),
  confidence_level: z.enum(['LOW', 'MEDIUM', 'HIGH']),
  action_taken: z.enum(['BLOCKED', 'THROTTLED', 'LOGGED', 'RATE_LIMITED']),
})

const AlertsResponseSchema = z.object({
  items: z.array(AlertSchema),
  total: z.number(),
  page: z.number(),
  pageSize: z.number(),
})

export async function GET(request: NextRequest) {
  // Auth check — applies in ALL environments including development
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // PD1: always return mock data synchronously.
  // ⚠️ Do NOT gate on NODE_ENV === 'development'. Production builds
  // ('npm run build && npm start') set NODE_ENV='production' and fall
  // through to the PD2 path, failing with ECONNREFUSED to FastAPI.
  // The demo should run as a production build — this gate breaks the demo.
  // To switch to PD2: remove this return and uncomment the fetch block below.
  return NextResponse.json(MOCK_ALERTS)

  // PD2 — remove the early return above and uncomment when FastAPI is running:
  // const res = await fetch(`${process.env.FASTAPI_BASE_URL}/api/alerts`, {
  //   headers: { Authorization: `Bearer ${process.env.INTERNAL_API_KEY}` },
  // })
  // const raw = await res.json()
  // const parsed = AlertsResponseSchema.safeParse(raw)
  // if (!parsed.success) {
  //   return NextResponse.json({ error: 'Invalid response from upstream' }, { status: 502 })
  // }
  // return NextResponse.json(parsed.data)
}
```

> ⚠️ Every Route Handler must call `auth()` and check for a valid
> session before returning any data — even in development. The mock
> shortcut is for the FastAPI dependency only, not for auth.
> Apply this same pattern to all route.ts files:
> `app/api/alerts/[id]/route.ts`, `app/api/stats/route.ts`,
> `app/api/ml-health/route.ts`

**Why this is Session 2 not Session 8**: Hooks depend on these endpoints existing. Test with `curl http://localhost:3000/api/alerts` before writing any hook.

---

### Session 3 — Feature Queries & Zustand Store
**Output**: `features/*/queries.ts`, `store/dashboardStore.ts`

**Files**:
```
features/alerts/queries.ts      ← alertListOptions() + useAlerts + useAlert
features/stats/queries.ts       ← statsOptions() + useDashboardStats
features/ml-health/queries.ts   ← mlHealthOptions() + useMLHealth
store/dashboardStore.ts         ← Zustand: selectedAlertIds, activeIncidentId
```

> ⚠️ Query key rule: NEVER put a raw object in a query key. Always use
> toQueryString(filters) from lib/searchParams.ts. Use queryOptions()
> for all query definitions so server prefetch and client hooks share
> the exact same key + fetcher with no drift.

```typescript
// features/alerts/queries.ts — canonical pattern for all feature queries
import { queryOptions, useQuery } from '@tanstack/react-query'
import { toQueryString, type DashboardFilters } from '@/lib/searchParams'
import type { Alert, PaginatedAlerts } from './types'

export const alertKeys = {
  all: ['alerts'] as const,
  list: (filtersKey: string) => ['alerts', 'list', filtersKey] as const,
  detail: (id: string) => ['alerts', 'detail', id] as const,
}

export const alertListOptions = (filters: DashboardFilters) =>
  queryOptions({
    queryKey: alertKeys.list(toQueryString(filters)),
    queryFn: () =>
      fetch(`/api/alerts?${toQueryString(filters)}`).then(r => r.json()),
    staleTime: 30_000,
  })

export const useAlerts = (filters: DashboardFilters) =>
  useQuery(alertListOptions(filters))
```

**Verify**: Each hook should resolve against the Route Handlers from Session 2.

---

### Session 4 — App Shell (Providers + Layout)
**Output**: `app/providers.tsx`, `app/layout.tsx`, `app/(dashboard)/layout.tsx`

**Files**:
```
app/providers.tsx               ← 'use client' — QueryClientProvider wrapper
app/layout.tsx                  ← RSC root layout — imports Providers
app/(dashboard)/layout.tsx      ← RSC — renders Sidebar + TopBar + {children}
app/page.tsx                    ← redirect('/dashboard')
app/globals.css                 ← Tailwind base + CSS custom properties
app/global-error.tsx            ← 'use client' — must render <html><body> (Next.js requirement)
app/(auth)/login/page.tsx       ← Credentials login form — calls NextAuth signIn(); must match the provider configured in auth.config.ts
```

> ⚠️ QueryClient must be created with useState lazy init — never at
> module level in a client component and never inside the render
> function body. Without useState, a new QueryClient is created on
> every render, destroying the cache.

```typescript
// app/providers.tsx — correct pattern
'use client'
import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 30_000,
          // ⚠️ Never set gcTime to 0 — causes hydration errors with
          // HydrationBoundary. The garbage collector removes cache
          // entries before HydrationBoundary finishes rendering.
          // Safe minimum is gcTime: 2 * 60 * 1000 (2 minutes).
          gcTime: 2 * 60 * 1000,
          retry: 1,
        },
      },
    })
  )
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

**Key**: `app/providers.tsx` is the ONLY place `QueryClientProvider` lives. `app/layout.tsx` is RSC.

**QueryClient initialization**: The `useState(() => new QueryClient(...))` lazy init pattern in `providers.tsx` is correct for Next.js App Router. Do not move it to module level (SSR request sharing) and do not write `new QueryClient()` bare in the function body (new empty cache every render). The lazy `useState` initializer is the one right answer.

```typescript
// app/global-error.tsx — REQUIRED. Must render <html> and <body>.
// Without this, an uncaught error in app/layout.tsx (e.g., broken Providers import)
// produces a blank white screen with no recovery path during demo.
'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body>
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <p>Something went wrong at the application level.</p>
          <button onClick={reset}>Try again</button>
        </div>
      </body>
    </html>
  )
}
```

---

### Session 5 — Atomic UI Components
**Output**: `components/ui/*.tsx`, all RSC

**Files**:
```
components/ui/SeverityBadge.tsx         ← CVA: critical/high/medium/low variants
components/ui/ConfidenceBar.tsx         ← width prop (0-100), color from getConfidenceLevel()
components/ui/ActionLabel.tsx           ← CVA: blocked/throttled/logged/ratelimited
components/ui/ShapChart.tsx             ← horizontal bars, positive=red/negative=yellow
```

**What to give the AI**: The design screenshot cropped to each UI element + types from Session 1.

---

### Session 6 — Layout Components
**Output**: `components/layout/*.tsx`

**Files**:
```
components/layout/Sidebar.tsx           ← RSC static shell, imports SidebarNavItem
components/layout/SidebarNavItem.tsx    ← 'use client' — usePathname for active border
components/layout/MLHealthWidget.tsx    ← 'use client' — useMLHealth() + Suspense
components/layout/TopBar.tsx            ← 'use client' — search, severity pill filters
                                           (writes to URL params, not Zustand)
```

**Key detail**: `TopBar` severity pills do `router.push('?severity=HIGH')` — not `setFilter()` in Zustand.

---

### Session 7 — Dashboard Feature Components
**Output**: `components/dashboard/*.tsx`

**Build in this order** (dependency chain within the session):
1. `MetricCards.tsx` — `'use client'`, calls `useDashboardStats()` — no props required; hydrated from server prefetch in Session 8
2. `CRSComparisonPanel.tsx` — `'use client'`, calls `useDashboardStats()` — same cache entry as MetricCards, zero additional requests
3. `AttackDistribution.tsx` — RSC, accepts `distribution: {label, pct}[]`
4. `ConfidenceHistogram.tsx` — RSC, accepts `bins: {label, count, pct}[]`
5. `AlertBanner.tsx` — `'use client'`, useState for dismiss
6. `AlertsTable/AlertsTable.tsx` — `'use client'`. **Live query filter source must be `useSearchParams()`**, NOT the `initialFilters` prop from the RSC page. If `initialFilters` is used as the `useAlerts()` argument, severity pill clicks in `TopBar` will have no effect on the table. Pattern:
   ```typescript
   const searchParams = useSearchParams()
   const filters = {
     severity: (searchParams.get('severity') ?? 'ALL') as SeverityFilter,
     timeRange: (searchParams.get('timeRange') ?? '24h') as TimeRange,
     search: searchParams.get('search') ?? '',
   }
   // Clear stale selection whenever filters change
   useEffect(() => { clearSelection() }, [filters.severity, filters.timeRange, filters.search])
   ```
7. `AlertsTable/BulkActionBar.tsx` — `'use client'`, reads `selectedAlertIds` from Zustand **with `useShallow`** to prevent re-renders on every store write:
   ```typescript
   import { useShallow } from 'zustand/react/shallow'
   const selectedIds = useDashboardStore(useShallow(s => s.selectedAlertIds))
   ```
8. `IncidentDetailPanel.tsx` — `'use client'`, reads `activeIncidentId` from Zustand, calls `useAlert(id)`

---

### Session 8 — Page Assembly
**Output**: `app/(dashboard)/dashboard/page.tsx` + `loading.tsx`

**Files**:
```
app/(dashboard)/dashboard/page.tsx      ← RSC — server prefetch + HydrationBoundary
app/(dashboard)/dashboard/loading.tsx   ← Suspense skeleton fallback
app/(dashboard)/dashboard/error.tsx     ← Error boundary per route
app/(dashboard)/alerts/page.tsx         ← RSC — same async searchParams pattern as dashboard/page.tsx
app/(dashboard)/alerts/loading.tsx      ← Suspense skeleton fallback
app/(dashboard)/alerts/error.tsx        ← Error boundary
app/(dashboard)/ml-health/page.tsx      ← RSC — same async searchParams pattern
app/(dashboard)/ml-health/loading.tsx   ← Suspense skeleton fallback
app/(dashboard)/ml-health/error.tsx     ← Error boundary
```

> ⚠️ **Every RSC page that reads `searchParams` must type it as `Promise<...>` and
> `await` it** (Next.js 15 breaking change). All three pages above (`dashboard`,
> `alerts`, `ml-health`) must use the `normalizeSearchParams()` helper from
> `lib/searchParams.ts`. Pages that skip the `await` silently receive a `Promise`
> object in the filter value, producing non-deterministic query keys and broken
> filter behavior.

```typescript
// app/(dashboard)/dashboard/page.tsx  — RSC
import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query'
import { normalizeSearchParams } from '@/lib/searchParams'
import { alertListOptions } from '@/features/alerts/queries'
import { statsOptions } from '@/features/stats/queries'

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const filters = await normalizeSearchParams(searchParams)
  const queryClient = new QueryClient()

  await Promise.all([
    queryClient.prefetchQuery(statsOptions()),
    queryClient.prefetchQuery(alertListOptions(filters)),
  ])

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <AlertBanner />
      <MetricCards />
      <CRSComparisonPanel />
      <AlertsTable initialFilters={filters} />
      <IncidentDetailPanel />
    </HydrationBoundary>
  )
}
```

```typescript
// app/(dashboard)/dashboard/loading.tsx  — automatic Suspense fallback
export default function DashboardSkeleton() {
  return <div className="animate-pulse ...">/* skeleton grid */</div>
}
```

```typescript
// app/(dashboard)/dashboard/error.tsx
'use client'
export default function DashboardError({
  error,
  reset,
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <p className="text-text-muted text-sm">Failed to load dashboard.</p>
      <button onClick={reset} className="text-primary text-sm underline">
        Retry
      </button>
    </div>
  )
}
```

---

## 8. shadcn/ui Setup (One-Time)

Run once before Session 4:

```bash
cd frontend
npx shadcn@latest init -t next
```

```css
/* globals.css — Tailwind v4 CSS-first config */
@import "tailwindcss";
@import "tw-animate-css";

@theme {
  --color-sidebar-bg: #1e3a5f;
  --color-primary: #e03131;
  --color-surface-light: #f4f7fb;
  --color-border: #e2e8f0;
  --color-text-main: #0f172a;
  --color-text-muted: #64748b;
  --color-status-high: #dc2626;
  --color-status-medium: #f97316;
  --color-status-low: #6b7280;
  --color-status-blocked: #dc2626;
  --color-status-throttled: #f97316;
  --color-status-logged: #6b7280;
  --color-status-ratelimited: #8b5cf6;
}
```

> **`tailwindcss-animate` is deprecated** (March 2025). shadcn's CLI now uses `tw-animate-css`. After init, verify `globals.css` imports `tw-animate-css`, not `tailwindcss-animate`. If you see the old package, replace it.

Components to add (add them as you need them in sessions):
```bash
npx shadcn@latest add button badge table checkbox input card
npx shadcn@latest add dropdown-menu tooltip sheet
npx shadcn@latest add skeleton      # used in loading.tsx files
```

---

## 9. Prompt Template for AI Sessions

Paste at the top of **every** code generation session:

```
Stack constraints (non-negotiable):
- Next.js 15 App Router, TypeScript strict mode
- Tailwind CSS ONLY — no inline styles, no CSS modules
- shadcn/ui components for interactive primitives
- 'use client' ONLY if component uses: useState, useEffect, event handlers, 
  browser APIs, custom hooks, or TanStack Query/Zustand hooks
- Import types from @/features/[feature]/types
- Import constants from @/lib/constants
- Import cn() from @/lib/utils
- Props MUST be fully typed — no 'any', no implicit types
- No hardcoded mock data inside components — all data comes via props or hooks
- Confidence: LOW <50% (gray), MEDIUM 50-80% (orange), HIGH >80% (red)
- Color tokens: sidebar-bg=#1e3a5f, primary=#e03131, surface=#f4f7fb
- Use isPending not isLoading (TanStack Query v5 — isLoading is removed, silently fails)
- Use queryOptions() factory for all query definitions — not raw queryKey/queryFn objects
- Tailwind v4: no tailwind.config.ts — design tokens go in globals.css @theme block
```

---

## 10. PD1 vs PD2 Checklist

| What changes in PD2 | File to edit | Nothing else changes |
|---|---|---|
| Real alerts data | `app/api/alerts/route.ts` | ✅ |
| Real stats | `app/api/stats/route.ts` | ✅ |
| Real ML health | `app/api/ml-health/route.ts` | ✅ |
| Live polling | `features/alerts/queries.ts` — add `refetchInterval` | ✅ |
| Auth header to FastAPI | `app/api/*/route.ts` — add Authorization header | ✅ |
| Delete mock data | `mocks/` directory | ✅ |

Components, hooks, Zustand store — **zero changes** between PD1 and PD2.

---

## 11. Security & Version Constraints

### CVE-2025-29927 — Middleware Auth Bypass (CVSS 9.1)

**Affected**: Next.js 11.1.4 through 15.2.2
**Fix**: Upgrade to `next >= 15.2.3`
**Impact**: Allows complete bypass of middleware-based authentication checks. An attacker can access protected routes without a valid session.

**Required actions**:
1. Pin `"next": ">=15.2.3"` in `package.json`
2. `middleware.ts` **must exist** at the project root — if it doesn't exist, there is no auth protection
3. `auth.config.ts` (edge-compatible) is imported by `middleware.ts` to validate sessions

```typescript
// middleware.ts
import NextAuth from 'next-auth'
import { authConfig } from './auth.config'

export const { auth: middleware } = NextAuth(authConfig)

export const config = {
  matcher: [
    // Protect all dashboard pages
    '/(dashboard|alerts|ml-health)(.*)',
    // Protect all /api routes EXCEPT /api/auth (NextAuth callbacks)
    '/api/((?!auth).*)',
  ],
}
```

> ⚠️ The `/api/auth` exclusion in the matcher is required. Without it,
> middleware blocks NextAuth's own OAuth callback and session endpoints
> at `/api/auth/[...nextauth]`, breaking login entirely.

---

## 12. Testing Checkpoints Per Session

```
Session 1 end:  npx tsc --noEmit — types + utils must compile clean
                lib/searchParams.ts: npx tsc --noEmit must pass on this file
Session 2 end:  curl localhost:3000/api/alerts → 200 + valid mock JSON
                curl localhost:3000/api/stats  → 200 + valid mock JSON
Session 3 end:  npx tsc --noEmit — all files in features/ and store/
                must compile clean with zero errors.
                Manual smoke test: add a temporary console.log in
                providers.tsx to confirm QueryClient initializes once
                (check React DevTools — should show exactly 1
                QueryClientProvider in the tree). Remove after check.
Session 4 end:  localhost:3000/dashboard loads without console errors
                or hydration warnings in browser DevTools
Session 5 end:  Create app/dev/page.tsx — render all atomic UI components
                with hardcoded props. Verify visually. Delete after session.
Session 6 end:  Nav active state correct on route change.
                TopBar severity pill updates URL (?severity=HIGH), not Zustand.
Session 7 end:  AlertsTable rows clickable. IncidentPanel opens.
                Bulk selection updates Zustand selectedAlertIds correctly.
Session 8 end:  Full page renders. loading.tsx skeleton visible on
                Chrome DevTools → Network → Slow 3G throttle.
                error.tsx renders when /api/alerts route.ts throws.
```

---

## 13. File Count Summary

| Category | Files | Type |
|---|---|---|
| App routes + layouts | 11 | Mixed RSC / redirect (includes not-found.tsx at app root) |
| Route `loading.tsx` + `error.tsx` | 6 | Mixed (error = `'use client'`) |
| Route handlers (BFF) | 4 | Server-only |
| Auth + middleware | 3 | `middleware.ts`, `auth.ts`, `auth.config.ts` |
| Layout components | 5 | Mixed |
| Dashboard components | 8 | Mixed |
| Atomic UI components | 4 | RSC |
| Feature queries | 3 | `'use client'` hooks |
| Types | 3 | Pure TS |
| Mocks (PD1 only) | 3 | Pure TS |
| Store | 1 | `'use client'` |
| Config + lib | 4 | Mixed |
| **Total** | **~54** | |

Clean, traceable, testable. Each file has one job.
