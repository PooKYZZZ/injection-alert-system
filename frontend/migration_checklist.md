# WAF-ML SOC — HTML → Next.js 15 Migration Checklist
**Team 13 | DICT Capstone**

> **HOW TO USE:** Each task = one new AI conversation.
> Copy the task block + paste the migration analysis as context.
> Do not combine tasks. Complete in order unless marked PARALLEL.

---

## LEGEND
- 🔴 PD1 CRITICAL — must be done before the demo
- 🟡 PD1 NICE TO HAVE — do if time allows
- 🟢 POST PD1 — can wait until PD2
- ⚡ PARALLEL — can be worked on simultaneously with another task
- ⚠️ HIGH RISK — missing a sub-step causes silent failure

---

## TASK 1: Scaffolding the Next.js App Router Architecture
**Status:** 🔴 PD1 CRITICAL
**Requires:** None
**Parallel with:** None
**Estimated effort:** 2 hours
**Owner suggestion:** Frontend Lead

### What this task produces
A clean, compiling Next.js 15 app router project directly inside the `injection-alert-system/frontend/` directory, configured with Tailwind CSS v4, shadcn/ui, self-hosted fonts, and the standard root directory structure required by the migration plan. It will serve a blank `app/page.tsx` on `localhost:3000`.

### Sub-checklist
- [ ] Scaffold Next.js 15 app
  - Navigate to the project root: `cd injection-alert-system`
  - Remove the existing `frontend/README.md` if it blocks installation, then run:
  - `npx create-next-app@15 frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`
- [ ] Install Shadcn UI CLI & Radix base primitives
  - Navigate to `frontend/`: `cd frontend`
  - Run: `npx shadcn@latest init` (Select Default style, Slate color, CSS variables: `yes`)
- [ ] Install self-hosted fonts
  - Run: `npm install @fontsource/inter @fontsource/ibm-plex-sans`
  - Modify `src/app/layout.tsx` to import the font CSS globals instead of `next/font/google` if preferred, or configure `next/font/google` explicitly inside `layout.tsx` for Inter/IBM Plex.
- [ ] Create folder structure
  - Create `frontend/src/components/ui/`
  - Create `frontend/src/components/layout/`
  - Create `frontend/src/stores/`
  - Create `frontend/src/services/`
  - Create `frontend/src/hooks/`
  - Create `frontend/src/types/`
- [ ] Configure Tailwind CSS tokens
  - Edit `frontend/tailwind.config.ts` (or `app/globals.css` if using v4 variable injection) to include prototype colors: `sidebar-bg`, `primary`, `status-high`, etc.

### Verification
- [ ] `npm run dev` starts successfully.
- [ ] `http://localhost:3000` renders with no console errors and the correct fonts applied.
- [ ] Git commit initial scaffold.

### Fallback
None. This is foundational.

---

## TASK 2: OpenAPI Type Generation & Base API Client
**Status:** 🔴 PD1 CRITICAL
**Requires:** Task 1, FastAPI backend running locally
**Parallel with:** Task 3 (Auth setup)
**Estimated effort:** 1.5 hours
**Owner suggestion:** Full-stack/Backend Engineer

### What this task produces
A fully typed API client. Instead of manually writing interfaces, this step grabs the `openapi.json` from the running FastAPI backend and generates exactly matching TypeScript definitions in `src/types/api-types.ts`.

### Sub-checklist
- [ ] Install openapi-typescript package
  - Ensure you are in the `frontend/` directory.
  - Run: `npm install -D openapi-typescript`
- [ ] Generate types from FastAPI
  - Ensure FastAPI is running locally (e.g., at `http://127.0.0.1:8000`)
  - Run: `npx openapi-typescript http://127.0.0.1:8000/openapi.json -o src/types/api-types.ts`
- [ ] Create base API client
  - Create `frontend/src/services/api.ts`
  - Setup a base `fetch` wrapper or `axios` instance configured to point to Next.js API route handlers (e.g., `baseURL: '/api'`), NOT directly to FastAPI.
- [ ] Optional: Install Zod
  - Run: `npm install zod`

### Verification
- [ ] Open `frontend/src/types/api-types.ts` and confirm interfaces like `Alert` and `PredictResponse` exist and match the Python models.
- [ ] A test import in a Next.js file (`import { paths } from '@/types/api-types'`) throws no TS errors.

### Fallback
Manually write out 5–6 critical TypeScript interfaces in `types/index.ts` if the openapi generator fails to parse the FastAPI schema perfectly.

---

