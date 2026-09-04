# CyberTrace Dashboard and Alerts Audit

## Decision checkpoint

**Date:** 2026-08-25  
**Scope:** Dashboard, Alerts, shared frontend data behavior, BFF/API boundaries, backend query semantics, ML/WAF evidence presentation, and related local proof paths  
**Status:** Report and planning only  
**Implementation in this checkpoint:** None

This document records the findings, evidence, design options, recommendations,
risks, dependencies, and validation plans identified during the Dashboard and
Alerts review.

No production code, tests, configuration, schemas, dependencies, database
contents, or implementation commits are changed by this checkpoint. The only
intended file change is this Markdown report.

The earlier audit remediation work was developed in an isolated worktree and
was not merged into master. Therefore this report distinguishes:

- behavior already corrected in the current source/history;
- corrections verified in the isolated audit worktree but not merged here;
- remaining findings in the current checkout;
- recommendations that still require a decision or approval.

The current checkout already contained unrelated user changes before this
report was created. Those changes are outside this audit document and must be
preserved.

## Executive summary

CyberTrace has a credible thesis-level foundation for these pages:

- Dashboard aggregate statistics are now designed to come from the complete
  selected window rather than from the first page of Alerts results.
- Backend range queries use UTC-normalized rolling windows and upper/lower
  bounds.
- Charts have an explicit initial size and an honest empty-window state.
- The BFF boundary, authentication checks, asynchronous backend access, and
  Zod validation are already established patterns.
- The local ModSecurity/OWASP CRS proof path has separate evidence showing the
  WAF rule layer, bridge, backend ingestion, ML classification, and dashboard
  evidence as different stages.

The main remaining work is not a broad redesign. It is a small set of changes
that would make the system easier to prove and defend:

1. Add fixed-reference-time tests proving exact rolling-window boundaries and
   Dashboard/Alerts parity.
2. Make confidence terminology unambiguously different from severity and avoid
   presenting an average model score as a calibrated system-quality measure.
3. Change alert opening to an explicit review action, unless the project
   deliberately defines opening as the start of review.
4. Add small mobile and accessibility improvements without replacing the dense
   investigative table.
5. Preserve and better explain the WAF/CRS-to-ML evidence chain instead of
   collapsing it into one unexplained score.

The recommended thesis direction is deliberately conservative: use explicit
evidence fields and simple, testable semantics. Do not add an invented numeric
“system confidence” or a business-severity model without independent evidence
and a defensible definition.

## 1. Audit scope and evidence

### 1.1 Reviewed areas

- Dashboard timeframe control and statistics.
- Dashboard attack distribution, confidence bands, enforcement map, activity
  timeline, recent-alert preview, cards, labels, and empty states.
- Alerts listing, filtering, search, sorting, pagination, detail navigation,
  triage behavior, loading/error states, responsive behavior, and URL state.
- TanStack Query keys, cache freshness, request cancellation, and rapid filter
  changes.
- Next.js BFF routes and FastAPI/backend query paths.
- Database timestamp and aggregation behavior.
- Frontend and backend response contracts, including Zod and Pydantic models.
- Model confidence, confidence tiers, CRS anomaly scores, action values, and
  triage states.
- ModSecurity/OWASP CRS local proof evidence and dashboard evidence.
- Authentication boundaries, data exposure, logs, and privacy-sensitive
  evidence handling.

### 1.2 Runtime evidence

The browser audit used an authenticated local session. No authentication
bypass was attempted.

The local runtime used an existing local demo database containing 40 records:

| Category | Count |
| --- | ---: |
| SQL Injection | 10 |
| Code Injection | 10 |
| Other Attacks | 10 |
| Normal | 10 |
| Non-Normal | 30 |
| BLOCKED | 30 |
| ALLOWED | 10 |
| THROTTLED | 0 |

No new attack traffic was generated during this decision checkpoint. The
backend runtime was local-only. Its development model fallback was observed,
which affects new predictions but not the already persisted demo records used
for the Dashboard/Alerts comparison.

### 1.3 Browser results

When the records were still less than one hour old, the Dashboard showed 40
records for the one-hour window and the larger windows also showed 40.

Later, after the records aged beyond one hour, the observed aggregate results
were:

| Window | Non-Normal | BLOCKED | THROTTLED | ALLOWED | Average confidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 hour | 0 | 0 | 0 | 0 | — |
| 6 hours | 30 | 30 | 0 | 10 | 99.8941% |
| 24 hours | 30 | 30 | 0 | 10 | 99.8941% |
| 7 days | 30 | 30 | 0 | 10 | 99.8941% |

The Alerts page showed 40 records for the 7-day window, 20 records per page,
30 BLOCKED records, 10 ALLOWED records, and 10 SQL Injection search results.

The exact historical example of 100 -> 80 -> 50 -> 100 was not reproduced
against the corrected rolling-window behavior. The live result instead showed
the expected relationship: records disappeared from the one-hour window as
time passed while remaining in the larger windows.

### 1.4 Browser and server observations

- Final browser warning/error collection was empty.
- Dashboard and Alerts requests returned successful responses after the local
  services stabilized.
- A deliberate backend restart caused temporary upstream failures during
  testing. Those failures were expected environment behavior, not evidence of
  a steady-state Dashboard defect.
- Mobile Dashboard cards stacked without obvious clipping.
- Mobile Alerts remained usable through an internal horizontal table scroll,
  but not all columns were visible at once.
- Opening a New alert changed it to In Review for a user with triage permission.
  This changed the local count from 40 New to 39 New and 1 In Review.

## 2. System model and terminology

The operator should be able to follow this chain:

