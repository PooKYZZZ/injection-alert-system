# Full-Deployment WAF-ML Milestone 0 Baseline

**Date:** 2026-09-24
**Status:** Baseline captured; no functional policy, schema, ingress, or deployment behavior changed.

This document is the repository-grounded Milestone 0 deliverable for the full-deployment WAF-ML policy plan. It records what was verified in the live repositories and what remains a decision or validation item. The implementation plan remains the design source, while current source code, configuration, tests, and Git state are the technical truth.

## Authority and scope

The working order used for this baseline is:

1. Explicit user-approved requirements.
2. Repository instructions and security boundaries.
3. `docs/FULL_DEPLOYMENT_WAF_ML_POLICY_PLAN.md`.
4. Live source, configuration, and tests.
5. Historical status documents.

The plan is still marked as planning-only. It must not be treated as proof that the planned enforcement behavior, public ingress, database persistence, notifications, or end-to-end deployment already work.

## Repository and branch baseline

| Repository | Current branch and commit | Working-tree state | Milestone branch status |
|---|---|---|---|
| Main WAF-ML application (`E:\AI\PDDDD\injection-alert-system`) | `master` at `2e7dfb3` before this milestone | Pre-existing `.gitignore` modification preserved; it ignores the local copy of the full-deployment plan | `codex/waf-ml-m00-architecture-baseline` created for this document |
| Target portal (`E:\AI\land-records-portal`) | `stable/portal-pre-waf` at `f011b9f` | Pre-existing `.dockerignore` modification preserved (`.pytest_cache`, `.serena`) | Confirmed target base; no milestone branch created yet |

Both working directories intentionally point at the same GitHub repository, `PooKYZZZ/injection-alert-system`. The target portal is coordinated through the `stable/portal-pre-waf` branch; future portal milestone branches and PRs should use that branch as their target base, while main-application PRs use `master` unless a stacked dependency is explicitly documented.

## Live architecture map

The following relationships were confirmed from source and Compose configuration; runtime reachability was not claimed from configuration inspection alone.

- The FastAPI backend is entered through `web_app.presentation.app:create_app`. Its enforcement routes include `/internal/enforcement/check` and `/internal/enforcement/challenge`; WAF ingest is a separate route that triages and records recommendations.
- The existing enforcement domain is scoped to `RECORD_SEARCH`. The current policy maps LOW to monitor/challenge behavior, MEDIUM to throttling, HIGH to application blocking, and CRITICAL to WAF blocking, but this is not yet the approved full-deployment evidence policy.
- The target portal uses the server-side `lib/enforcement-check.ts` wrapper for record search. The wrapper calls the backend with scope `RECORD_SEARCH`, preserves Cloudflare connecting-IP provenance when present, and currently fails open when the check cannot be completed.
- Other portal route handlers and server actions perform route-specific reads or writes without the same enforcement wrapper. `middleware.ts` currently has no active matcher.
- The target Compose path includes a Cloudflare tunnel, `target_waf_ingress`, ModSecurity/OWASP CRS, a target bridge, and the portal. The application Compose path has a separate `app_cloudflare_ingress` path to the Next.js frontend. A shared protected ingress for both public hostnames is not established by the current configuration.
- The browser-to-BFF boundary exists in the main application. The target portal's server-side route boundary must remain server-side; browser code must not call FastAPI directly.
- Existing database primitives include enforcement recommendations, fixed request windows, and challenge grants. A unified persisted policy/evidence record for the planned fields is not yet established.

## Target route inventory

This is the live route inventory used for the next milestone. “Partial” means the route exists and is known, but the full approved enforcement contract is not implemented or evidenced.