## TASK 3: Authentication Layer (NextAuth.js & Middleware)
**Status:** 🔴 PD1 CRITICAL | ⚠️ HIGH RISK
**Requires:** Task 1
**Parallel with:** Task 2 (Type Generation)
**Estimated effort:** 3 hours
**Owner suggestion:** Backend Engineer

### What this task produces
A protected application. All routes under `/` will redirect to `/login` if no valid session is present. The Next.js API routes will have access to the JWT to securely proxy requests to FastAPI.

### Sub-checklist
- [ ] Install NextAuth.js (v5 Beta recommended for App Router compatibility)
  - Ensure you are in the `frontend/` directory.
  - Run: `npm install next-auth@beta`
- [ ] Create NextAuth configuration
  - Create `frontend/src/auth.ts` defining the providers (Credentials provider wrapping the FastAPI `/login` endpoint).
  - Create `frontend/src/app/api/auth/[...nextauth]/route.ts` bridging `auth.ts`.
- [ ] Implement Route-Level Middleware
  - Create `frontend/src/middleware.ts` in the root (next to `src/`).
  - Configure the matcher logic: protect `/`, `/alerts`, `/settings`, etc.; whitelist `/login`, `/api/auth`.
- [ ] Build Login Page
  - Create `frontend/src/app/login/page.tsx`.
  - Add simple username/password form calling NextAuth `signIn('credentials', ...)`.
- [ ] Update Environment Variables
  - Add `AUTH_SECRET` (generate using `npx auth secret`) and backend auth URLs to `frontend/.env.local`. Ensure they do NOT start with `NEXT_PUBLIC_`.

### Verification
- [ ] Navigating to `localhost:3000` redirects to `/login`.
- [ ] Submitting valid credentials on `/login` redirects back to `/` with a valid session cookie.

### Fallback
Hardcode a single fallback static JWT in server-side Next.js route handlers and skip the UI login flow entirely for the PD1 demo if NextAuth integration delays shipping.

---

## TASK 4: Next.js API Routes Proxy
**Status:** 🔴 PD1 CRITICAL | ⚠️ HIGH RISK
**Requires:** Task 2, Task 3
**Parallel with:** Task 5 (Zustand/Query setup)
**Estimated effort:** 2.5 hours
**Owner suggestion:** Full-stack/Backend Engineer

### What this task produces
A secure bridge where the Next.js server talks to FastAPI, Groq, and Supabase. The browser only talks to the Next.js server. Secrets are completely isolated from the CSR (Client Side Rendered) components.

### Sub-checklist
- [ ] Create REST Proxies
  - Create `frontend/src/app/api/stats/route.ts` that fetches from FastAPI `/api/stats`, attaches the NextAuth JWT, and returns the response.
  - Create `frontend/src/app/api/alerts/route.ts` (GET and POST for fetching and labeling).
- [ ] Create LLM Proxy
  - Create `frontend/src/app/api/explain/route.ts`.
  - Logic: Receives `alertId`. Next.js fetches alert details from FastAPI (or Supabase directly), wraps it in a prompt, securely calls Groq REST API using the `GROQ_API_KEY` environment variable within `frontend/.env.local`, and returns the string response.
- [ ] Optional: Supabase Data Fetch
  - If bypassing FastAPI for direct reads, install `@supabase/supabase-js`, initialize it in `route.ts` using `DATABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`.

### Verification
- [ ] Browser network tab shows requests going to `localhost:3000/api/stats`, NOT `localhost:8000/api/stats`.
- [ ] Output of `/api/stats` contains valid JSON.
- [ ] The browser source code and network requests do NOT contain the `GROQ_API_KEY`.

### Fallback
None. Hiding the Groq API key and handling CORS securely demands this proxy layer.

---

## TASK 5: State Management & TanStack Query Config
**Status:** 🔴 PD1 CRITICAL
**Requires:** Task 1
**Parallel with:** Task 4 (Proxy Setup)
**Estimated effort:** 1 hour
**Owner suggestion:** Frontend Lead

### What this task produces
The global providers necessary for fetching server state (alerts, stats) and managing client UI state (which rows are selected, is the incident panel open?).

### Sub-checklist
- [ ] Install dependencies
  - Ensure you are in the `frontend/` directory.
  - Run: `npm install @tanstack/react-query zustand`
- [ ] Setup QueryProvider
  - Create `frontend/src/components/providers/query-provider.tsx`.
  - Wrap `children` in `QueryClientProvider`.
  - Mount `QueryProvider` inside `frontend/src/app/layout.tsx`.
- [ ] Scaffold Zustand Store
  - Create `frontend/src/stores/useAlertStore.ts`.
  - Define state: `selectedAlertIds: Set<string>`, `activeIncidentId: string | null`.
  - Define actions: `toggleAlert(id)`, `clearSelection()`, `openIncident(id)`, `closeIncident()`.