~~~
request
  -> ModSecurity / OWASP CRS evidence
  -> WAF bridge and backend ingest
  -> ML prediction and model confidence
  -> confidence tier and policy action
  -> persisted alert
  -> Dashboard aggregate or Alerts investigation view
  -> analyst triage state
~~~

These stages are related, but they do not mean the same thing.

| Concept | Meaning in CyberTrace | Current evidence/field | Must not be confused with |
| --- | --- | --- | --- |
| WAF evidence | What ModSecurity/CRS detected at the HTTP boundary | CRS score, CRS rule IDs, matched messages, transaction ID, HTTP status | ML confidence or attack severity |
| Prediction | The ML class assigned to the request | SQL Injection, Code Injection, Other Attacks, Normal | Analyst triage state |
| Model confidence | How strongly the classifier favored its predicted class | Raw confidence from 0 to 1 | Probability that the system is correct in all environments |
| Confidence tier | A policy band applied to model confidence | LOW, MEDIUM, HIGH, CRITICAL | Business severity |
| CRS anomaly score | A WAF rule/anomaly score accumulated by CRS | crs_score | Model confidence or CyberTrace severity |
| Action | Recorded policy outcome for the event | BLOCKED, THROTTLED, ALLOWED | Proof that a network request was actually stopped in every deployment |
| Triage status | Analyst workflow state | new, in_review, escalated, resolved, false_positive | Prediction or action |
| Severity | An independent assessment of operational harm | Not currently defined as an independent validated model; severity remains a compatibility alias for confidence tiers | Confidence tier |
| System confidence | A combined assessment of evidence sources | Not currently defined or validated | A made-up numeric probability |

The repository architecture documentation already states that HIGH and CRITICAL
are confidence tiers, not a new business/security severity model. The frontend
still contains legacy names such as SeverityBadge and severity query aliases
for compatibility. That compatibility should not be allowed to define the
visible meaning of the product.

## 3. Timeframe correctness audit

### 3.1 Intended semantics

The four controls should represent rolling windows ending at approximately the
same current instant:

~~~
1h  = [now - 1 hour, now)
6h  = [now - 6 hours, now)
24h = [now - 24 hours, now)
7d  = [now - 7 days, now)
~~~

The lower boundary is inclusive and the upper boundary is exclusive. A record
exactly at the upper boundary belongs to the next interval, not the current
one. This prevents double counting when adjacent intervals are compared.

### 3.2 End-to-end request path

The intended data path is:

~~~
Dashboard timeframe state
  -> TanStack Query stats key containing the window and timezone
  -> Next.js /api/stats route
  -> FastAPI /stats route
  -> one UTC reference time for stats aggregates and buckets
  -> repository [start, end) queries
  -> aggregate response and activity buckets
  -> BFF validation and frontend rendering
~~~

The Alerts page uses the same logical window through the BFF parameter mapping,
but its list request calculates its own current request end time. This is
acceptable for a live page, but it means Dashboard statistics and a separately
requested Alerts list are not guaranteed to be a byte-for-byte snapshot at an
exact boundary.

### 3.3 Confirmed historical causes

Earlier implementation history showed two important defects:

1. Dashboard charts and maps were derived from the first page of Alerts results
   while cards used full aggregate statistics. A 20-row page could not represent
   a complete 100-record window.
2. Alerts time filtering used only a lower timestamp bound in one path, so
   future-dated rows could appear in Alerts even though they were outside the
   current Stats window.

The current source contains the aggregate-statistics design and lower/upper
range predicates. These findings are considered corrected in the base source,
but they still need deterministic regression tests before they can be treated
as permanently protected behavior.

### 3.4 Cache and race assessment

The current query design includes the window in the Stats key and the full
filter serialization in the Alerts key. Fetches receive an abort signal. Stats
and Alerts use short freshness intervals rather than unbounded caching.

No cross-window cache collision was reproduced.

There are two residual freshness considerations:

- Stats and Alerts can be fetched at slightly different instants.
- Stats and Alerts have different freshness windows, so one widget may be a few
  seconds older than another.

These are normal live-dashboard tradeoffs, not evidence of the reported
100/80/50/100 defect. A strict point-in-time dashboard would need an explicit
as_of value shared by all requests, which is more complex and should be added
only if exact snapshot parity is required.

### 3.5 Deterministic tests — recommendation

**Priority:** High  
**Category:** Correctness, reproducibility, thesis defensibility  
**Status:** Recommended; not implemented in this checkpoint

Use a fixed reference time and insert test records at known positions:

- exactly at the start of the one-hour window;
- one second inside the window;
- one second outside the window;
- exactly at the current/end boundary;
- slightly in the future;
- equivalent positions for 6-hour, 24-hour, and 7-day windows where useful.

The tests should assert:

- [start, end) inclusion/exclusion;
- future records are excluded;
- Stats totals and Alerts totals agree for equivalent filters;
- activity bucket totals equal the selected-window total;
- attack-type, confidence-tier, and action maps sum to the expected population;
- IDs in the 1-hour result are a subset of the 6-hour result, which is a subset
  of the 24-hour and 7-day result;
- changing windows cannot reuse an unrelated cached response.

**Options:**

1. Add only live browser tests. This is easy to understand but timing-sensitive
   and unreliable at exact boundaries.
2. Add repository tests with injected reference times. This is deterministic
   and proves the core semantics but does not alone prove the browser wiring.
3. Add repository, BFF, and focused frontend tests. This is the recommended
   balanced approach.
4. Add a full end-to-end time-freezing framework. This is unnecessary for a
   thesis project unless a real cross-process clock problem is demonstrated.