| Target route | Method/input observed | Current enforcement boundary | Baseline status |
|---|---|---|---|
| `/records/search` | GET query parameters | `checkRecordSearchEnforcement` before protected work | PASS for the existing search-only wrapper; full policy behavior not tested |
| `/records/[recordNo]` | GET path parameter | No equivalent wrapper observed | PARTIAL |
| `/transactions/status` | GET reference parameter | No equivalent wrapper observed | PARTIAL |
| `/support/submit` | POST form submission | No equivalent wrapper observed | PARTIAL |
| `/appointments/submit` | POST form submission | No equivalent wrapper observed | PARTIAL |
| `/comments/submit` | POST form submission | No equivalent wrapper observed | PARTIAL |
| `/login/submit` | POST form submission | No equivalent wrapper observed | PARTIAL |
| `/records/[recordNo]/request-copy` | GET path/input route | No equivalent wrapper observed; lower ML priority is a plan decision, not proof of exclusion | PARTIAL |
| `/records/[recordNo]/request-copy/submit` | POST form submission | No equivalent wrapper observed | PARTIAL |

The next route-coverage milestone must define exclusions for health checks, static assets, trusted internal traffic, and internal service calls before adding a broad matcher or wrapper.

## Dependency and ownership map

| Concern | Current source of behavior | Known consumer or dependency | Current gap |
|---|---|---|---|
| Classification scope | `web_app/domain/classification_scope.py` and triage use cases | Alerts, recommendations, dashboard, notifications | Consumers need a single positive operational allowlist and fail-closed handling for unknown labels |
| Enforcement decision | `web_app/domain/enforcement.py`, enforcement use cases, repositories | Target portal and internal callers | Scope, evidence inputs, reason, and final transport action are not one shared contract |
| WAF evidence | WAF ingest schemas/use case and ModSecurity bridge fields | Triage and persistence | Reconciliation and provenance need a bounded, redacted evidence contract |
| Source provenance | Portal Cloudflare header handling and backend source fields | Enforcement windows and audit records | Canonical source key and trusted proxy boundary remain unresolved |
| Persistence | Existing enforcement recommendation, window, and challenge-grant models | Backend policy evaluation | Schema/migration changes require an approved contract and explicit migration review |
| Notifications | Existing notification/outbox paths | HIGH/CRITICAL analyst alerts | Failure persistence and end-to-end delivery are not yet validated |
| Public ingress | `docker-compose.*cloudflare.yml`, ModSecurity/CRS, target bridge | Public target and application hostnames | Actual hostname routing and bypass resistance require runtime checks |

## Policy and deployment gap matrix

| Requirement area | Baseline result | Evidence or next action |
|---|---|---|
| Preserve approved confidence thresholds | PASS | Existing confidence-tier tests passed; no threshold change made |
| Preserve `Other Attacks` for analysis | PASS | Existing classification scope keeps it out of the positive operational alert path |
| Positive operational alert allowlist | PARTIAL | Existing scope is a foundation; every alert, enforcement, notification, and query consumer still needs contract-level tests |
| LOW monitor-only behavior | PARTIAL | Current implementation can challenge LOW in enforce mode; the approved “Monitor Only” semantics need an explicit contract and UI representation |
| MEDIUM conditional throttling | PARTIAL | Window and challenge primitives exist; supporting evidence, repetition threshold, duration, and response contract are unresolved |
| HIGH/CRITICAL evidence-based blocking | PARTIAL | Existing action mapping is not proof of the planned evidence gate or same-request behavior |
| Temporary restriction expiry | PARTIAL | Fixed-window primitives exist; route/policy expiry matrix is not yet run |
| Target route coverage | PARTIAL | Search is wrapped; eight other user-controlled route families lack the same verified boundary |
| ModSecurity/CRS separation | PARTIAL | Target Compose path includes ModSecurity/CRS; public blocking, audit correlation, and ML action separation are not runtime-proven |
| Application-hostname ingress consistency | NOT TESTED | Verify public hostnames, tunnel network membership, origin reachability, and direct-origin bypass paths |
| Evidence persistence and correlation | PARTIAL | Existing WAF ingest and recommendation paths exist; unified transaction/correlation/policy evidence representation is not established |
| Dashboard and export representation | NOT TESTED | Validate LOW as “Monitor Only,” policy reason, evidence, final action, and notification status |
| Telegram/email delivery | NOT TESTED | Run approved notification paths with failure persistence; do not expose credentials in evidence |
| Cross-branch compatibility | PARTIAL | The target branch is confirmed; shared contract and rollout-order decisions remain unresolved |