### Verification
- [ ] React Developer Tools show `QueryClientProvider` mounted in the tree.
- [ ] A dummy Zustand store `console.log()` inside a client component outputs the correct default state.

### Fallback
Use standard React `useState` and `useEffect` if Query/Zustand setup fails, but performance will significantly degrade on polling.

---

## TASK 6: Building the Dashboard UI (Static to React)
**Status:** 🔴 PD1 CRITICAL
**Requires:** Task 1, Task 5
**Parallel with:** Task 7 (Real-time SSE)
**Estimated effort:** 4 hours
**Owner suggestion:** Frontend Engineer

### What this task produces
The `app/page.tsx` now contains the fully styled dashboard (KPI cards, Sidebar, Comparison panel) migrated from the static HTML but broken into composable React Client/Server components.

### Sub-checklist
- [ ] Extract the Sidebar layout
  - Create `frontend/src/components/layout/Sidebar.tsx`.
  - Apply the `#1e3a5f` styling and static links.
- [ ] Implement KPI Stat Cards
  - Create `frontend/src/components/ui/StatCard.tsx`.
  - Create `frontend/src/app/page.tsx` layout putting cards in a grid.
- [ ] Build the CRS vs ML Comparison Banner
  - Create `frontend/src/components/dashboard/ComparisonBanner.tsx`.
- [ ] Hook up TanStack Query
  - In a client component (or Server Component if fetching at render time), invoke `useQuery({ queryKey: ['stats'], queryFn: fetchStats })`.
  - Pass the dynamic data to the `StatCard` and `ComparisonBanner`.
  - Add Skeleton loaders (`frontend/src/components/ui/skeleton.tsx` from shadcn) for the `isLoading` state.

### Verification
- [ ] The UI looks identical to the HTML prototype screenshot.
- [ ] If the FastAPI server is shut down, the UI gracefully falls back to an error state or skeleton loader instead of crashing.

### Fallback
Hardcode the data props if the backend API isn't ready in time for the Demo, but keep the React component structure.

---

## TASK 7: Alert Table & Data Grid
**Status:** 🔴 PD1 CRITICAL
**Requires:** Task 6
**Parallel with:** None
**Estimated effort:** 3 hours
**Owner suggestion:** Frontend Engineer

### What this task produces
The core analyst view. A sortable, selectable table displaying historical alerts.

### Sub-checklist
- [ ] Install TanStack Table
  - Ensure you are in the `frontend/` directory.
  - Run: `npm install @tanstack/react-table`
- [ ] Build the Column Definitions
  - Create `frontend/src/components/alerts/columns.tsx` defining the mappings (Timestamp, Severity, Score, Path, Attack Type, Action).
  - Implement custom cell renderers for the Severity badges (`status-high`, etc.).
- [ ] Build the DataTable Component
  - Create `frontend/src/components/alerts/DataTable.tsx`.
  - Feed it data via `useQuery(['alerts'], fetchHistoricalAlerts)`.
- [ ] Wire up Checkboxes to Zustand
  - Connect row selection changes to `useAlertStore.getState().toggleAlert()`.

### Verification
- [ ] The table renders 20+ rows successfully from the Next.js API route.
- [ ] Selecting a checkbox updates the "X Selected" counter in the UI.

### Fallback
Render a standard HTML `<table>` mapping over the array (`alerts.map()`) without TanStack Table if pagination/sorting math becomes a blocker for PD1.

---

## TASK 8: Real-Time SSE Integration (Live Alerts)
**Status:** 🔴 PD1 CRITICAL | ⚠️ HIGH RISK
**Requires:** Task 4 (Proxy), Task 7 (Table)
**Parallel with:** Task 9 (Incident Panel)
**Estimated effort:** 3 hours
**Owner suggestion:** Backend/Full-stack Engineer

### What this task produces
Rows automatically prepend to the alert table without the user refreshing the page when a new attack is detected.

### Sub-checklist
- [ ] Create Next.js SSE Route Handler
  - Create `frontend/src/app/api/stream/alerts/route.ts`.
  - Fetch the stream from FastAPI `StreamingResponse`.
  - Return a `new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } })`.
- [ ] Consume SSE in React
  - Create `frontend/src/hooks/useAlertStream.ts`.
  - Use the native `EventSource` API pointing to `/api/stream/alerts`.
  - On message receipt, update the TanStack Query cache dynamically (`queryClient.setQueryData(['alerts'], (old) => [newAlert, ...old])`).