**Recommendation:** Option 3. Keep the fixed-time logic at the repository/BFF
boundary and add a small frontend test for URL/query-key propagation. Do not
freeze the entire browser or introduce a new time abstraction everywhere.

**Dependencies:** Existing test fixtures, existing repository reference-time
parameter, and a safe local test database. No schema or production-data change
is needed.

**Validation:** Targeted pytest, BFF contract tests, frontend query/state tests,
then one browser pass using the existing local records.

## 4. Dashboard findings

### D-01 — Dashboard aggregate source mismatch

**Priority:** High  
**Area:** Dashboard / Backend dependency  
**Category:** Actual correctness defect  
**Status:** Corrected in the current source/history; regression protection remains

**Current behavior:** Dashboard aggregate widgets are intended to use the full
Stats response. The Alerts query remains a recent-row preview.

**Problem:** The earlier implementation calculated some distributions from the
first paginated Alerts page. This made the Dashboard sample-dependent and could
make cards disagree with charts.

**Root cause:** Presentation code was performing full-window aggregation on a
paginated response rather than receiving an authoritative aggregate.

**Evidence:** Source history and the local 40-record browser run. The current
Dashboard showed full-window distributions while the Alerts page showed 20
rows per page.

**Options:**

1. Continue deriving aggregates from Alerts rows. Rejected because pagination
   makes the result mathematically incomplete.
2. Fetch every alert and aggregate in the browser. Rejected because it is
   inefficient and moves policy/data responsibility into the client.
3. Use backend Stats aggregates and keep Alerts for recent display rows.
   Recommended.

**Recommended solution:** Keep the current authoritative Stats design and add
deterministic parity tests.

**Benefits:** Correct totals, smaller browser payloads, clear ownership, and a
defensible explanation during a thesis presentation.

**Risks/dependencies:** Stats response fields must remain contract-validated;
no schema change is required for the current design.

**Validation:** Fixed-reference aggregate tests, BFF schema tests, and browser
comparison against Alerts pagination.

**Decision:** Necessary and already structurally addressed. Add tests next.

### D-02 — Dashboard timeframe is not URL-backed in the current checkout

**Priority:** Medium  
**Area:** Dashboard / Shared frontend  
**Category:** UX, shareability, maintainability  
**Status:** Confirmed current-checkout issue; not implemented here

**Current behavior:** The Dashboard stores its selected window in local React
state and starts with a default window. A browser refresh or shared link does
not reliably preserve the selected timeframe.

**Problem:** An operator cannot reliably share “the 7-day Dashboard view” or
use browser Back/Forward as a record of window changes.

**Root cause:** URL state and local component state are separate sources of
truth.

**Options:**

1. Keep local state only. Simple, but not shareable.
2. Store the window in the URL and derive the query state from it. Recommended.
3. Duplicate the window in Zustand, React state, and the URL. Rejected because
   it increases synchronization risk.