## Research summary and application

The research was limited to sources relevant to this project. Findings were treated as constraints and review guidance, not as authorization to add infrastructure.

| Finding | Application | Decision |
|---|---|---|
| OpenAI harness guidance favors depth-first repository-local context and versioned instructions for long-running coding work. | Keep this baseline and the ignored progress handoff concise and evidence-based; reload them at milestone boundaries. | ADOPTED |
| GitHub pull requests are reviewable change units with explicit base/head branches and review history. | Use one open PR per independently reviewable milestone, use `master` and `stable/portal-pre-waf` as the confirmed bases, and cross-link coordinated PRs. | ADOPTED |
| OWASP API guidance treats unrestricted resource consumption as a bounded rate-limit and resource-isolation concern. | Use route-specific, source-verified, expiring restrictions; do not add an unbounded global throttle. | ADOPTED |
| OWASP logging guidance emphasizes interaction identifiers, source context, consistent event fields, redaction, and failure handling. | Preserve correlation IDs, provenance, policy reason, notification status, and redacted evidence without restoring raw secrets or headers. | ADOPTED |
| ModSecurity's transaction variables and disruptive actions must remain distinguishable from application policy decisions. | Keep CRS blocking, ML evidence, and application enforcement as separate evidence/action fields; do not switch the entire WAF to DetectionOnly to make a test pass. | ADOPTED |
| Broad new distributed infrastructure, automatic model promotion, synchronous same-request ML, and a full reverse-proxy redesign would expand scope. | Defer these until an explicit architecture decision shows they are required. | DEFERRED |

Sources:

- [OpenAI: Harness engineering](https://openai.com/index/harness-engineering/)
- [OpenAI: Running Codex safely](https://openai.com/index/running-codex-safely/)
- [GitHub: About pull requests](https://docs.github.com/en/pull-requests/get-started/about-pull-requests)
- [OWASP API4: Unrestricted Resource Consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP ModSecurity Reference Manual](https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-%28v2.x%29)

## Decisions requiring approval before functional milestones

The following choices change a public contract, security behavior, persistence, or cross-repository compatibility and must not be guessed:

1. Canonical source key and trusted proxy/Cloudflare provenance rules.
2. MEDIUM repetition threshold and bounded time window.
3. Whether MEDIUM supporting evidence uses OR or AND semantics.
4. HIGH/CRITICAL evidence requirements and fallback when evidence is absent.
5. Temporary throttle duration and exact response format, including `Retry-After` behavior.
6. Whether same-request ML enforcement is required or whether the approved design is asynchronous recommendation plus subsequent request enforcement.
7. Whether the public application hostname must traverse the target's protected WAF ingress or retain a separate ingress with equivalent controls.
8. The rollout order for coordinated PRs: main policy contract first, then target-branch route coverage, followed by ingress and end-to-end validation.
9. Any database migration or additive schema change required to persist the approved evidence and policy contract.

## Baseline validation

The following read-only or test commands were run from the repository roots:

```text
Main focused backend tests:
.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_confidence_tiers.py tests/unit/test_enforcement_policy.py tests/unit/test_enforcement_use_cases.py tests/unit/test_enforcement_repository.py tests/unit/test_triage_use_case.py tests/unit/test_waf_ingest_schema.py tests/unit/test_waf_ingest_use_case.py
Result: 128 passed in 1.63s

Target portal unit tests:
npm run test:unit
Result: 39 passed, 0 failed
```

Not run at this milestone: full backend/frontend suites, Docker startup, public hostname checks, database migration, cross-repository HTTP integration, dashboard/export validation, notification delivery, and expiry/bypass matrices. No production or hosted readiness is claimed.

## Milestone boundary

This baseline is documentation-only. It creates no database migration, changes no API contract, changes no enforcement behavior, and changes no Docker or reverse-proxy configuration. The next functional milestone is blocked until the policy, evidence, ingress, and compatibility decisions above are resolved or explicitly staged with a compatibility plan.