### Verification
- [ ] Network tab shows a pending `text/event-stream` connection.
- [ ] Manually triggering a cURL attack against ModSecurity causes a new row to instantly appear in the React table.

### Fallback
Drop SSE. Use TanStack Query polling at a 5-second interval: `useQuery({ ..., refetchInterval: 5000 })`. It is heavier on the server but functionally identical for the demo.

---

## TASK 9: Incident Detail Panel & Recharts
**Status:** 🔴 PD1 CRITICAL
**Requires:** Task 5, Task 6
**Parallel with:** Task 8
**Estimated effort:** 2.5 hours
**Owner suggestion:** Frontend Engineer

### What this task produces
The sliding right-hand panel showing deep specifics of a selected attack, the SHAP feature contribution charts, and the LLM explanation.

### Sub-checklist
- [ ] Install Recharts
  - Ensure you are in the `frontend/` directory.
  - Run: `npm install recharts`
- [ ] Build Incident Panel Layout
  - Create `frontend/src/components/alerts/IncidentPanel.tsx`.
  - Make it conditionally render based on `useAlertStore((state) => state.activeIncidentId)`.
- [ ] Sanitize Payload Display
  - STRICT REQUIREMENT: Render the HTTP payload string inside a `<pre><code>{payload}</code></pre>` block. Ensure ESLint flags any use of `dangerouslySetInnerHTML`.
- [ ] Implement Recharts for SHAP
  - Create a custom horizontal `BarChart` matching the HTML CSS values for Feature Contribution.
- [ ] Wire up the Groq Explanation Button
  - Click "Explain" -> trigger mutation to `/api/explain` -> render resulting text string.

### Verification
- [ ] Clicking a table row opens the panel with correct dynamic data.
- [ ] Clicking the "X" closes the panel.
- [ ] Recharts displays SHAP values accurately.

### Fallback
Hardcode the SHAP values using plain CSS widths (`width: 80%`) representing the fallback dummy data if Recharts integration is messy.

---

## TASK 10: Analyst Actions & Feedback Loop
**Status:** 🟡 PD1 NICE TO HAVE
**Requires:** Task 9
**Parallel with:** None
**Estimated effort:** 2 hours
**Owner suggestion:** Frontend Engineer

### What this task produces
The UI for analysts to "Mark False Positive" and "Apply Mitigation", closing the ML retraining loop.

### Sub-checklist
- [ ] Create Feedback Modal
  - Create `frontend/src/components/alerts/FeedbackModal.tsx`.
  - Form UI: Radio buttons (TP / FP), Textarea (Reason).
- [ ] Wire Mutation
  - Use `useMutation({ mutationFn: submitFeedback })` pointing to `/api/feedback`.
- [ ] Confirmation Guard for Mitigation
  - Create a generic Confirmation Dialog (`shadcn/ui` AlertDialog).
  - Wrap the "Apply Mitigation" button. Prevent POST to `/api/mitigate` unless confirmed.

### Verification
- [ ] Clicking "Mark False Positive" opens the modal. Submitting sends a 200 OK POST request exactly matching the FastAPI schema.
- [ ] Clicking "Apply Mitigation" halts with an "Are you sure?" modal before firing.

### Fallback
Skip the Modal. Have the buttons instantly fire a hardcoded "False Positive" JSON payload to the backend just to prove the API connection works for the demo.

---

## TASK DEPENDENCY MAP
```text
Task 1 (Scaffold)
 ├── Task 2 (OpenAPI Types) ────┐
 ├── Task 3 (Auth / NextAuth) ──┤
 │                              ├── Task 4 (API Proxies) ──┐
 ├── Task 5 (Zustand/Query) ────┤                          │
 │                              │                          │
 └────── Task 6 (Base UI / KPI Cards) ─────────────────────┤
                                                           │
                      ┌────────────────────────────────────┘
                      │
            Task 7 (Data Table)
                      │
          ┌───────────┴───────────┐
Task 8 (SSE Stream)      Task 9 (Incident Panel)
                                  │
                         Task 10 (Feedback Loop)
```

---

## PD1 MINIMUM VIABLE DEMO CHECKLIST
The exact subset of tasks that must be green for a passing PD1 demo.
- [ ] **Task 1: Scaffolding** complete
- [ ] **Task 3: Authentication** complete (cannot demo without basic login)
- [ ] **Task 4: API Proxies** complete (secure route to FastAPI)
- [ ] **Task 6: Base UI** complete (static visuals match prototype)
- [ ] **Task 7: Data Table** complete (alerts load from API)
- [ ] **Task 9: Incident Panel** complete (displays details safely)

*(Tasks 2, 8, and 10 can be manual workarounds or skipped if time absolutely expires).*