**Research basis:** Next.js documents URL search parameters as a mechanism for
reading state from the URL, while TanStack Query requires variables that affect
a query to be represented in its key. See [Next.js useSearchParams](https://nextjs.org/docs/app/api-reference/functions/use-search-params), [Next.js useRouter](https://nextjs.org/docs/app/api-reference/functions/use-router), and [TanStack Query query keys](https://tanstack.com/query/v4/docs/framework/react/guides/query-keys).

**Recommended solution:** Use a small URL-backed window value with a strict
allow-list and derive both Stats and recent-preview filters from it. Keep
local state only for transient animation/loading presentation.

**Benefits:** Shareable views, reliable navigation, and one source of truth.

**Risks/dependencies:** Existing old timeRange links may need compatibility
normalization. No schema change is needed.

**Validation:** Refresh, direct links for all four windows, Back/Forward, rapid
changes, and query-key assertions.

**Decision:** Recommended next-phase work; important but not an emergency.

### D-03 — Confidence display and card wording can mislead

**Priority:** Medium  
**Area:** Dashboard / Alerts / Shared frontend  
**Category:** Interpretability and terminology correctness  
**Status:** Confirmed; partially addressed in prior isolated remediation but not
fully applied to the current checkout

**Current behavior:** The system has a raw confidence value and a confidence
tier. Some visible formatting rounds values such as 99.9672% to 100%. Legacy
names and color tokens still use “severity.” The Allowed card uses wording
similar to Benign / LOW conf, although Normal predictions remain Allowed at
all valid confidence tiers.

**Problem:** A display such as Normal — 100% (CRITICAL) looks contradictory.
The average confidence card can also be read as a measured system accuracy,
even though it is an average model score. “Model stable” is stronger than the
statistic alone proves.

**Root cause:** Confidence tier, display styling, and legacy severity naming
evolved together even though they represent different concepts.

**Research basis:** Classification thresholds describe how a score becomes a
class decision; they do not automatically establish a calibrated probability
or business severity. See [Google ML thresholding](https://developers.google.com/machine-learning/crash-course/classification/thresholding), [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html), and the calibration research by [Guo et al.](https://proceedings.mlr.press/v70/guo17a/).

**Options:**

1. Keep CRITICAL visually and verbally as-is. Rejected because it remains
   ambiguous.
2. Rename the visible concept to Confidence / Confidence tier, preserve the
   existing thresholds, and show useful precision. Recommended.
3. Add a separate severity model immediately. Rejected until severity has a
   defined input, label policy, validation data, and operator use case.
4. Add a calibrated probability claim. Rejected unless calibration evidence and
   evaluation support it.

**Recommended solution:** Keep confidence and severity separate. Display the
prediction and confidence explicitly, for example:

~~~
Prediction: Normal
Confidence: 99.9672% (Critical confidence tier)
Action: Allowed
~~~

Rename only the visible terminology that is misleading. Preserve the current
confidence thresholds and action policy. Do not retroactively invent severity.

**Benefits:** More honest operator interpretation and a clearer thesis
explanation.

**Risks/dependencies:** UI tests and screenshots need updated expected labels.
Existing API aliases such as severity should remain temporarily for
compatibility rather than forcing a schema migration.

**Validation:** Render Normal, non-Normal, low-confidence, and high-confidence
fixtures; verify precision; confirm that Normal remains Allowed; review the
Dashboard, Alerts table, detail drawer, filters, and legends together.

**Decision:** Necessary terminology correction. Do not create a separate
severity model at this stage.

### D-04 — Average confidence and “system confidence”

**Priority:** Medium  
**Area:** Dashboard / ML evidence presentation  
**Category:** Explainability and scientific defensibility  
**Status:** Design decision required; no current system-confidence field exists

**Current behavior:** The Dashboard displays aggregate average model confidence.
WAF evidence, ML confidence, confidence tier, and action are separate fields.
There is no validated numeric system_confidence field.

**Problem:** Combining WAF score, model confidence, prediction, and action into
one number would suggest a mathematical probability that the project does not
currently define or validate.

**Root cause:** Mature security products often expose risk/severity concepts,
which can make it tempting to add a combined score without enough evidence.

**Options:**

1. Add a numeric System Confidence score. Rejected because its weighting,
   calibration, ground truth, and uncertainty would be unclear.
2. Add a qualitative evidence assessment such as Corroborating evidence,
   ML-only evidence, or Evidence sources differ. Possible later, but only
   after exact rules are defined.
3. Keep the evidence sources separate and show a compact evidence chain.
   Recommended for the current thesis scope.

**Recommended solution:** Do not add a numeric system-confidence field. If an
operator needs a synthesis, add a categorical, explicitly defined Evidence
assessment derived from visible facts, not a probability. For example, “CRS and
ML classifications agree” is explainable only when the CRS rule category and
ML prediction actually support that statement.

**Benefits:** Explainability, traceability, and no unsupported score.

**Risks/dependencies:** A qualitative assessment still needs a documented rule
table and tests. It should not be added merely as a decorative badge.

**Validation:** Unit-test each evidence combination and show the underlying WAF
rules, CRS score, prediction, model confidence, and action beside it.

**Decision:** Defer the new field. Preserve separate evidence fields now.

### D-05 — Dashboard search is visually present but not clearly owned

**Priority:** Medium  
**Area:** Dashboard / Alerts navigation  
**Category:** UX correctness  
**Status:** Confirmed current-checkout issue; not implemented here

**Current behavior:** The shared TopBar exposes a search control. The Dashboard
does not use that search value as part of its aggregate query, so the operator
can type a term without changing Dashboard statistics.

**Problem:** The control appears to promise a Dashboard search but does not
provide one.

**Root cause:** Dashboard aggregate semantics and global search ownership are
not explicitly separated.

**Options:**

1. Implement search across every Dashboard chart and aggregate. Rejected as
   duplicated semantics and unnecessary scope.
2. Make the control explicitly global and route to Alerts with the search term
   and selected window. Recommended.
3. Remove search from the Dashboard. Possible, but less useful than routing an
   existing global control to the investigation page.

**Recommended solution:** Treat TopBar search as an investigation shortcut to
Alerts. Preserve the search term and window in the URL.

**Benefits:** One authoritative filtered list and no misleading aggregate
behavior.

**Risks/dependencies:** Requires clear placeholder/help text such as Search
alerts and URL-state tests.

**Validation:** Search from Dashboard, verify Alerts results, preserve window,
clear search, refresh, and use Back/Forward.

**Decision:** Recommended next-phase work.

### D-06 — Dashboard charts and empty-state behavior

**Priority:** Low  
**Area:** Dashboard  
**Category:** Performance, accessibility, visual correctness  
**Status:** Largely corrected; no broad rewrite recommended

**Current behavior:** Recharts containers have explicit initial dimensions and a
minimum height. Empty windows show No events in this window rather than a
misleading active plot. The timeline exposes a role and text summary, and the
Dashboard includes a visible Blocked/Throttled/Allowed legend.

**Earlier concern:** Chart mount warnings such as an initial negative width or
height were observed during earlier review, and an empty chart could look like
missing data rather than a quiet period.

**Evidence:** Current TimelineChart and AttackTypePanel use positive
initialDimension values and tests cover the empty state.

**Recommendation:** Keep the existing local solution. Do not replace Recharts,
build a generic chart framework, or add memoization without a measured issue.

**Remaining improvement:** The pie chart has an accessible label but its full
values are easier to understand through the visible bar/list view than by a
screen reader. A short text summary can be added if accessibility testing
shows it is needed.

**Decision:** No emergency change. Optional accessibility follow-up only.

## 5. Alerts findings

### A-01 — Alerts filter, pagination, and URL behavior

**Priority:** Medium  
**Area:** Alerts / Shared frontend  
**Category:** Correctness and usability  
**Status:** Core behavior works; some current-checkout state improvements remain

**Current behavior:** Alerts supports search, confidence/action/triage/window
filters, pagination, detail links, loading, empty, error, retry, and browser
navigation. The local run showed 40 total alerts, 20 per page, 30 BLOCKED,
10 ALLOWED, and 10 SQL Injection search results.

**Problem:** The current Dashboard and Alerts state conventions are not fully
unified. Dashboard timeframe state is local while Alerts filters are URL
driven. This creates different refresh/share behavior between pages.

**Root cause:** Filter state evolved separately in the two feature areas.

**Options:**

1. Keep page-local state. Simpler initially, but harder to share and reproduce.
2. Use URL state for operator-visible filters and query state for server data.
   Recommended.
3. Put every filter in global Zustand state. Rejected because URL state is more
   appropriate for shareable investigation views.

**Research basis:** TanStack Query recommends including query-affecting
variables in query keys and supports cancellation through the query signal.
The implementation should keep URL state as the input and TanStack Query as the
server-state cache, rather than duplicating both in a global store. See
[TanStack Query query keys](https://tanstack.com/query/v4/docs/framework/react/guides/query-keys)
and [query cancellation](https://tanstack.com/query/v4/docs/react/guides/query-cancellation).

**Recommendation:** Unify only the repeated timeframe/filter normalization.
Do not build a generic filter engine.

**Validation:** Filter combinations, refresh, direct URL, Back/Forward, rapid
changes, pagination reset after filtering, and equivalent Dashboard counts.

**Decision:** Necessary for maintainability where logic is duplicated; avoid a
broad state-management rewrite.

### A-02 — Triage is advertised as sortable although the backend contract is not

**Priority:** Medium  
**Area:** Alerts / Backend contract  
**Category:** Actual correctness and accessibility  
**Status:** Confirmed current-checkout defect; not implemented here

**Current behavior:** The table column configuration marks Triage as sortable,
so it renders as a button-like sort header. The frontend sort type and backend
supported sort fields do not consistently provide a Triage sort.

**Problem:** Clicking the header can send an unsupported or misleading
sort_by=triage request. The operator receives no trustworthy sorting semantics.

**Root cause:** The display column definition and API sort contract drifted.

**Options:**

1. Remove the sort affordance from Triage. Recommended for current scope.
2. Add real triage ordering to the backend and document the order. Reasonable
   only if analysts need it and the order is defined.
3. Sort the current page locally. Rejected because it would not sort the full
   result set.

**Recommended solution:** Remove the sort affordance for Triage now. If later
needed, add a real backend sort with explicit status ordering and tests.

**Benefits:** The UI promises only behavior the API supports.

**Risks/dependencies:** Removing a button is low risk. Adding backend sorting
would require contract and repository tests.

**Validation:** Assert that Triage is a plain header, and verify timestamp,
confidence, and action sorting still work.

**Decision:** Necessary small correctness fix; backend triage sorting deferred.

### A-03 — Alert opening automatically changes New to In Review

**Priority:** Medium  
**Area:** Alerts / Triage workflow  
**Category:** UX, audit semantics, workflow correctness  
**Status:** Confirmed behavior; decision required; not implemented here

**Current behavior:** When a user with triage permission opens a New alert, the
page sends a triage update to in_review. Opening the drawer is therefore a
persisted mutation.

**Problem:** Navigation and workflow mutation are coupled. A user may click to
inspect an alert without intending to claim it for review.

**Root cause:** The current row-click handler treats opening as the beginning of
investigation.

**Research basis:** NIST SP 800-61 Rev. 3 describes triage and prioritization as
decisions based on defined risk factors, and incident-management guidance
emphasizes clear handling decisions rather than implicit first-come behavior.
See [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final).
This does not dictate one UI click pattern, but it supports explicit and
explainable analyst decisions.

**Options:**

1. Opening starts review. This is efficient, but the mutation must be visible
   and documented.
2. Opening is read-only; an explicit Start Review action changes the state.
   Recommended for thesis defensibility.
3. Opening starts review only after a confirmation dialog. More explicit but
   adds friction for every alert.

**Recommended solution:** Use Option 2. Open the detail drawer without mutation.
Show Start Review to users with permission, keep viewers read-only, and update
the triage state only after that explicit action.

**Benefits:** Clear audit semantics, fewer surprising count changes, and a
simple explanation during a defense.

**Risks/dependencies:** Adds one visible workflow action. Existing triage API
and statuses can be reused; no schema change should be necessary.

**Validation:** Opening, closing, explicit Start Review, repeated opening,
invalid IDs, direct detail links, Back/Forward, users with and without triage
permission, and triage count updates.

**Decision:** Recommended to change after approval. Do not preserve hidden
automation merely because it currently exists.

### A-04 — Alert timestamps and confidence formatting

**Priority:** High  
**Area:** Alerts / Shared frontend / Backend response contract  
**Category:** Correctness and interpretability  
**Status:** Confirmed; partial backend support; not implemented in this checkpoint

**Current behavior:** The table uses native frontend date parsing and displays
time plus relative age. It does not consistently show a calendar date in a
seven-day view. Confidence is rounded to a whole percentage in the current
table path.

**Problem:** Naive timestamps can be interpreted in the browser timezone, and a
seven-day list can show several rows with the same time-of-day but different
dates. Whole-number confidence formatting hides meaningful differences.

**Root cause:** The timestamp contract is not fully explicit for every response
field, and date/percentage presentation is duplicated in components.

**Research basis:** JavaScript date parsing has implementation/history pitfalls
when strings are not explicit about timezone. See [MDN Date.parse](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/parse).

**Options:**

1. Let each component call new Date() and format independently. Rejected.
2. Serialize all instants as explicit UTC RFC3339 and use one shared parser and
   formatter. Recommended.
3. Convert timestamps to browser-local strings in the BFF. Rejected because
   it makes the BFF requester-dependent and loses canonical instants.

**Recommended solution:** Keep instants canonical in UTC through storage and
transport; localize only at display. Require explicit offset/Z timestamps in
new API responses, preserve a carefully documented legacy fallback only if
required, show date plus time for multi-day views, and display useful
confidence precision.

**Benefits:** Correct cross-timezone interpretation and easier API contract
testing.

**Risks/dependencies:** Existing screenshots and component tests will change.
Historical naive data needs a clearly documented interpretation; do not
silently reinterpret known local timestamps.

**Validation:** UTC, Asia/Manila, and another timezone; malformed timestamps;
exact boundary records; seven-day display; detail drawer; BFF/Pydantic/Zod
contract tests.

**Decision:** Necessary correctness work.

### A-05 — Alerts table responsive and accessibility improvements

**Priority:** Medium  
**Area:** Alerts  
**Category:** Accessibility and responsive usability  
**Status:** Usable but improvable; not implemented here

**Current behavior:** The table uses semantic table markup, accessible control
labels, checkboxes, sortable controls, and an internal horizontal scroll at
narrow widths. The table remains dense on a 390px viewport.

**Problem:** Users may not realize that more columns exist off-screen. Some
important chart/table information is easier to understand visually than via
assistive technology.

**Research basis:** W3C recommends appropriate table semantics, including
headings and relationships, while the WAI-ARIA APG explains that controls need
clear accessible names. See [W3C Tables Tutorial](https://www.w3.org/WAI/tutorials/tables/)
and [WAI-ARIA accessible names](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/).

**Options:**

1. Keep horizontal scrolling but add a visible instruction or fade/scroll
   affordance. Recommended first step.
2. Hide lower-priority columns on mobile. More compact, but hides evidence.
3. Replace rows with cards on mobile. More responsive-looking, but duplicates
   layout and can hide exact investigative fields.
4. Add a compact mobile summary plus an expandable evidence view. Useful later,
   but more code than currently justified.

**Recommended solution:** Keep the table and add a concise scroll hint. Ensure
each row remains keyboard-accessible and that important values have textual
summaries. Do not replace the investigative table with cards without a
demonstrated need.

**Benefits:** Better discoverability without losing exact evidence fields.

**Risks/dependencies:** Small layout change; no API dependency.

**Validation:** Keyboard-only navigation, screen-reader name inspection,
390px/768px/desktop screenshots, contrast review, and long path/payload cases.

**Decision:** Recommended focused polish, not a compliance rewrite.

### A-06 — Loading, empty, error, malformed-data, and authentication states

**Priority:** Low  
**Area:** Dashboard / Alerts / BFF  
**Category:** UX robustness and security  
**Status:** Mostly healthy; keep coverage focused

**Current behavior:** Loading skeletons, empty states, error messages, retry
buttons, and cached-data update states exist. BFF routes authenticate and
return bounded errors rather than exposing backend stack traces.

**Evidence:** Browser inspection showed successful empty-window behavior and
retry-capable errors. Source contracts use Zod validation for Alerts/Stats
payloads.

**Concerns:** A malformed upstream payload must fail as an error rather than
being silently converted to zeros. During a refresh, cached values should not
be replaced with misleading zero values. Authentication expiry should return
the established login behavior.

**Recommendation:** Add focused contract tests for malformed timestamps,
missing required confidence fields, invalid enums, and partial response errors.
Do not add fake fallback records.

**Benefits:** Honest failure states and easier diagnosis.

**Risks/dependencies:** Requires stable test fixtures; no production schema
change.

**Decision:** Maintain and test; no broad state rewrite.

### A-07 — Performance and request volume

**Priority:** Low  
**Area:** Shared frontend / BFF  
**Category:** Performance assessment  
**Status:** No material defect confirmed

**Current behavior:** Stats and Alerts are cached briefly, query keys are
variable-specific, fetches receive cancellation signals, and Alerts are
paginated at 20 rows. Charts transform a bounded bucket list.

**Potential concern:** Stats and Alerts are separate requests and may refresh at
different times. This is a freshness tradeoff, not a demonstrated performance
failure.

**Recommendation:** Do not add memoization, virtualization, a state library,
or an API aggregator unless profiling demonstrates a real cost. If strict
parity becomes a requirement, investigate an explicit as_of value before
disabling useful caching.

**Decision:** Defer optimization; preserve the current simple design.

## 6. WAF and OWASP CRS evidence audit

### 6.1 Verified local evidence layers

The repository contains separate reports for separate proof claims.

#### Technical CyberTrace WAF path — localhost:8088

The CRS baseline report records:

- normal /healthz traffic returning HTTP 200;
- normal API health traffic returning HTTP 200;
- controlled SQL injection-looking traffic returning HTTP 403;
- controlled XSS-looking traffic returning HTTP 403;
- controlled command/file-access-like traffic returning HTTP 403;
- a weird-but-legitimate query returning HTTP 200;
- observed CRS rules and paranoia-level/1 tags.

The live ingest report records a complete chain for a controlled SQLi request:

~~~
SQLi request
  -> ModSecurity / OWASP CRS HTTP 403
  -> JSON audit transaction
  -> bridge post status 200
  -> FastAPI internal lookup found=true
  -> prediction SQL Injection
  -> confidence 0.998819 / HIGH
  -> action BLOCKED
  -> CRS score 5 and rules 942100, 949110
~~~

#### Realistic demo-target path — localhost:8089

The demo-target report records normal portal traffic returning HTTP 200 and
controlled SQLi/XSS requests returning HTTP 403. The separate audit log,
transaction IDs, CRS rules, and demo-target bridge are kept distinct from the
technical 8088 path.

Dashboard screenshot evidence shows the application displaying WAF/ML alert
fields, including request path, prediction, action, and CRS score. It does not
turn the screenshot into production deployment proof.

### 6.2 What the CRS evidence proves

The evidence supports these claims:

- CRS blocked the tested attack-looking requests in the local test paths.
- Audit logs contained transaction and rule evidence.
- The bridge forwarded selected evidence to FastAPI.
- At least one controlled event was stored, classified, and retrievable by
  transaction ID.
- The Dashboard/Alerts UI can display the resulting application record.

It does not prove:

- that every SQLi/XSS/RCE payload is blocked;
- that CRS is tuned for every real application request;
- that the ML model caused the WAF block;
- that a recorded action always equals live network enforcement;
- production WAF deployment or centralized SIEM retention;
- full false-positive or penetration-test coverage.

The OWASP CRS documentation explains anomaly scoring and reporting. The score
should therefore be labeled as CRS anomaly score, not as CyberTrace severity or
model confidence. See [OWASP CRS documentation](https://coreruleset.org/docs/index.print)
and the CRS explanation of [anomaly scoring and reporting](https://coreruleset.org/20260420/migrating-crs-3-to-4-part-4-scoring/).

### 6.3 Recommended evidence presentation

**Priority:** Medium  
**Area:** Dashboard / Alerts / Backend dependency  
**Category:** Explainability and security evidence  
**Status:** Current evidence is good; presentation can be clarified

The detail view should preserve a visibly separated evidence structure:

~~~
WAF evidence
  HTTP status
  transaction ID
  CRS anomaly score
  CRS rule IDs/messages
  source provenance

ML evidence
  prediction
  model confidence
  confidence tier
  model version when available

System outcome
  action recorded
  triage status
~~~

Do not collapse these fields into one “risk score” without a defined model.
Keep 8088 and 8089 evidence separate in proof reports and screenshots.

**Decision:** Preserve the current layered evidence model. Add only labels or
small evidence-grouping improvements after approval. Do not add a SIEM,
correlation engine, or enterprise case-management system for this task.

## 7. Security, privacy, and data-boundary findings

### S-01 — BFF and authorization boundary

**Priority:** High as a preserved invariant  
**Area:** Shared frontend / BFF / Backend  
**Category:** Security boundary  
**Status:** Strength; must not regress

The intended path remains:

~~~
Browser -> Next.js route handler/BFF -> FastAPI -> repository
~~~

The browser should not call FastAPI directly. BFF routes should continue to
enforce session/permission checks, validate upstream payloads, and avoid
returning raw internal stack traces or secrets.

No token, cookie, database URL, or API key was included in this report.

**Recommendation:** Preserve this boundary in all future Dashboard/Alerts
changes. Do not treat hidden frontend controls as authorization.

**Decision:** No change; regression tests are appropriate.

### S-02 — WAF and request-data privacy

**Priority:** Medium  
**Area:** Alerts / WAF evidence / Documentation  
**Category:** Security and privacy  
**Status:** Policy exists; operational discipline required

Alerts intentionally display request paths, query strings, payload snippets,
source IPs, and CRS evidence to authorized users. That is useful for an analyst,
but raw request bodies and headers can contain credentials or personal data.

The existing ModSecurity policy intentionally excludes sensitive request-header
part B from new raw audit files and documents redaction/retention boundaries.

**Recommendation:** Keep evidence summaries bounded and redacted. Do not paste
raw audit events, cookies, Authorization values, database URLs, or full request
bodies into screenshots or proof Markdown. Keep routine logs separate from
checked-in proof evidence.

**Decision:** Preserve the existing policy. Do not expand data collection for
Dashboard polish.

## 8. What is necessary, optional, or deferred

### Necessary next work

- Fixed-reference timeframe boundary and parity tests.
- Explicit confidence terminology and precision.
- Remove unsupported Triage sorting affordance.
- Complete the timestamp contract and shared presentation handling.
- Decide and implement explicit alert review semantics after approval.

### Recommended but not urgent

- URL-backed Dashboard timeframe state.
- Route Dashboard search to Alerts with preserved filters.
- Horizontal-scroll instruction for the Alerts table.
- Text summaries for chart values where assistive-technology testing shows a
  real gap.
- Small evidence-section labels in the alert detail view.

### Defer

- A numeric System Confidence score.
- A new independent severity model.
- Full WAF correlation or SIEM infrastructure.
- Virtualized alert rendering.
- A generic Dashboard component framework.
- A new as_of snapshot protocol unless strict cross-request parity is later
  required.
- Full production log rotation/retention automation.

## 9. Explicit non-goals

The following should not be changed as part of this remediation:

- confidence thresholds;
- BLOCKED, THROTTLED, and ALLOWED policy mapping;
- the rule that Normal predictions remain Allowed;
- database schema and migrations;
- direct browser-to-FastAPI access;
- model artifacts or automatic model promotion;
- hosted or production database contents;
- the existing local ModSecurity proof paths;
- the Snapshot pill, which is not active on the Dashboard path;
- pagination for the current bounded Alerts workflow;
- the current chart library without measured evidence of a problem;
- the application’s thesis scope by adding enterprise SOC features.

## 10. Proposed implementation plan after approval

No item below is implemented by this report.

### Commit/PR 1 — Deterministic timeframe semantics and parity tests

**Change:** Add fixed-reference repository tests, BFF contract tests, and
focused frontend propagation tests.

**Why:** Make rolling-window semantics reproducible and mathematically
defensible rather than relying only on a live clock.

**Dependencies:** Existing async repository fixtures and safe local test data.

**Expected tests:** Exact start/end boundaries, future records, all four
windows, ID subset relationships, aggregate/bucket totals, and equivalent
Dashboard/Alerts counts.

**Validation:** Targeted pytest, BFF tests, frontend tests, then browser smoke.

**Risk:** Low. No production data or schema change should be needed.

### Commit/PR 2 — Unify URL/filter state and data contracts

**Change:** Make Dashboard timeframe URL-backed, route global Dashboard search
to Alerts, use shared current-URL handling for rapid changes, and complete the
explicit UTC timestamp/confidence formatter contract.

**Why:** Remove duplicated state semantics and ambiguous display behavior.

**Dependencies:** Compatibility normalization for existing timeRange and legacy
severity links.

**Expected tests:** Refresh/direct-link/Back/Forward tests, rapid filter tests,
Zod/Pydantic timestamp tests, malformed-data tests, and confidence rendering
fixtures.

**Validation:** Browser tests at all four windows and with search/filter
combinations; timezone display checks.

**Risk:** Medium because it touches shared URL and response presentation, but
not the policy thresholds or database schema.

### Commit/PR 3 — Clarify confidence and WAF evidence presentation

**Change:** Use visible Confidence / Confidence tier terminology, preserve
useful precision, clarify average-confidence wording, and group WAF evidence,
ML evidence, outcome, and triage fields in the detail presentation.

**Why:** Make the detection chain explainable without inventing severity or a
numeric system-confidence score.

**Dependencies:** Product wording review and existing evidence fields.

**Expected tests:** Normal/high-confidence, non-Normal, WAF-only, ML-only, and
corroborating-evidence fixtures.

**Validation:** Detail drawer, table, Dashboard cards, legends, screenshots,
and thesis explanation review.

**Risk:** Low to medium; avoid renaming persisted fields or breaking legacy API
aliases.

### Commit/PR 4 — Explicit alert review workflow

**Change:** Make opening a New alert read-only and add an explicit Start Review
action for authorized users, if the recommended workflow is approved.

**Why:** Separate navigation from persisted analyst decisions.

**Dependencies:** Confirmation that the thesis workflow prefers explicit review
action over automatic review on open.

**Expected tests:** Permissions, open/close, Start Review, repeated opening,
invalid links, Back/Forward, and triage counts.

**Validation:** Authenticated browser tests as viewer and analyst.

**Risk:** Medium; it changes analyst workflow semantics but reuses existing
triage states and endpoints.

### Commit/PR 5 — Focused mobile/accessibility improvements

**Change:** Add a small table scroll affordance and useful text summaries for
charts/important values.

**Why:** Improve discoverability and assistive-technology access without hiding
investigative fields or rebuilding the UI.

**Dependencies:** No API or schema dependency.

**Expected tests:** Keyboard navigation, accessible names, semantic table checks,
narrow viewport screenshots, and long-content cases.

**Validation:** 390px, tablet, and desktop browser passes.

**Risk:** Low.

## 11. Approval gate

Before implementation, confirm the following decisions:

1. Approve fixed-reference timeframe and parity tests.
2. Approve visible confidence terminology separate from severity.
3. Approve not adding a numeric System Confidence score at this stage.
4. Approve explicit Start Review instead of changing triage state merely by
   opening an alert.
5. Approve the small Alerts mobile/accessibility improvements.
6. Approve preserving the current WAF/CRS evidence chain without adding SIEM or
   enterprise correlation infrastructure.

Until approval is given, this report is the stopping point.

## 12. Research and evidence references

### Framework and frontend state

- [TanStack Query — Query Keys](https://tanstack.com/query/v4/docs/framework/react/guides/query-keys)
- [TanStack Query — Query Cancellation](https://tanstack.com/query/v4/docs/framework/react/guides/query-cancellation)
- [Next.js — useSearchParams](https://nextjs.org/docs/app/api-reference/functions/use-search-params)
- [Next.js — useRouter](https://nextjs.org/docs/app/api-reference/functions/use-router)
- [MDN — Date.parse()](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/parse)

### Accessibility

- [W3C WAI — Tables Tutorial](https://www.w3.org/WAI/tutorials/tables/)
- [W3C WAI-ARIA APG — Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/)

### ML confidence and calibration

- [Google Machine Learning — Classification Thresholding](https://developers.google.com/machine-learning/crash-course/classification/thresholding)
- [scikit-learn — Probability Calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [Guo et al. — On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a/)

### Incident response and WAF evidence

- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final)
- [OWASP CRS Documentation](https://coreruleset.org/docs/index.print)
- [OWASP CRS — Anomaly Scoring and Reporting](https://coreruleset.org/20260420/migrating-crs-3-to-4-part-4-scoring/)

### Repository evidence

- docs/architecture.md
- docs/client-requirements.md
- docs/project-ops/DEMO_TARGET_WAF_PROOF.md
- docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md
- reports/modsecurity-live-proof/crs-baseline.md
- reports/modsecurity-live-proof/e2e-proof.md
- reports/modsecurity-live-proof/demo-target-crs-proof.md
- reports/modsecurity-live-proof/dashboard-evidence.md
- docs/superpowers/plans/2026-08-24-dashboard-refinement.md

## Final status

~~~
PASS: Audit findings and options are documented.
PASS: Deterministic timeframe testing is defined.
PASS: Confidence, severity, CRS score, action, triage, and system-confidence concepts are separated.
PASS: ModSecurity/OWASP CRS evidence and limitations are documented.
PASS: Alert triage options and a recommended workflow are documented.
PASS: Mobile/accessibility options are documented.
PASS: Security and privacy boundaries are documented.
PASS: Proposed implementation commits and validation are documented.
PASS: No production code, tests, configuration, schemas, dependencies, or database contents were changed for this checkpoint.
PENDING: User approval before any implementation work.
~~~
