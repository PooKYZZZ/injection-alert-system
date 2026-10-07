# CyberTrace Usability, Retention, and Access Improvements

**Research date:** 2026-10-04
**Plan status:** Proposed only; no application implementation is included.

This is one self-contained document: codebase findings and external research come first, followed by the codebase-specific implementation plan.

## Contents

- [Research](#research)
  - [Executive recommendation](#executive-recommendation)
  - [Current CyberTrace behavior](#current-cybertrace-behavior)
  - [Research findings and recommendations](#research-findings-and-recommendations)
  - [Options considered](#options-considered)
  - [Research sources](#research-sources)
- [Implementation plan](#implementation-plan)
  - Baseline, authentication, roles, manual export, retention/archive decision, visual refinement, guided tour, and regression phases.

Read the research for the findings and recommended direction; continue to the implementation plan for affected code areas, sequencing, gates, and acceptance criteria.

## Research

### Executive recommendation

The smallest defensible direction is to improve the experience around the existing system rather than introduce a new data platform:

1. Keep the traffic log table as the canonical source for Traffic History. It already has timestamp query paths and indexes, and evidence tables refer to its IDs. Do not split, delete, or move rows just to create a seven-day screen.
2. Treat the time shown by default in the UI separately from data retention. Keep short chart presets (currently 1h, 6h, 24h, and 7d), allow Traffic History searches and manual exports over explicit historical ranges, and choose an actual retention policy only after measuring volume and confirming academic/privacy obligations.
3. Give Admin and Analyst, and the existing full-privilege Owner, a manual export with a user-selected date range. Use a server-side bounded query, a fixed allowlist of useful fields, UTC timestamps, explicit formula-injection handling, and an existing audit mechanism where it fits. Do not let Viewer bulk-export by default.
4. Keep manual range export distinct from any automated monthly archive. A monthly job, if later justified, should produce a calendar-month artifact through its own schedule and idempotent process. It must not constrain manual ranges, and CSV must not become the sole canonical copy of audit data.
5. Do not add a second archive table, file archive, partitioning, scheduler, or database extension yet. No measured Traffic History volume or active archive/export job was found, and there is no evidence that the current indexed table is over capacity. Confirm live DB migration and backup state before relying on either.
6. Fix authentication defects before polishing those screens. Trace recent-TOTP behavior end to end without weakening the gate; trace reset-link replacement, expiry, URL configuration, and actual email delivery. Preserve documented response semantics unless the product owner changes them.
7. Keep the CyberTrace visual identity and current component system. Improve hierarchy, density, chart explanation, accessibility, responsive behavior, and interaction details in place. Use a short, optional, replayable spotlight tour rather than a forced onboarding campaign.

**Retention conclusion:** Seven days is a reasonable dashboard default, not an evidenced retention period. Fourteen days is also arbitrary without a volume or investigation requirement. Thirty days is a useful initial period to measure and a plausible review horizon for analyst demonstrations, but it is not a reason by itself to move or delete records. The evidence supports one indexed table and date filters, not a specific automatic expiry period. If policy requires an interim decision before metrics are available, use 30 days as a provisional review point, preserve data pending an approved disposal rule, and revisit after collecting actual growth and investigation data.

### Method and confidence

This review checked live source, migrations, tests, architecture/operations documents, current UI, API/BFF paths, and Docker configuration. Older improvement plans were not used as design authority. The prior retention-policy document was checked only to distinguish policy proposals from runtime behavior.

External evidence is ranked as follows:

- **High confidence:** standards, official framework/database/security documentation, and peer-reviewed or well-described academic research.
- **Medium confidence:** official product documentation, which shows real product patterns but is not a universal usability rule.
- **Low confidence:** forum and Reddit observations, included as practitioner anecdotes only.

The working tree contains unrelated existing edits. This research and plan are intended to be the only new files for this task.

### Current CyberTrace behavior

| Area | Observed in source | Unknown or not implemented |
|---|---|---|
| Architecture | Next.js App Router routes act as the browser-facing BFF; FastAPI owns backend API behavior; async SQLAlchemy persists traffic data in PostgreSQL. Root Compose runs app containers; local Compose adds PostgreSQL with a named volume. | Current hosted DB state and deployment-specific replica count are not proven by repository source. |
| Traffic records | ORM model TrafficLog maps to traffic_logs, with timestamps, action/prediction/confidence, request metadata, and sensitive fields such as IP, query string, raw request, and persisted model input. TrafficLogActionHistory is append-oriented and references traffic rows with ON DELETE RESTRICT; other evidence/enforcement records also reference traffic IDs. | Expected live records/day, retained byte size, query latency, current backup plan, and legal/adviser retention requirement. |
| Querying | Repository paths apply timestamp >= start and timestamp < end. Migrations add time indexes, including a PostgreSQL BRIN index. BRIN can help where physical row order correlates with time, but benefit must be measured on real data. | Query plans and representative production-like scale. No evidence establishes that the table is too large. |
| Dashboard | Dashboard time windows are 1h, 6h, 24h, and 7d. Timeline series are calculated from stored action_taken; the UI uses “recorded” action language and chart text explains the series. | An accessible tabular equivalent for every chart value was not confirmed in the inspected component. |
| Traffic History | The page uses an existing filter bar and alerts client. Filters include time window (including ALL), recorded action, confidence, triage, and normal-traffic inclusion. Query state is URL-backed. | No custom calendar date range was observed in the current filter contract. |
| Archive/export | No Traffic History CSV route, Content-Disposition response, or traffic archive job was found. Existing model/retraining exports are separate. A runbook describes backup/restore but is not an automated backup. | Actual database backup coverage, Supabase plan, object storage, archive recovery tests, and hosted migration head. |
| Roles | Current roles are OWNER, ADMIN, ANALYST, and VIEWER. Viewer has read/statistics access only. Admin and Analyst can read/triage; Admin has account management and action-update privileges. Owner inherits full access. Authorization is permission-based. | Whether live database RPC definitions and the current migration head exactly match the repository. |
| Account lifecycle | auth_accounts.disabled_at is used to enable/disable accounts. The UI already shows Active, Disabled, and Pending setup and confirms disabling. Account-management operations write security events and update authorization version. | Whether UI terminology should say “Suspended” or “Disabled”; no new lifecycle enum is evident as necessary. |
| Recent TOTP | Role and account-status PATCH routes require requireRecentTotp with account-management permission. The guard requires MFA/TOTP claims and a recent auth_time; verified MFA completion is mapped to session claims by frontend/auth.ts. | The recurring failure was not reproduced in this read-only review. Root cause remains **Unknown**; hosted RPC/schema alignment is also unknown. |
| Password reset | Frontend/API/database code creates reset tokens with a 30-minute expiration; only a token digest is persisted. SQL token creation replaces earlier pending reset tokens. Consumption enforces pending/unexpired use and changes the password. The documented flow intentionally returns 404 for an ineligible/nonexistent account and 200 queued for eligible accounts. | Email provider delivery, outbox failure/retry state, active environment URL/domain configuration, request throttling across layers, and which link a user actually opened. Secret values were not inspected. |
| Onboarding and design | CyberTrace has a custom tokenized Tailwind CSS v4 visual system, Radix dialogs, Motion, Recharts, Lucide, Help & Guide, and common loading/error/empty states. No first-run spotlight tour was found. Reduced-motion support exists for theme transitions and some authentication styling; motion should be audited component by component. | Full browser rendering, screen-reader behavior, touch testing, and cross-viewport quality were not verified. |

Relevant implementation sources include docs/architecture.md, docs/CONTEXT.md, docs/SETUP.md, docs/project-ops/RETENTION_POLICY.md, docs/project-ops/BACKUP_RESTORE_RUNBOOK.md, web_app/infrastructure/database/database.py, web_app/infrastructure/repositories/traffic_log_repository.py, migrations/versions/20260322_000005_add_performance_indexes.py, migrations/versions/20260930_000031_cybertrace_evidence_history.py, frontend/lib/searchParams.ts, the Traffic History and Dashboard pages, frontend/lib/auth/roles.ts, frontend/lib/auth/route-guard.ts, frontend/auth.ts, and frontend/lib/server/db/password-recovery.ts.

#### Important evidence boundaries

- docs/project-ops/RETENTION_POLICY.md is policy documentation, not proof of a running retention job or current database behavior.
- docs/project-ops/BACKUP_RESTORE_RUNBOOK.md describes a procedure; it does not establish that automated backups are enabled or restorable.
- The repository migration head is 20260930_000031, but hosted migration state was not queried. The architecture document records older schema evidence, so that snapshot must not be described as current.
- Model/retraining archive files do not constitute Traffic History archives.
- A healthy local container, passing API test, or index in a migration would not prove hosted retention, database backup, or production query performance.

### Research findings and recommendations

#### 1. Visual design: information first, with a deliberate identity

WCAG 2.2 provides testable boundaries for contrast, keyboard focus, reflow, target size, focus visibility, and accessible authentication. It does not require a sterile visual style. WAI-ARIA modal-dialog guidance explains focus placement, contained keyboard navigation, Escape behavior, and focus restoration. Fluent 2 typography, spacing, token, and motion guidance shows how consistent hierarchy can coexist with product personality. Carbon’s data-table guidance treats filtering, sorting, column choices, and bulk actions as part of the table workflow.

The industry products named in the request use recurring patterns that transfer well:

- **Elastic Security and Microsoft Sentinel:** put time scope, severity, filters, and investigation context near the data they affect; make counts and charts lead to records ([Elastic](https://www.elastic.co/guide/en/security/current/detection-response-dashboard.html), [Sentinel](https://learn.microsoft.com/en-us/azure/sentinel/datalake/kql-queries)).
- **Grafana and Datadog:** use clearly labeled time controls, including absolute ranges where historical investigation needs them; Datadog distinguishes browser-local selection from UTC queries and offers density controls ([Grafana](https://grafana.com/docs/grafana/latest/visualizations/dashboards/use-dashboards/), [Datadog time frames](https://docs.datadoghq.com/dashboards/guide/custom_time_frames/), [Datadog dashboard configuration](https://docs.datadoghq.com/dashboards/configure/)).
- **Cloudflare Log Explorer and Splunk:** provide visible filters and columns for dense records; preserve analyst control and a path from summary to evidence ([Cloudflare](https://developers.cloudflare.com/log-explorer/log-search/), [Splunk](https://help.splunk.com/en/splunk-enterprise-security-7/user-guide/7.3/incident-review/triage-notables-on-incident-review-in-splunk-enterprise-security)).
- **Sentry:** saved Discover queries expose time scope, fields, grouping, filters, and result limits, illustrating that scope and columns are part of an analytics workflow ([Sentry Discover API](https://docs.sentry.io/api/discover/create-a-new-saved-query/)).
- **Linear, GitHub, and Vercel:** Linear describes balancing hierarchy, density, alignment, and contrast; GitHub Primer exposes shared accessibility and design-token foundations; Vercel shows scoped search and visible filters ([Linear redesign](https://linear.app/now/how-we-redesigned-the-linear-ui), [GitHub Primer](https://primer.style/), [Vercel logs](https://vercel.com/docs/logs/runtime)).
- **Intercom:** keep tours short, targeted, and easy to skip/restart rather than using long compulsory sequences.

These are patterns, not designs to copy. A useful CyberTrace balance is:

- Use rich visual hierarchy for the page title, time scope, important risk/recorded-action summaries, and a few primary visualizations.
- Use restrained surface differences, typography, spacing, and line weight to distinguish sections. Do not make every region a large rounded card; reserve stronger elevation and color for meaningful grouping or status.
- Keep dense record lists compact enough for comparison. Use labels, column alignment, short status text, stable sort behavior, and an obvious active-filter summary. Let a row or detail panel expose deeper evidence progressively.
- Use color as a redundant semantic signal, with text/icon support. Do not rely on red/amber/green alone, especially for recorded actions and confidence.
- Make contextual help answer “what does this number mean?” and “what can I do next?” where that question arises. Existing Help & Guide can remain the deeper reference.
- Use subtle feedback for actions and transitions. Every motion needs a purpose; honor prefers-reduced-motion for chart/tour/entry transitions as well as existing theme animation.
- Do not trade brand character for whitespace without cause. Establish a limited CyberTrace-specific motif in typography, icon treatment, section labels, or data marks. Avoid neon glow, arbitrary gradients, and animated decoration.

**Simple when:** a control is familiar, the task is frequent, data is dense, or a transition should not distract.
**Richer when:** a visual distinction explains risk/action scope, a drill-down reduces mental joins, a preview prevents a mistake, or animation helps track a state change.
**CyberTrace application:** preserve the present visual system and make deliberate refinements; do not replace the dashboard with a generic SaaS template.

##### Guidance by interface element

| Element | Research synthesis | CyberTrace recommendation |
|---|---|---|
| Typography and spacing | Fluent, Primer, and Carbon use shared type/space tokens to show hierarchy and align controls. | Keep current tokens; distinguish page titles, section headings, metrics, labels, and supporting text. Use consistent spacing rather than adding whitespace uniformly. |
| Cards and dashboard composition | Datadog allows a denser dashboard mode; Linear's redesign describes hierarchy, alignment, and density as deliberate design variables. | Keep the current composition and visual personality. Use a small number of emphasized KPI cards, then group related visualizations; avoid giving every panel equal weight or elevation. |
| KPIs | Security/observability tools use summary metrics as entry points into scoped evidence. | Label the population and time window for each KPI; distinguish request/traffic totals from recorded actions and verified HTTP outcomes. Make useful counts link to corresponding filtered records. |
| Tables and data density | Carbon recommends a toolbar for global table actions, consistent row sizing, sorting, expansion, and pagination. | Keep Traffic History dense and scan-friendly; make filters, date scope, sort, and export part of a compact toolbar. Use row expansion or a detail panel for secondary evidence. |
| Navigation and account menus | Linear and GitHub show persistent navigation, clear current context, and task-appropriate actions; WCAG requires keyboard access and visible focus. | Keep the existing sidebar and account menu. Group account/profile, security, and sign-out actions predictably, and ensure mobile navigation, focus order, and Escape behavior remain clear. |
| Charts and tooltips | WAI guidance requires meaningful alternatives for non-text content; Elastic and Sentinel connect summaries to underlying results. | Keep chart titles/legends, use hover/focus tooltips only as supplemental detail, provide text and a table-equivalent view, and expose the selected range. |
| Contextual help | Progressive disclosure puts concise explanation beside a decision while leaving deeper guidance available. | Retain Help & Guide; add small contextual explanations for confidence, recorded actions, observed status, filters, and export scope. Avoid unexplained icon-only help. |
| Loading, empty, and error states | GOV.UK error guidance associates errors with fields and retains entered values; stable state messaging reduces uncertainty. | Preserve selected filters and form data after errors, announce state changes to assistive technology, and provide a clear retry or next action. Avoid decorative skeletons that imply false progress. |
| Authentication and account lifecycle | Accessible authentication emphasizes labels, password-manager support, paste, errors, and clear status. | Keep Login, recovery, reset, MFA, and step-up visually related. Put the active task first, show loading/success/failure clearly, and make account status and disable/restore consequences explicit. |
| Touch and responsive behavior | WCAG 2.2 includes target-size and reflow criteria; dense tables need intentional small-screen behavior. | Test laptop and narrow mobile widths. Prefer a deliberate scroll/detail treatment over collapsing security evidence into unreadable cards; keep touch targets usable. |
| Color, focus, and motion | WCAG contrast/focus criteria and reduced-motion preferences provide measurable constraints. | Use color redundantly with text/icons, test both themes and focus states, and honor reduced motion for new chart/tour/entry effects. Use motion to indicate cause and effect, not decoration. |

#### 2. Dashboard charts, tables, and terminology

The current dashboard offers a coherent short-window set of 1h, 6h, 24h, and 7d. Keep those choices until usage and query measurements suggest a change. Do not add 30d solely because it is common elsewhere. A longer overview becomes useful only if records remain available, the aggregate is semantically comparable, and the chart remains readable.

Keep the title **Recorded actions over time** while the chart represents stored action_taken. A recorded BLOCKED decision is not proof that the HTTP response was blocked or that the request was prevented. Preserve observed_http_status as a distinct field when available; never silently relabel the chart as confirmed outcomes.

For nontrivial charts, provide a concise textual summary and an accessible table or equivalent data view with the same totals and time buckets. Tooltips should be supplementary, reachable without a pointer where applicable, and not the sole carrier of meaning. Use explicit date/time labels and timezone information. An absolute-range selector may be useful on Traffic History before it belongs on the dashboard.

#### 3. Guided onboarding and spotlight tours

“Product tour,” “guided walkthrough,” “spotlight tour,” and “coach marks” describe related patterns. Intercom’s official guidance frames tours as short task/overview help, recommends a small number of pointer steps for introductory tours, and makes restart or snooze available. This supports a short first-use overview, not a mandatory tutorial on every visit.

Recommended CyberTrace experience:

- One optional first-use Dashboard tour of about 4–5 meaningful steps; a shorter 3–4 step Traffic History tour launched from Help. Do not force both when the user first signs in.
- Provide **Skip**, **Previous**, **Next**, and **Finish**, a visible “step X of Y” indicator, and a persistent Help entry to restart.
- Persist completion/version per user and tour in browser storage for this single-user-per-browser app. A version bump may make new steps eligible once; Skip should suppress automatic replay for that version; explicit Help replay should always work. If users regularly move devices or share browsers, revisit server-side persistence rather than preemptively adding a DB table.
- Use stable data-tour targets, wait for delayed content, skip hidden/missing targets, and use viewport-aware placement. Prefer neutral copy such as “This filter changes the current results” over positional directions.
- On narrow mobile layouts, either reposition the bubble and scroll the target into view or switch to a compact dialog/card sequence. Do not leave controls hidden behind a spotlight mask.
- Support Escape to exit, keyboard operation, focus movement into the current tour surface, clear screen-reader labels/live progress, and focus restoration to the target or original control. Respect reduced motion.

Existing Motion and Radix primitives help with a contained explanation dialog, but a robust spotlight also needs collision detection, target visibility handling, focus behavior, and screen-reader semantics. React Joyride v3 documentation describes React 19 compatibility, Floating UI collision handling, portals, focus management, and keyboard behavior. It is a reasonable small-library candidate, not an approved dependency. Before selecting it, verify package health/license, actual bundle impact, existing dependency overlap, browser/mobile behavior, and whether the tested version matches this project. Repository instructions require approval before adding a dependency. Avoid building a bespoke positioning/focus framework merely to avoid one library.

#### 4. Retention and archive storage

##### Why “seven days recent, then archive” is not a storage recommendation yet

The current code already queries the canonical traffic table by time. The UI can show a short default window without moving records. That is the lowest-cost way to distinguish recent activity from historical investigation.

There is no known traffic volume, growth rate, investigation interval, DB plan, actual backup schedule, or institutional data-retention requirement in the source reviewed. Choosing 7, 14, or 30 days as an automatic deletion/archival boundary would be invented precision. NIST log-management guidance ties retention to requirements and useful analysis rather than a universal duration. Its revision draft is useful context but is a draft, not a binding CyberTrace policy.

| Candidate | Benefits | Costs/risks | CyberTrace view |
|---|---|---|---|
| 7 days | Small recent screen; aligns with current chart preset. | Too short as a data-loss boundary for delayed review, demonstrations, and investigations; no volume evidence supports it. | Keep as a default UI window, not the database retention rule. |
| 14 days | Modest operational buffer. | Still arbitrary and adds a scheduled lifecycle without evidence. | Not a preferred archive threshold without investigation data. |
| 30 days | Gives instructors/analysts more time for delayed review; convenient calendar context. | Not a compliance answer; increases exposure if sensitive request fields are retained; does not prove need for separate storage. | Good provisional measurement/review horizon and plausible UI preset later, not automatic deletion. |
| One indexed table, policy-based retention later | Fewest components; no duplicate/copy reconciliation; historical filters and exports use one canonical record. | DB grows until an approved retention rule; index/query cost needs measurement. | Recommended now. Measure real size and query latency; decide policy after that. |
| Archive table | Keeps one database and permits archive-specific queries. | Requires schema/migration and rethinking foreign keys, child evidence, uniqueness, API reads, and restoration; a row move is not a simple cleanup. | Defer until measured scale/operational need justifies it. |
| Monthly CSV or compressed CSV as sole store | Human-readable and portable; compressed files are smaller. | Append concurrency, partial/corrupt files, duplicate exports, filtering, restore/replay, and backup path must all be solved; relational evidence references no longer resolve naturally. | Do not use as the only canonical archive. CSV is an export, not a database replacement. |
| JSON/JSONL files | Preserves types more predictably than CSV and streams line by line. | Still needs durable storage, manifest, checksum, safe publication, index/search strategy, restore tooling, privacy access, and backup. | Useful for machine interchange in some workflows, but not simpler than the current table. |
| PostgreSQL monthly partitioning | Can make very large time-series retention/drop operations efficient. | Partitioned unique keys must include the partition key; current traffic IDs are referenced by child tables. Requires migration and operational lifecycle work. | Overengineering until volume or maintenance measurements show a bottleneck. |
| Persistent object/file storage | Separates archive files from DB and can support downloads. | Requires storage access controls, durable mounts/backups, lifecycle policy, integrity and restore checks; local container filesystem is not durable. | Future option only if monthly artifacts are a confirmed requirement. |

PostgreSQL documentation positions partitioning for large-table use and warns about unique-key constraints across partitions. BRIN is useful when physical row placement correlates with indexed values; the existing BRIN index is promising but not performance proof. Docker volumes persist container data, whereas the writable container layer is ephemeral. Supabase backup features vary by plan and do not settle every file/object or off-site recovery need; the active CyberTrace plan and backup coverage are unknown.

**Recommendation:** Use traffic_logs as the source for recent history, older history, and export. Keep timestamp indexes and enforce a query range in user-facing paths. Do not archive/delete records just because they fall outside a seven-day UI window. Measure records and bytes per day, query plans/latency at representative ranges, and backup/restore evidence. The first retention decision should be a documented data-handling rule (what fields, whose approval, what purpose, exact expiry), not a file format.

##### Separate monthly workflow

If monthly long-term files are a confirmed project requirement, keep it separate from interactive export:

- The monthly job groups records by a full calendar month. It may emit a monthly archive download/artifact, but it must not restrict manual custom ranges.
- Prefer a complete regenerated month snapshot (or manifest-backed immutable artifact) over appending daily rows to a CSV. Rebuild to a temporary artifact, validate row count/checksum, then atomically publish/replace a manifest or object pointer. Reruns for the same month must have a deterministic identity and must not silently duplicate rows.
- If the archive is only a CSV download convenience, retain database rows as canonical. If it becomes the long-term sole copy, first design recovery, row-link/evidence behavior, access controls, durable storage, integrity checks, and a tested restore path. That is a materially larger change.
- A scheduler should run only after its host, timezone, one-run-at-a-time lock, retry behavior, and monitoring are specified. The application has other scheduled/background work, but no traffic archive job was observed. Supabase Cron is a possible PostgreSQL-native mechanism, but its availability/configuration is unverified and enabling it is a database/deployment change. Do not add it by default.

##### Scheduler options at CyberTrace scale

| Option | Fit and failure mode | Recommendation |
|---|---|---|
| Reuse an existing application scheduler/worker | Avoids a new service, but can run once per API replica or stop during container restart. Requires a verified singleton/leader or database lock, durable job outcome, and safe retry. | First option only if Phase 0 confirms the existing worker lifecycle and deployment topology. |
| Host or Docker scheduled task | Simple to understand and keeps the web process separate, but depends on host configuration, image availability, task logs, and explicit retry/overlap behavior not currently evidenced in the repository. | Reasonable for a single controlled Compose deployment if an operator can monitor and rerun it; otherwise do not add just for this feature. |
| PostgreSQL/Supabase Cron | Runs close to the data and exposes job history, but depends on extension/plan availability, DB privilege/configuration, and migration/deployment approval. It is not verified as enabled today. | Consider only if supported by the actual Supabase project and the archive is approved; do not enable speculatively. |
| Trigger archival when a user opens Traffic History | No dedicated infrastructure, but misses work when nobody visits, can increase page latency, and creates race/authorization complexity. | Reject for automated archival. |

#### 5. Manual CSV export: custom dates, safety, and access

Manual export is a separate user operation from monthly archival. Admin and Analyst should choose any valid custom range, including one that crosses month boundaries. The monthly job, if approved, still groups by calendar month.

Recommended contract:

- UI labels start and end dates clearly. Use a documented display timezone; UTC is the least ambiguous default because backend timestamps are instants. Make the selected day boundaries and timezone visible.
- Treat selected calendar dates as inclusive in the UI and translate to a UTC half-open interval [start, end + one day). The repository already uses >= start and < end, avoiding subsecond and boundary duplication. For timestamp precision, expose explicit date-time values instead of pretending they are inclusive dates.
- Use the existing browser → Next.js Route Handler → FastAPI boundary. Validate dates and filters with Zod in the BFF, and validate authorization/range again server-side. The browser must never call FastAPI directly.
- Apply current visible filters only if download scope is clearly stated. Show a summary before a large export, including dates, active filters, timezone, and row count if a cheap count query is feasible.
- Stream a bounded result using deterministic order. Set an explicit measured maximum rows/bytes; if a request exceeds it, return an actionable response and ask the user to narrow the range. Do not silently truncate or buffer an unbounded export in frontend memory.
- Start with a fixed field allowlist: stable record ID, UTC event timestamp, method, request path, prediction/classification, confidence, recorded action_taken, and observed status when present. Decide explicitly whether source IP is included: it is useful to analysts but sensitive. Exclude raw HTTP request/body, query string, persisted model input text, and secrets from the default export. Do not combine current action state with action-history rows unless their meanings are labeled separately.
- Use text/csv; charset=utf-8, a safe filename, CRLF and RFC 4180 quoting, and UTC ISO 8601 timestamps. Choose whether Excel compatibility needs a UTF-8 BOM and test that choice. CSV quoting alone does not prevent spreadsheet formula execution.
- Neutralize untrusted cell values that begin with formula-triggering characters/whitespace/control characters according to a documented policy and test with spreadsheet-compatible cases. OWASP notes there is no universal sanitization that preserves all underlying cell data for every spreadsheet program. Document that the human-oriented export may prefix dangerous text; do not alter canonical DB values. A future exact machine interchange format could be JSONL, but it should not expand this first feature without need.
- Mark the response non-cacheable with Cache-Control: no-store, do not put exported values in logs/URLs, and use existing security audit events if suitable. Capture actor, range, filters, event time, row count, and outcome without copying cell contents into the audit record.
- Permission matrix: Admin and Analyst may export; Owner inherits full authorization. Viewer remains read-only and has no bulk export by default. Enforce on both BFF and FastAPI; hiding a button is not authorization.

There is no universal row cap prescribed by cited standards. Set it from a local performance benchmark and available memory, not from Microsoft Sentinel’s service-specific limits. If typical ranges fit safely, CSV can remain simple. If realistic large exports require durable background jobs, add that as a later feature rather than prebuilding a reporting platform.

#### 6. RBAC, Viewer, and account lifecycle

Admin/Analyst/Viewer is a legitimate small RBAC model when each role maps to a real audience and least-privilege permissions. CyberTrace also has Owner, so it belongs in the permission matrix.

Viewer has a clear purpose: supervisor, instructor/evaluator, management, or audit observer who needs read-only status. Keep Viewer for that audience. The role should not mutate triage, enforcement, accounts, or bulk-export data by default. If an auditor needs export, make an explicit permission decision rather than silently treating all Viewer accounts as analysts.

Reuse the existing Active/Disabled/Pending setup model and disable/reenable security events. A two-state active/suspended lifecycle is often enough for an account that already has pending setup. Do not add a status enum or lifecycle table without a demonstrated need. Use explicit confirmation with target identity and impact; explain that disabling blocks sign-in and what happens to active sessions; make restore equally clear. Verify audit events include actor, target, action, and time and prevent unsafe self-disable/last-owner cases.

For export, add a permission such as TRAFFIC_EXPORT to Admin and Analyst and inherit it for Owner through the existing role permission model. Confirm owner full-permission behavior is tested. Do not infer permission from UI visibility.

#### 7. Recent-TOTP/RBAC investigation

The current gate has a plausible complete source path: the account role route invokes requireRecentTotp, verified completion tokens are converted to Auth.js claims, and the session callback copies auth_level, auth_method, and auth_time. That supports investigating session freshness; it does not establish the reported failure cause.

The next investigation should:

1. Reproduce a real role change using a test account and capture a request/correlation ID, route, status, and sanitized response code.
2. Trace step-up start, TOTP verification, completion-token consumption, Auth.js sign-in/JWT/session refresh, route guard, and admin_change_account_role Supabase RPC in sequence.
3. At each boundary, record only claim presence/type/age, role/permission outcome, challenge status, and RPC result. Never log TOTP values, completion tokens, cookies, JWTs, passwords, or DB secrets.
4. Compare deployed RPC/function definition and migration version with the repository. The database role/RPC can be stale even if the frontend carries a fresh MFA claim.
5. Test success inside the freshness interval; missing/stale/wrong-method claims; expired or replayed challenge; insufficient role; self/last-owner guard; trusted-origin behavior; and DB RPC error mapping.

Issue classes to distinguish include: step-up success without session cookie/JWT rotation; a stale server/client session; request reaching another tab/device; auth_time unit/time interpretation; role authorization failing independently of MFA; and hosted RPC/migration drift. These are hypotheses only. Keep the recent-TOTP requirement.

#### 8. Forgot Password investigation

OWASP recommends predictable generic responses, consistent timing, single-use random tokens, expiry, and safe URL construction. CyberTrace architecture documentation intentionally specifies 200 queued for eligible users and 404 for ineligible/nonexistent accounts. That differs from generic anti-enumeration guidance and should remain until a product/security decision changes it; do not silently change the contract.

Current code evidence says reset tokens expire after 30 minutes and a later request revokes earlier pending reset tokens. Users who request multiple links can invalidate the email they open later. The UI should explain that only the newest link works, or the product should deliberately change replacement behavior after evaluating risk and delivery reliability.

Investigate, without reading secret values:

- Request timestamps and normalized result codes; throttling across account/IP; repeat-request UX and cooldown.
- Outbox row state, lease/retry attempts, provider outcome, delivery latency, bounce/suppression, and whether the worker is active.
- AUTH_APP_ORIGIN presence/URL shape at runtime through sanitized validation only, redirect allowlisting, HTTPS/public domain, reverse-proxy headers, and generated path.
- Token creation/replacement transaction, 30-minute expiry clock, single-use consumption, URL encoding, and reuse of old/new links in a controlled test.
- Frontend and API validation/error mapping, rate-limit status, expired-link guidance, and safe next step to request a new email.
- Mail provider domain/DNS/template configuration without exposing credentials; compare provider request IDs/timestamps with outbox records.

The UI should identify the next action, preserve the entered email after validation errors, show clear sending/success/error states, and avoid rendering raw provider or SQL errors. Add a password confirmation input only if project requirements favor it; server-side validation remains authoritative.

#### 9. Authentication UI and accessibility

Modern auth screens can be distinctive and task-focused: a strong CyberTrace brand panel or restrained illustration, clear form hierarchy, and consistent controls; keep the input task central on mobile. Do not hide recovery behind decoration.

Use labeled inputs, password-manager/autofill semantics, paste-friendly password and one-time-code inputs, visible password-visibility controls with accessible names, field-associated errors, focus-on-error behavior, and programmatic success announcements. During submission, provide status feedback and prevent duplicate submission without clearing entered values. For MFA, set an appropriate one-time-code autocomplete token where supported. Support keyboard-only use, visible focus, touch-sized targets, screen magnification/reflow, and reduced motion. Test login, Forgot Password, Reset Password, MFA, and step-up as complete paths.

### Options considered

| Option | Decision | Reason |
|---|---|---|
| Delete or move every record older than seven days to monthly CSV | Reject for now | Seven days lacks evidence; CSV-only retention weakens query, integrity, restore, and record-link behavior; physical deletion conflicts with the audit-style data boundary and needs explicit approval. |
| Store older rows in a second DB archive table immediately | Defer | Requires migration, child relationship strategy, dual reads, restore semantics, and updated reports; no measured scale pressure. |
| Partition traffic_logs by month now | Reject for current scale | Adds schema/maintenance complexity and partition-key implications for existing ID references. |
| Keep one table and show a short recent window, with custom history/export dates | Recommend now | Separates UI defaults from database lifecycle and reuses existing indexed query paths. |
| Generate monthly CSV snapshots automatically | Defer behind evidence/approval | Suitable only if monthly downloadable artifacts or external retention are confirmed. Must be separate and idempotent in durable storage, with source rows retained until a tested retention rule exists. |
| Permit any authenticated role to export | Reject | Bulk data export is a separate egress privilege. Admin/Analyst are justified; Viewer remains read-only by default. |
| Use a new full design system or generic dashboard template | Reject | CyberTrace already has a custom visual system and useful components. Targeted refinement has lower risk and preserves identity. |
| Build a custom tour engine from scratch | Reject as first choice | Focus handling, collision detection, responsive target placement, and missing targets are easy to get wrong; evaluate a small library candidate and gate the dependency. |
| Remove Viewer because it has no write permission | Reject | Read-only supervisors, instructors, evaluators, and auditors are a valid audience with an explicit permission boundary. |

### Recommended CyberTrace design

#### Near-term design

- Keep one canonical relational traffic_logs table and existing evidence links.
- Keep dashboard choices at 1h/6h/24h/7d until use data justifies change; retain accurate “recorded action” labels.
- Extend Traffic History with an explicit custom date range and active-filter summary. The initial view may still default to 7d.
- Add manual custom-date CSV export for Admin/Analyst/Owner only, with safe field allowlist and range/size limits. A month choice may be a convenience preset but must resolve to the same custom-range contract.
- Make export and archive different actions: “Export selected dates” is immediate and user-driven; “Monthly archive” is an automated calendar-month operation that remains separately scheduled and implemented only if evidence justifies it.
- Do not start automatic deletion or row movement in this improvement pass. Establish volume, backup, and retention evidence before choosing a lifecycle.
- Diagnose MFA and password-delivery defects first. Keep current security gates while gathering trace evidence.
- Refine current Dashboard, Traffic History, account and auth screens in the existing design system; keep Help & Guide and add a brief optional tour with replay.

#### Retention review trigger

Revisit storage architecture only when a concrete trigger is reached:

- observed database storage/growth materially affects the current Supabase plan or backup window;
- representative EXPLAIN ANALYZE and user-facing latency exceed an agreed target;
- the adviser/data owner sets a specific retention or deletion requirement;
- operators need monthly offline artifacts for recovery or academic evaluation;
- backup/restore cannot meet the required recovery window.

Then compare same-table indexes, query tuning, archive table, or durable file/object archive against measured volume. Do not select partitioning or a storage service before that comparison.

### Research sources

These sources informed principles and patterns. Product examples describe those products, not requirements for CyberTrace.

#### Standards and accessibility

- [W3C Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/) — keyboard, focus, contrast, reflow, target size, accessible authentication.
- [WAI-ARIA Authoring Practices: Modal Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) — focus containment, Escape, restoration, labeling.
- [WAI: Understanding Non-text Content](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html) and [Understanding Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) — alternatives and contrast for chart information.
- [MDN: prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion) — user-controlled motion preference.
- [IETF RFC 4180: Common Format and MIME Type for CSV Files](https://datatracker.ietf.org/doc/rfc4180/) — quoting and text/csv.
- [OWASP CSV Injection](https://community.owasp.org/attacks/CSV_Injection) — spreadsheet formula risks and mitigation caveats.

#### Security and identity

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) — least privilege and server-side checks on each request.
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) — reauthentication for sensitive actions.
- [OWASP Multifactor Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html) — MFA strength and reauthentication context.
- [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) — tokens, responses, expiry, and URL practices.
- [GOV.UK Design System: Error Message](https://design-system.service.gov.uk/components/error-message/) and [Password Input](https://design-system.service.gov.uk/components/password-input/) — associated validation and usable password inputs.

#### Database, storage, and operations

- [NIST SP 800-92, Guide to Computer Security Log Management](https://csrc.nist.gov/pubs/sp/800/92/final) — final guidance; retention should serve requirements and analysis.
- [NIST SP 800-92 Rev. 1 Initial Public Draft](https://csrc.nist.gov/pubs/sp/800/92/r1/ipd) — draft discussion of log lifecycle/storage transitions; not a final standard.
- [PostgreSQL: Table Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html) — partition use cases and constraints.
- [PostgreSQL: BRIN Indexes](https://www.postgresql.org/docs/current/brin.html) — benefit depends on correlation of indexed values with physical row order.
- [Docker: Volumes](https://docs.docker.com/engine/storage/volumes/) and [Persisting Container Data](https://docs.docker.com/get-started/docker-concepts/running-containers/persisting-container-data/) — persistent volume versus container filesystem.
- [Supabase: Backups](https://supabase.com/docs/guides/platform/backups) — plan-specific database backup behavior and limits.
- [Supabase Cron](https://supabase.com/docs/guides/cron) — database scheduling option and run monitoring; not verified as enabled for CyberTrace.

#### Product and design-system patterns

- [Grafana: Use dashboards](https://grafana.com/docs/grafana/latest/visualizations/dashboards/use-dashboards/) — dashboard time selection.
- [Elastic Security: Detection response dashboard](https://www.elastic.co/guide/en/security/current/detection-response-dashboard.html) — time scope and moving between summary and underlying alerts.
- [Cloudflare Log Explorer: Search](https://developers.cloudflare.com/log-explorer/log-search/) — time, fields, filters, result scope.
- [Splunk Enterprise Security: Triage notables](https://help.splunk.com/en/splunk-enterprise-security-7/user-guide/7.3/incident-review/triage-notables-on-incident-review-in-splunk-enterprise-security) — analyst filtering and table-oriented triage.
- [Microsoft Sentinel: Query and export](https://learn.microsoft.com/en-us/azure/sentinel/datalake/kql-queries) — custom time scope, columns, CSV export; service-specific limits are not reused here.
- [Vercel: Runtime logs](https://vercel.com/docs/logs/runtime) and [filter redesign](https://vercel.com/changelog/redesigned-search-and-filtering-for-runtime-logs) — scoped search and visible filters.
- [Datadog: Custom time frames](https://docs.datadoghq.com/dashboards/guide/custom_time_frames/) and [dashboard configuration](https://docs.datadoghq.com/dashboards/configure/) — absolute/relative time selection, timezone display, dashboard density.
- [Sentry Discover saved queries](https://docs.sentry.io/api/discover/create-a-new-saved-query/) — saved query time ranges, fields, grouping, filters, and result limits; this is API documentation, not a UI accessibility specification.
- [GitHub Primer](https://primer.style/) — product design system, accessibility, and color/spacing/typography tokens.
- [Linear UI redesign](https://linear.app/now/how-we-redesigned-the-linear-ui) and [Linear Inbox](https://linear.app/docs/inbox) — hierarchy/density design rationale and contextual/keyboard interaction patterns.
- [Carbon: Data table guidelines](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) — table actions and organization.
- [Microsoft Fluent 2: Layout](https://fluent2.microsoft.design/layout), [Typography](https://fluent2.microsoft.design/typography), [Design tokens](https://fluent2.microsoft.design/design-tokens), and [Motion](https://fluent2.microsoft.design/motion) — hierarchy, spacing, consistency, and restrained motion.
- [React Joyride v3: Accessibility](https://react-joyride.com/docs/accessibility), [New in v3](https://react-joyride.com/docs/new-in-v3), and [Recipes](https://react-joyride.com/docs/recipes) — candidate tour behavior and positioning.
- [Intercom: Product tour best practices](https://www.intercom.com/help/en/articles/3095688-best-practices-for-using-product-tours), [Product tours explained](https://www.intercom.com/help/en/articles/2900885-product-tours-explained), and [Automatically show a tour](https://www.intercom.com/help/en/articles/2900893-automatically-show-your-product-tour-to-the-right-customers) — short, targeted, restartable tours.

#### Published research

- [Human-AI Teaming and Alert Fatigue (ACM Transactions on Internet Technology, 2024)](https://doi.org/10.1145/3670009) — alert workload and fatigue; supports reducing ambiguity, not an assumption that CyberTrace has SOC-scale volume.
- [Alert Fatigue in Security Operations Centers: A Systematic Survey (ACM Computing Surveys, 2025)](https://doi.org/10.1145/3723158) — analyst workload and alert-management challenges; enterprise evidence should not be scaled numerically to this project.
- [SoK: A Comprehensive Analysis of SOC Alert Triage (USENIX Security 2024)](https://www.usenix.org/conference/usenixsecurity24/presentation/yang-limin) — one large SOC study; its volume and 53-day investigation observations show why some organizations need long history, not that CyberTrace needs the same infrastructure.
- [Structured Threat Analysis of Security Analysts (USENIX SOUPS 2023 proceedings)](https://www.usenix.org/system/files/soups2023_full_proceedings.pdf) — supports displaying relevance, context, and related evidence in a workflow.
- [Dashboard design study (arXiv 2022)](https://arxiv.org/abs/2205.00757) — exploratory design research; lower-weight evidence for dashboard iteration.

#### Community/practitioner evidence — low confidence

- [ReactJS discussion: product tours and onboarding](https://www.reddit.com/r/reactjs/comments/1ujxnfu/how_do_you_usually_handle_product_toursonboarding/) and [maintained alternatives to React Joyride](https://www.reddit.com/r/reactjs/comments/1nzfaap/maintained_alternative_to_react_joyride_for_react/) contain opinions about custom versus library-based tours and maintenance. These are anecdotal threads, not representative studies or security guidance.
- [UXDesign discussion of data-table design](https://www.reddit.com/r/UXDesign/comments/vlurxl) illustrates that table behavior needs product-specific design beyond appearance. This is practitioner opinion only.

### Final finding

The proposal should be split into independent concerns: authentication correctness, permission boundaries, historical querying/export, any future retention rule, visual usability, and guided onboarding. The most reliable small-scale improvement is to preserve the current canonical traffic store, let Admin/Analyst choose an arbitrary date range for a manual export, and keep any monthly archive process separately designed and authorized. This protects evidence relationships and makes the user-facing behavior useful before new storage machinery is justified.

## Implementation plan

**Plan date:** 2026-10-04

The plan below translates the research into work for this repository. Manual custom-date exports are independent of any scheduled month-based archive.
### Goal and boundaries

Deliver functional authentication fixes, a clear read-only role, safe manual date-range CSV export, better Traffic History and dashboard usability, and a short guided tour while preserving the current architecture.

Manual export and automated archive are separate capabilities:

- **Manual export:** Admin and Analyst (and Owner through full permissions) choose any valid custom date range. The range can cross calendar months. This is an on-demand user action.
- **Monthly archive:** A separate scheduled process groups eligible older traffic by calendar month for long-term artifacts or monthly archive downloads. It does not constrain manual exports and is not assumed to be in scope until the baseline phase confirms storage, recovery, privacy, and operational needs.

The recommended first implementation keeps the existing traffic table canonical, adds no retention job or deletion, and uses the same server-side range-query boundary for history and export. A retention policy or archive job requires a separate decision if the baseline shows a real need.

#### Non-goals

- No backend/frontend direct browser connection; retain Browser → Next.js Route Handler → FastAPI.
- No weakening or bypassing of recent TOTP.
- No physical traffic-data UPDATE/DELETE behavior without explicit approval.
- No production model registry, ML policy, or unrelated enforcement behavior changes.
- No new database, log warehouse, message queue, object-storage service, custom SMTP infrastructure, or generic redesign.
- No claims of hosted, end-to-end, or production readiness based only on local checks.

### Implementation governance

- **Primary change kind:** Focused feature slices — custom-date Traffic History export and optional guided onboarding.
- **Secondary change kinds:** Direct defect fixes for recent-TOTP/RBAC and password-reset delivery; scoped UX refinements; conditional retention/archival only after evidence.
- **Scope:** Targeted changes within current feature boundaries. Keep route handlers thin, data access async, and backend dependencies flowing through the existing domain/application/infrastructure/presentation layers.
- **Extraction outcome:** Add a backend use case/repository query for export only if existing query logic cannot safely serve it. Keep tour state local to Dashboard/Traffic History rather than creating a global onboarding platform.
- **Contract notes:** Add a new export permission and explicit request/CSV response contract. Preserve current account response and traffic action contracts. Do not relabel recorded actions as verified HTTP outcomes.
- **Database:** No initial schema change, migration, or archive table is recommended. A migration needs explicit approval and a separate design/review.
- **Dependencies:** Reuse current design components. React Joyride is a candidate only; adding any dependency requires explicit approval under repository instructions.
- **Validation:** Use the narrowest backend tests, BFF route and contract tests, and frontend lint/typecheck as affected layers change. Security-sensitive changes need focused authorization, injection, and privacy checks. This file is a plan; none of these checks were run in this research pass.

### Phase 0 — Baseline and decisions

**Purpose:** Establish behavior and measurements before selecting retention or archive architecture.

#### Work

1. Preserve and identify pre-existing working-tree changes. Do not include, reset, or reformat unrelated work.
2. Run a sanitized read-only baseline against the intended development/test database:
   - confirm actual migration head and deployed definitions of account-management and password-reset RPCs;
   - report row count, oldest/newest timestamp, approximate table/index bytes, daily growth over available history, and count of child evidence/enforcement references;
   - collect representative EXPLAIN (ANALYZE, BUFFERS) for 7-day, 30-day, and custom-range queries using safe test data; capture latency without exposing traffic contents;
   - verify backup plan and a documented restore capability with the project owner. Do not treat the runbook as proof of an actual backup.
3. Reproduce the reported recent-TOTP failure and intermittent reset email issue with test accounts. Keep secrets, tokens, TOTP values, cookies, and reset URLs out of logs and evidence.
4. Confirm institutional/adviser requirements for retention, evaluation, and raw request data handling. Distinguish a retention period from the UI's recent window.
5. Confirm the manual export field set, whether source IP belongs in the default export, supported timezone, measured export limits, and whether an export audit event fits an existing event sink.
6. Confirm whether calendar-month archive artifacts are required, what “long-term” means for this academic project, who can retrieve them, and where durable storage/backup would live.
7. Inventory current tour/package versions, app motion behavior, and mobile/screen-reader expectations before choosing a library.

#### Deliverable

A short baseline record in the eventual implementation PR or a separately approved project document: measured volume/query behavior, verified live schema/backup facts, retention decision owner, export scope, and whether Phase 4 archive automation proceeds.

#### Gate

Do not implement scheduled archive, row movement, deletion, partitioning, or schema changes if volume, retention authority, archive destination, or recovery behavior remains unknown.

### Phase 1 — Authentication defects

Implement functional fixes before visual polish.

#### 1A. Recent TOTP for account role changes

**Likely source areas**

- frontend/features/user-management/RecentTotpStepUpForm.tsx
- frontend/app/api/auth/mfa/step-up/route.ts and the corresponding verification route
- frontend/lib/auth/route-guard.ts
- frontend/auth.ts
- frontend/app/api/admin/users/[id]/role/route.ts
- frontend/lib/server/db/account-management.ts
- relevant account/MFA migrations and route/session tests

**Investigation and change**

1. Reproduce the exact user sequence and classify the failure by status/code: challenge start, TOTP verification, completion-token consumption, session refresh, route guard, trusted-origin check, role permission, or database RPC.
2. Verify challenge completion creates a fresh Auth.js token/session and that auth_time is numeric seconds, within the configured freshness interval, and carried into the subsequent PATCH request.
3. Verify the challenge purpose and method are TOTP recent reauthentication, not merely password, backup-code recovery, or a stale prior session.
4. Compare deployed migration/function definitions to repository source before changing client or guard behavior.
5. Make the narrowest fix at the failing boundary. Preserve requireRecentTotp; return a distinct safe response where needed so the UI can say whether reauthentication expired, permission is missing, or the account operation failed.
6. Avoid printing session claims or credentials. Tests should assert claim presence/age and response codes without emitting values.

**Acceptance**

- A role change succeeds after fresh TOTP for an authorized Admin/Owner within the freshness window.
- Missing, expired, stale, wrong-method, wrong-purpose, replayed, and insufficient-role states fail safely and consistently.
- Trusted-origin and database failure behavior remain explicit.
- No recent-TOTP enforcement is removed or broadened.

#### 1B. Forgot Password / Reset Password

**Likely source areas**

- frontend/features/user-management/ForgotPasswordForm.tsx
- frontend/features/user-management/ResetPasswordForm.tsx
- frontend/app/(auth)/forgot-password/page.tsx
- frontend/app/(auth)/reset-password/page.tsx
- frontend/app/api/auth/forgot-password/route.ts
- frontend/app/api/auth/reset-password/route.ts
- frontend/lib/server/db/password-recovery.ts
- password recovery migrations, notification worker/outbox, and current tests

**Investigation and change**

1. Trace request → token creation/replacement → outbox enqueue → worker lease/retry → provider result → trusted reset URL → token consumption. Correlate with safe IDs/timestamps only.
2. Verify AUTH_APP_ORIGIN shape/availability at runtime through sanitized validation, and test public host, forwarded protocol, path, and token URL encoding.
3. Confirm latest-token invalidation and 30-minute expiry are reflected in copy and error recovery. A second request currently replaces earlier pending reset tokens; make this understandable in the UI.
4. Check throttling, duplicate submissions, provider retry/bounce outcomes, and mail-domain configuration. Do not add custom SMTP.
5. Preserve documented 200 queued versus 404 not_found semantics unless a deliberate product/security decision changes enumeration behavior.
6. Improve actionable expired/used-link states and preserve the email field after errors. Keep password validation server-side and avoid returning provider/SQL details.

**Acceptance**

- A valid eligible request queues a message and the observed provider outcome can be traced safely.
- The newest reset link works once within its expiry; older, expired, and used links have a safe next step.
- Origin/configuration errors are observable without revealing values.
- Repeated submissions are bounded and do not cause confusing UI races.
- Existing documented account-response semantics remain unchanged unless separately approved.

### Phase 2 — Role and account lifecycle clarity

**Likely source areas**

- frontend/lib/auth/roles.ts
- existing BFF route guards and FastAPI authorization dependencies
- frontend/features/user-management/UserManagementWorkspace.tsx
- frontend/features/user-management/AccountActionsDialog.tsx
- account-management functions and security-event tests
- matching role/RPC migrations only if baseline identifies real drift

#### Decisions

- Keep Viewer. Define it as read-only access for supervisors, instructors/evaluators, management, and auditors. It can read approved traffic/statistics but cannot triage, change enforcement, administer accounts, or bulk-export by default.
- Keep OWNER in the matrix as full privilege. Do not describe the system as having only three roles.
- Reuse Active, Disabled, and Pending setup. Prefer consistent “Disabled” or “Suspended” copy; do not add a new status column/enum.
- Add a dedicated permission such as TRAFFIC_EXPORT for Admin and Analyst. Owner must inherit it through current full-permission behavior.

#### Work and acceptance

1. Write a role/permission matrix, including export, account lifecycle, triage, and current read permissions.
2. Ensure both Next.js BFF and FastAPI enforce permissions; do not rely on a hidden or disabled button.
3. Verify disabling/re-enabling writes existing actor/target/action/time security events, increments authorization version as intended, and protects the current operator/last Owner where required.
4. Keep confirmation dialogs explicit: target identity, access effect, and reversible restore action.
5. Add no schema if existing permission and event models can represent behavior.

**Acceptance**

- Viewer can view intended read-only data and is denied mutations and bulk export by both server layers.
- Admin and Analyst can export but retain their distinct account-management/action permissions.
- Owner retains full access.
- Disable/restore is auditable and confirmation is clear; Pending setup stays distinct from Disabled.

### Phase 3 — Manual custom-date Traffic History export

This phase implements user-driven export only. It does not execute, trigger, or depend on monthly archiving.

#### Likely code areas

- frontend/app/(dashboard)/traffic-history/page.tsx
- frontend/components/alerts/FilterBar.tsx and Traffic History client/table/detail components
- frontend/features/alerts/contract.ts, schemas, and query utilities
- a new or existing frontend/app/api/... BFF route for CSV export
- frontend/lib/auth/roles.ts and route authorization helpers
- web_app/presentation/api/routes.py or the existing alerts router
- an application-level export use case and async repository query under existing backend layering
- traffic repository/API tests, BFF route contract tests, and frontend component tests

#### Contract and interaction

1. Add explicit Start date and End date inputs to Traffic History. In v1, use UTC as the date-boundary timezone and state this next to the selection. A range such as October 1 through October 5 includes both calendar dates.
2. Translate UI dates into an exclusive backend end bound: start_at <= timestamp < end_at_exclusive, where end_at_exclusive is midnight UTC on the day after the selected end date.
3. Keep export scope predictable: date range is required; current visible filters are applied and summarized before download. The user must see whether confidence/action/search filters narrow exported rows. Do not silently include or ignore hidden filters.
4. Add an Export CSV action for Admin, Analyst, and Owner. Viewer does not see it and remains denied if invoking the route manually.
5. Use Browser → Next.js Route Handler → FastAPI. Parse/validate dates and supported filters with Zod in the BFF, then repeat authorization and range validation in FastAPI. Use matching internal API credentials through server configuration; never expose them to browser code.
6. Add a streaming CSV response with stable timestamp/ID ordering, text/csv; charset=utf-8, safe Content-Disposition, and Cache-Control: no-store. Do not route export through a JSON-only BFF parser or buffer the full file in browser/server memory.
7. Apply a measured row/byte cap. If a selection exceeds the cap, return a clear response with the maximum and invite a narrower selection; never return a partial file without saying so.
8. Decide and document columns before implementation. Initial allowlist proposal: record ID, UTC timestamp, source IP if approved, method, path, prediction/classification, confidence, recorded action, and observed HTTP status if available. Exclude raw body/request, query string, persisted model input, secrets, and internal credentials. Current recorded action and historical action events must be separate fields/exports if both are included.
9. Escape CSV fields per RFC 4180. Add an explicit spreadsheet formula-injection policy for untrusted text; test dangerous prefixes and document any prefixing that changes the human export representation. Keep stored values untouched.
10. Use existing security audit/event infrastructure for actor, date range, filter scope, row count, and outcome if suitable. Do not log exported cell contents. If no suitable event sink exists, document the gap and request approval before a schema migration.
11. A monthly convenience preset may populate the date fields for one calendar month, but it must invoke the same manual export. The scheduled monthly archive, if implemented later, has a separate page/action/status and job; it is not a hidden mode of this request.

#### Acceptance

- Admin and Analyst can export a range of their choosing, including partial months and cross-month intervals; Owner has the same ability.
- UI dates are inclusive and backend interval is half-open, timezone behavior is explicit, and boundary rows are neither omitted nor duplicated.
- Existing supported filters are applied and shown in export scope.
- Export rows/columns are deterministic, bounded, privacy-reviewed, and CSV-injection-safe for tested spreadsheet cases.
- Viewer is denied at both server boundaries even if the UI is bypassed.
- The flow remains browser → BFF → FastAPI and does not expose backend credentials.
- The download is not cacheable and no sensitive values appear in URLs or normal logs.
- Monthly archiving can be absent, paused, or failing without changing manual range export behavior.

### Phase 4 — Retention decision and optional monthly archive

**Default outcome from current research:** retain one canonical traffic table, no archive table, no automatic deletion, no scheduled archive job. Preserve a short recent UI default and allow historical queries/exports. This is the least-complex architecture supported by current evidence.

#### Decision gate

Proceed with automation only if Phase 0 verifies a requirement for separate calendar-month artifacts or a measured database/backup problem. Record:

- approved retention duration and owner;
- archive purpose and whether DB rows remain canonical;
- persistent destination and its access, encryption, backup, and restore behavior;
- rule for late-arriving/updated records and month completion;
- job host/schedule/timezone, locking, retries, alerting, and operator recovery.

#### If monthly artifacts are approved while rows remain canonical

- Define eligibility separately from month grouping. A row may become archive-eligible after a chosen age (for example, a seven-day recent window) while its artifact belongs to its event calendar month.
- Because the current month’s artifact may grow as more rows age out, run an idempotent job that rebuilds each affected month from canonical DB rows and publishes a complete snapshot. Do not append blindly.
- Write to a temporary artifact; validate range, row count, and checksum; atomically publish a new version/manifest; retain the previous good version if generation fails.
- Serialize runs with an appropriate DB or job lock. Record month, cutoff, row count, checksum, job version, and outcome without copying traffic content into logs.
- Use durable storage with explicit backup and restore checks. A container writable layer is not a valid archive destination.
- Prefer an existing scheduler only after verifying single/multiple process behavior and recovery. Supabase Cron requires availability and deployment verification; do not enable an extension without approval.
- Leave canonical DB records unchanged. Monthly archive download should be clearly labeled as a point-in-time archive artifact.

#### If the requirement is to remove rows from the active table

Stop and design a separate migration proposal first. Existing child tables reference traffic IDs with restrictive foreign keys. The design must decide how every dependent action/evidence row remains queryable and restorable, guarantee idempotent copy and verification before source removal, preserve IDs and provenance, support dual-read during rollout, and test a full restore. Physical deletion requires explicit approval under AGENTS.md. It is not part of the initial feature slice.

#### Retention acceptance

- A written retention policy names its purpose, owner, exact age/timezone semantics, fields, archive destination, retrieval permissions, and disposal rule.
- Automated monthly behavior is idempotent, serialized, observable, and safely recoverable after interruption.
- Manual custom-date export remains independent and continues to query its selected range.
- No source row is removed until all references and a tested recovery path are accounted for and explicit approval is given.

### Phase 5 — Targeted visual and interaction refinement

Do not redesign every screen at once. Use feedback and accessibility findings to prioritize.

#### Dashboard

- Preserve current 1h/6h/24h/7d window choices initially.
- Make selected window and refresh/loading state clear; keep totals tied to the complete requested window rather than the small recent-alert preview.
- Retain “Recorded actions over time.” Add an accessible text/table equivalent for chart time buckets, verify keyboard/read-aloud behavior, and test reduced motion.
- Refine hierarchy and density in current cards/panels. Use richer color and emphasis only for meaningful data; keep decorative depth subtle.

#### Traffic History

- Add selected date scope, active filters, result count, sort, reset, and export scope in a visible compact toolbar.
- Keep the table information-dense with responsive overflow or a deliberate mobile row/detail treatment. Preserve stable ordering and accessible row controls.
- Add contextual help for confidence, recorded action, observed status, and export-sensitive fields.
- Keep deeper request/evidence details behind row expansion or a detail view; do not put raw payloads into the default list or CSV.
- Add purposeful empty, no-match, loading, and error states that preserve filter selections and offer a useful next action.

#### Authentication and user management

- First fix functional recovery/step-up defects in Phase 1.
- Then refine Login, Forgot Password, Reset Password, MFA, and step-up using the existing AuthShell/styles: clear form hierarchy, visible focus, associated errors, password/OTP autofill, accessible visibility button, disabled/loading status, success announcement, mobile reflow, and reduced motion.
- Keep account-menu and lifecycle wording consistent; do not add a navigation level unless task testing shows it helps.

#### Acceptance

- Existing CyberTrace tokens and components remain the visual foundation.
- New/refined controls work at laptop, tablet, and narrow mobile widths.
- Keyboard focus is visible and logical; color is not the sole status signal; errors and success are programmatically announced.
- Charts have an equivalent data representation; tooltips are supplementary.
- Reduced-motion preference is honored for every new motion treatment.
- No generic template replacement or unrequested animation/gradient package is introduced.

### Phase 6 — Guided product tour

#### Recommended implementation

1. Add one opt-in first-use Dashboard tour, approximately 4–5 steps. Add a separate short Traffic History tour reachable from Help; do not force both at first login.
2. Provide Skip, Previous, Next, Finish, progress text, and Help → Restart. Skip suppresses automatic reappearance for the current tour version; explicit restart always works.
3. Store tour completion and version in browser storage keyed by user ID and tour ID. Do not add server schema unless cross-device persistence is a confirmed requirement.
4. Add stable data-tour attributes to meaningful controls. Do not bind to CSS classes or translated copy. Handle delayed/missing/hidden targets by waiting briefly or skipping safely.
5. Support viewport-aware placement, scroll targets into view when needed, and switch to a compact guided dialog on narrow/mobile screens if the spotlight would obscure controls.
6. Implement Escape, keyboard navigation, focus entry/return, accessible step labels/live progress, screen-reader semantics, and reduced motion.
7. Evaluate React Joyride v3 for React compatibility, license, maintenance, bundle impact, and UX against the current stack. Repository instructions require explicit approval before adding it. If approval is not given, do not replace it with a large homegrown positioning framework; use existing Help & Guide with a simple accessible step dialog or defer spotlight behavior.

#### Acceptance

- First-use tour appears at most once per user/tour version and is dismissible immediately.
- Skip, Previous, Next, Finish, Restart, Escape, keyboard, focus, screen-reader progress, reduced motion, missing target, viewport collision, and mobile behavior are covered.
- Tour can be replayed from Help without creating a new global onboarding subsystem.
- Experience does not block essential tasks or force both tours.

### Phase 7 — Integration, deployment, and regression

#### Validation sequence

1. Focused backend repository/use-case/API tests for range boundaries, filters, ordering, caps, and streaming behavior.
2. Focused auth/session/route tests for recent-TOTP and password-reset lifecycle.
3. BFF authorization/schema/streaming tests, including Viewer denial, Zod failures, no-store headers, and CSV response forwarding.
4. Frontend component tests for date selection, filter scope, role visibility, account dialogs, auth errors, and tours.
5. Required repo checks for affected layers: backend pytest for changed backend paths; frontend lint and typecheck; BFF contract tests; migration tests only if a separately approved migration exists.
6. If browser verification is requested/available, test actual rendering, keyboard-only operation, screen-reader semantics, touch/mobile layout, Excel/LibreOffice CSV opening, and reduced-motion setting. Report source-level tests separately from browser/runtime proof.
7. Review diff for unrelated work, secrets, generated artifacts, policy/contract drift, and undocumented behavior.

#### Deployment

- No migration or new service is expected for manual export if existing query/API and security-event models are sufficient.
- Deploy frontend and FastAPI changes compatibly. Ensure BFF and backend permission maps are deployed together; deny export until both layers support it.
- Check CSV headers, proxy timeout/stream handling, memory behavior, and maximum size against current hosting limits.
- Do not add environment values or expose secrets. Validate required public origin by safe format/presence checks only.
- If a later archive job is approved, deploy disabled first, generate a non-destructive sample artifact, verify storage ACL/backup/restore, then enable the schedule with alerting.

#### Rollback

- Manual export: remove/disable export controls and deny the BFF route; existing traffic data and history remain unchanged.
- Permission: revoke export permission in both layers; keep read-only history available.
- Auth fixes: revert only the narrow route/session/recovery change and preserve the recent-TOTP guard. Do not roll back unrelated account security schema.
- UI refinement/tour: disable tour auto-start or feature flag the tour; prior page and Help remain usable.
- Monthly archive: pause the scheduler and retain the last verified artifact. Do not delete DB source records as rollback cleanup. Restore only from a tested backup/artifact procedure.
- Any migration: provide forward/backward scripts and a verified rollback rehearsal before deployment; archive-table design requires a separate migration plan.

### Dependency graph

1. Phase 0 establishes actual behavior, scale, privacy, and service state.
2. Phase 1 fixes auth workflows independently and protects sensitive admin actions.
3. Phase 2 finalizes export permission and account lifecycle behavior.
4. Phase 3 implements manual custom-date export; it needs Phase 2 authorization but does not depend on a monthly archive.
5. Phase 4 is a decision gate; current recommendation is to defer automatic archive and retention movement.
6. Phase 5 refines existing screens after core behavior is reliable.
7. Phase 6 adds the optional tour after target controls and labels stabilize.
8. Phase 7 verifies combined contracts and deployable behavior.

### Overall completion criteria

- Authentication defects have a demonstrated root cause and narrow tested fixes; TOTP security remains intact.
- Password-reset request, newest-link behavior, delivery diagnostics, expiry, and errors are predictable and documented.
- Viewer is justified and demonstrably read-only; Owner is represented in the matrix.
- Admin/Analyst/Owner can manually export any allowed custom date range, and CSV scope, fields, safety, size, timezone, and audit behavior are explicit.
- Manual export works independently of any monthly archival schedule.
- Retention period and archive automation are based on measured data and an approved data-handling requirement; otherwise the single indexed table remains canonical with no automatic deletion/move.
- Current CyberTrace visual identity remains; key routes work accessibly and responsively.
- Guided tours are short, optional, replayable, and usable with keyboard/screen-reader/reduced-motion/mobile paths.
- Validation evidence is limited to what was actually run and observed; no local proof is presented as hosted readiness.
