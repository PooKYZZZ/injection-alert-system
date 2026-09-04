# Search Records attack testing

This is a controlled local-lab test plan for the demo portal's protected
Search Records route. Every attack request in this workflow is:

- GET /records/search
- supplied only through the query parameter
- sent to the internal Docker WAF origin
- correlated with the ModSecurity audit log and backend WAF-ingest record
- bounded by request rate, runtime, and case count

The workflow does not send requests to the dashboard, frontend dashboard
routes, administrative routes, public hostnames, or execution endpoints.
The catalogue uses inert code-style examples and does not attempt file reads,
network calls, command execution, database changes, or destructive actions.

## Baseline and mutation order

The deterministic generator defines ten reviewed seeds for each family:

1. SQL injection
2. Code injection
3. General attacks, stored under the model label Other Attacks

The seed-only phase produces 30 cases. Those are sent first and saved as the
baseline report. The full phase then expands the same seeds into 50 cases per
family, for 150 total cases. Each seed has five forms:

- the original seed;
- alternate spacing;
- casing variation;
- delimiter or wrapper variation;
- an encoding or obfuscation variation.

Exact payload values, wire encodings, mutation names, expected labels, and
hashes are stored in:

- scripts/fixtures/search_records_attack_seeds.json
- scripts/fixtures/search_records_attack_catalog.json

## Isolated Compose test mode

The normal target stack audits only relevant error responses. The
docker-compose.search-records-test.yml overlay uses a separate ignored
audit-log directory, captures every response, and attaches only the backend
and bridge to the isolated target_waf_ingress network. This makes accepted
requests observable without changing the normal public deployment topology.

The backend test runner uses its internal API key from the ignored container
environment for read-only correlation lookups. It never prints that key.
After the test, recreate the services with the normal Compose files so the
temporary test network and audit volume are removed.

## Reproducible commands

Run from the repository root. The portal context and Cloudflare token remain
external operator inputs and must stay in ignored configuration.

~~~powershell
pwsh -NoProfile -File scripts/start_full_cloudflare_target.ps1 -PortalContext 'E:\AI\land-records-portal' -ValidateOnly
New-Item -ItemType Directory -Force logs\modsecurity\search-records-test | Out-Null
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml -f docker-compose.search-records-test.yml --profile demo-target --profile target-cloudflare up -d --build --force-recreate backend demo-target-modsecurity demo-target-bridge
docker exec injection-alert-system-backend-1 python -m scripts.search_route_attack_tester --catalog /app/scripts/fixtures/search_records_attack_seeds.json --audit-log /app/search-test-audit/modsec_audit.jsonl --origin http://demo-target-modsecurity:8080 --backend http://127.0.0.1:8000 --run-id search-records-seeds-20260903-r2 --output-csv /tmp/search-records-seeds-r2.csv --output-json /tmp/search-records-seeds-r2.json --references-output /tmp/search-records-seed-references-r2.json
docker cp injection-alert-system-backend-1:/tmp/search-records-seeds-r2.csv output\attack-tests\search-records-seeds-r2.csv
docker cp injection-alert-system-backend-1:/tmp/search-records-seeds-r2.json output\attack-tests\search-records-seeds-r2.json
docker cp injection-alert-system-backend-1:/tmp/search-records-seed-references-r2.json output\attack-tests\search-records-seed-references-r2.json
docker exec injection-alert-system-backend-1 python -m scripts.search_route_attack_tester --catalog /app/scripts/fixtures/search_records_attack_catalog.json --audit-log /app/search-test-audit/modsec_audit.jsonl --origin http://demo-target-modsecurity:8080 --backend http://127.0.0.1:8000 --run-id search-records-full-20260903 --max-rps 3 --max-runtime-seconds 300 --output-csv /tmp/search-records-full.csv --output-json /tmp/search-records-full.json --references-output /tmp/search-records-known-references.json
docker cp injection-alert-system-backend-1:/tmp/search-records-full.csv output\attack-tests\search-records-full.csv
docker cp injection-alert-system-backend-1:/tmp/search-records-full.json output\attack-tests\search-records-full.json
docker cp injection-alert-system-backend-1:/tmp/search-records-known-references.json output\attack-tests\search-records-known-references.json
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare up -d --no-deps --force-recreate backend demo-target-modsecurity demo-target-bridge
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare ps
~~~

The backend port remains unpublished on the host. The runner therefore calls
the WAF origin from the backend container and uses the backend's internal
loopback only for the read-only transaction lookup. The runner rejects public
or non-Search-Records endpoints.

## Acceptance interpretation

PASS means a seed reached the WAF, was ingested, and matched the expected
label and action. PASS_CANDIDATE means the same was true for a mutation,
which is retained as a regression candidate. FAIL means a seed was observed
but its label or action did not match. REVIEW means a mutation needs analyst
review before it becomes a golden control. Missing audit or bridge evidence is
never treated as a classification pass.

Confidence is recorded exactly as returned by the active model. A LOW or
MEDIUM general attack is saved as a confidence reference only when the system
observed it as an attack; the reference retains whether the exact Other
Attacks label matched. No threshold or action mapping is changed to
manufacture a desired confidence tier.

## Observed run results (2026-09-03)

The seed run was completed before the expansion run. The first attempt exposed
an asynchronous-state issue in the runner: the backend lookup returned a
durable `PROCESSING` row before inference had finished. The runner was updated
to continue polling until the row left `PROCESSING`, the focused regression
test passed, and the seed run was repeated successfully.

Seed baseline (`search-records-seeds-20260903-r2`):

- 30 of 30 requests completed.
- SQL injection: 10/10 exact label matches.
- Code injection: 2/10 exact label matches.
- General attack (`Other Attacks`): 6/10 exact label matches.
- All 30 requests had an audit event, bridge observation, and backend result.

Full expansion (`search-records-full-20260903`):

- 150 of 150 requests completed: 50 SQL, 50 code, and 50 general attacks.
- Every request used `GET /records/search?query=...`; no other route or public
  hostname was used.
- Every request had WAF audit, bridge, and backend persistence evidence.
- SQL injection: 50/50 exact label matches. The WAF returned 403 for 38 and
  200 for 12.
- Code injection: 12/50 exact label matches; 25 were predicted as `Other
  Attacks`, 11 as `SQL Injection`, and 2 as `Normal`. The WAF returned 403 for
  36 and 200 for 14.
- General attack: 24/50 exact label matches; 26 were predicted as `Code
  Injection`. The WAF returned 403 for 46 and 200 for 4.
- 148/150 ground-truth action comparisons matched. The two mismatches were
  code cases predicted as `Normal` at MEDIUM confidence, so the system took
  `ALLOWED` while the expected code-attack action was `THROTTLED`; this is a
  consequence of the label error, not a change to the existing policy. The
  test did not change thresholds or action mapping.
- Confidence tiers were SQL: 47 CRITICAL, 2 HIGH, 1 LOW; code: 24
  CRITICAL, 7 HIGH, 19 MEDIUM; and general: 42 CRITICAL, 6 HIGH, 2 MEDIUM.

Mutation accuracy was 10/10 for every SQL mutation group. Code-injection
accuracy was 2/10 for seeds, 4/10 for spacing, 1/10 for casing, 4/10 for
delimiters, and 1/10 for obfuscation. General-attack accuracy was 6/10 for
seeds, 6/10 for spacing, 6/10 for casing, 1/10 for delimiters, and 5/10 for
obfuscation. These results show that SQL identity generalizes across the
selected mutations, while code and general attack labels remain confused by
the active model.

Reference selection from the full run is saved in the local evidence bundle
`output/attack-tests/search-records-known-references.json`. It contains exact
payloads, wire queries, hashes, expected/predicted labels, confidence, tier,
action, WAF disposition, and transaction IDs. The full per-case report is in
`output/attack-tests/search-records-full.csv` and
`output/attack-tests/search-records-full.json`.

The run produced 50 confirmed SQL references, 12 confirmed code-injection
references, and 24 confirmed general-attack references. It produced no LOW
general-attack reference. It produced two exact MEDIUM general-attack
references:

| Case | Exact payload | Prediction | Confidence | WAF |
| --- | --- | --- | --- | --- |
| `SR-GEN-002` | `<script>console.log('CYBERTRACE_TEST')</script>%00` | `Other Attacks` | `0.725246` / MEDIUM | 403 BLOCKED |
| `SR-GEN-040` | `{{config}}%0a` | `Other Attacks` | `0.601911` / MEDIUM | 200 ACCEPTED |

No LOW general-attack case was observed in this run. That remains pending for
future approved fixture work; the confidence tier was recorded as observed
and was not forced by changing the model or policy.

The normal Compose files were recreated after the run. The isolated overlay
was not left active.

## Evidence and retention

Generated CSV, JSON, JSONL, audit logs, and local screenshots are kept under
`output/attack-tests` or other local runtime paths. The selected attack-test
evidence files in `output/attack-tests` were explicitly included in the
requested push; raw runtime logs and screenshots remain ignored. The reports
keep exact query payloads because the operator explicitly needs reusable
regression cases, but they do not contain credentials or full raw HTTP
headers/bodies. The normal WAF audit-log policy continues to exclude
request-body part B.

The scope and reporting approach follows the local-lab boundaries in
[NIST SP 800-115](https://csrc.nist.gov/pubs/sp/800/115/final) and the
input-validation testing focus in
[OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/latest/).

## Follow-up preservation, code expansion, and normal baseline (2026-09-03)

The original evidence was copied to distinct preserved files before the
follow-up run. The preserved baseline fixture
scripts/fixtures/search_records_followup_baseline.json contains the exact
50 SQL cases and results, all 50 original code cases and results, the 12
original Code Injection positives, and the 30 original seed results. The
separate scripts/fixtures/search_records_known_code_seeds.json fixture
contains the 12 confirmed code-positive rows used as immutable expansion
seeds.

The deterministic follow-up generator created:

- scripts/fixtures/search_records_code_expansion_catalog.json: 100 unique
  code-injection variations, eight mutations for each of the 12 confirmed
  cases plus four additional argument-form mutations;
- scripts/fixtures/search_records_normal_baseline.json: 50 realistic,
  punctuation-safe benign Search Records queries based on the demo portal's
  record vocabulary.

Both catalogues were validated for unique wire queries, canonical
GET /records/search?query=... request URIs, expected labels, hashes, and
their declared case limits.

### Code-expansion outcome

Run ID search-records-code-expansion-20260903 completed all 100 requests.
Every row had an executed request, ModSecurity audit transaction, bridge
observation, backend lookup, and terminal prediction.

- 58/100 were correctly classified as Code Injection (58%);
- 25 were classified as SQL Injection;
- 17 were classified as Other Attacks;
- none were classified as Normal;
- confidence tiers were 62 CRITICAL, 13 HIGH, and 25 MEDIUM.

The original full code baseline remains 12/50 (24%). Combining those original
50 code cases with the 100 new variations gives 70/150 (46.67%). Looking only
at the 12 confirmed seeds plus the 100 new variations gives 70/112 (62.5%);
these are reported separately so the original 38 failures are not hidden.

Mutation results:

| Mutation | Correct | Tested | Accuracy |
| --- | ---: | ---: | ---: |
| encoded spacing | 12 | 12 | 100% |
| separator | 11 | 12 | 91.67% |
| argument form | 3 | 4 | 75% |
| casing | 8 | 12 | 66.67% |
| whitespace | 8 | 12 | 66.67% |
| alternate delimiter | 6 | 12 | 50% |
| wrapper | 5 | 12 | 41.67% |
| quoted argument | 4 | 12 | 33.33% |
| comment | 1 | 12 | 8.33% |

The encoded-spacing and separator transformations were the most reliable.
Comment, quoted-argument, and wrapper transformations caused the most label
confusion. All 42 unsuccessful variants remain in the
misclassified_code_injection_cases group; their exact payloads, source seed,
mutation, prediction, confidence, tier, WAF result, and transaction IDs are
in the JSON report.

### Benign normal-traffic outcome

Run ID search-records-normal-baseline-20260903 completed all 50 requests.
All 50 had complete audit, bridge, backend, and terminal-prediction
correlation.

- 30/50 were correctly classified as Normal (60%);
- 20/50 were false positives, all classified as Other Attacks;
- no benign case was classified as SQL Injection or Code Injection;
- false-positive confidence tiers were 7 CRITICAL, 2 HIGH, and 11 MEDIUM.

The false-positive rows are preserved in the normal_false_positives group.
They include owner-name searches, location and classification searches, and
ordinary service phrases such as Public land records, Search land records,
and Certified copy.

### Result and reproduction files

The grouped report is stored locally at
output/attack-tests/search-records-followup-results-20260903.json, with a
human-readable summary at
output/attack-tests/search-records-followup-results-20260903.md. The raw
follow-up CSV/JSON reports and pre-run copies of the earlier baseline reports
are in the same evidence directory. The JSON grouped report is authoritative
for exact payloads and contains:

1. known_sql_injection_cases;
2. original_known_code_injection_cases;
3. original_seed_cases;
4. expanded_known_code_injection_cases;
5. misclassified_code_injection_cases;
6. known_normal_traffic; and
7. normal_false_positives.

To reproduce the catalogues and reports, run from the repository root:

~~~powershell
.venv/Scripts/python.exe -m scripts.search_records_followup_catalog --mode baseline --output scripts/fixtures/search_records_followup_baseline.json --known-code-output scripts/fixtures/search_records_known_code_seeds.json --base-catalog scripts/fixtures/search_records_attack_catalog.json --seed-catalog scripts/fixtures/search_records_attack_seeds.json --full-report output/attack-tests/search-records-full-before-code-expansion-20260903.csv --seed-report output/attack-tests/search-records-seeds-before-code-expansion-20260903.csv
.venv/Scripts/python.exe -m scripts.search_records_followup_catalog --mode code-expansion --output scripts/fixtures/search_records_code_expansion_catalog.json
.venv/Scripts/python.exe -m scripts.search_records_followup_catalog --mode normal --output scripts/fixtures/search_records_normal_baseline.json
~~~

For this workstation, Compose v5's Bake wrapper could not build while the
external DEMO_PORTAL_CONTEXT resolved to an unavailable drive path. The
standard backend Dockerfile build itself passed. If the same environment
issue occurs, use this bounded local fallback before the overlay command:

~~~powershell
docker build --build-arg INSTALL_TRAINING_REQUIREMENTS=false -t injection-alert-system-backend-followup:local -f Dockerfile .
docker tag injection-alert-system-backend-followup:local injection-alert-system-backend:latest
~~~

Start the isolated overlay without recreating unrelated dependent services:

~~~powershell
New-Item -ItemType Directory -Force logs/modsecurity/search-records-test | Out-Null
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml -f docker-compose.search-records-test.yml --profile demo-target --profile target-cloudflare up -d --no-build --no-deps --force-recreate backend demo-target-modsecurity demo-target-bridge
docker exec injection-alert-system-backend-1 python -m scripts.search_records_followup_tester --catalog /app/scripts/fixtures/search_records_code_expansion_catalog.json --audit-log /app/search-test-audit/modsec_audit.jsonl --origin http://demo-target-modsecurity:8080 --backend http://127.0.0.1:8000 --run-id search-records-code-expansion-20260903 --max-rps 3 --max-runtime-seconds 300 --output-csv /tmp/search-records-code-expansion.csv --output-json /tmp/search-records-code-expansion.json
docker exec injection-alert-system-backend-1 python -m scripts.search_records_followup_tester --catalog /app/scripts/fixtures/search_records_normal_baseline.json --audit-log /app/search-test-audit/modsec_audit.jsonl --origin http://demo-target-modsecurity:8080 --backend http://127.0.0.1:8000 --run-id search-records-normal-baseline-20260903 --max-rps 3 --max-runtime-seconds 300 --output-csv /tmp/search-records-normal-baseline.csv --output-json /tmp/search-records-normal-baseline.json
docker cp injection-alert-system-backend-1:/tmp/search-records-code-expansion.csv output/attack-tests/search-records-code-expansion-20260903.csv
docker cp injection-alert-system-backend-1:/tmp/search-records-code-expansion.json output/attack-tests/search-records-code-expansion-20260903.json
docker cp injection-alert-system-backend-1:/tmp/search-records-normal-baseline.csv output/attack-tests/search-records-normal-baseline-20260903.csv
docker cp injection-alert-system-backend-1:/tmp/search-records-normal-baseline.json output/attack-tests/search-records-normal-baseline-20260903.json
.venv/Scripts/python.exe -m scripts.search_records_followup_report --baseline scripts/fixtures/search_records_followup_baseline.json --code-catalog scripts/fixtures/search_records_code_expansion_catalog.json --normal-catalog scripts/fixtures/search_records_normal_baseline.json --code-report output/attack-tests/search-records-code-expansion-20260903.json --normal-report output/attack-tests/search-records-normal-baseline-20260903.json --output-json output/attack-tests/search-records-followup-results-20260903.json --output-markdown output/attack-tests/search-records-followup-results-20260903.md
~~~

Copy each /tmp report out of the backend container and run
scripts.search_records_followup_report with the baseline and both reports
to regenerate the grouped JSON and Markdown report. The tester accepts only
the internal WAF origin and the backend's internal lookup origin; it does not
accept public hostnames.

After the run, the normal Compose files were applied again. The final
topology has the backend and bridge on the default network only, ModSecurity
on the target application and target ingress networks, the normal relevant
audit-status policy, a healthy backend/frontend/Cloudflared stack, and a
passing Cloudflared readiness check. No model artifact, confidence
threshold, action mapping, database schema, or public route was changed.

## Round-two code-injection expansion (2026-09-03)

The exact 70 classifier-positive code-injection rows were snapshotted before
new generation into
`scripts/fixtures/search_records_code_seeds_round2.json`. The snapshot
contains the original 12 positives plus the 58 positives from the first
100-case expansion; each row retains its full payload, wire query, source
case, predicted label, confidence, tier, action, WAF result, and correlation
identifiers.

The deterministic round-two generator then created
`scripts/fixtures/search_records_code_expansion_round2_catalog.json` with
200 unique variations. All 70 seeds are represented, and the catalogue has
200 unique payloads and wire queries with no duplicate payload/query from the
earlier 150-case corpus. The mutation families cover nested expressions,
block and computed-call wrappers, separator and line-break boundaries,
quote/argument rewrites, encoded delimiter and wrapper chains, comment and
case context, alternate delimiters, and operator chains. The test strings are
inert classification inputs; they were sent only to the local protected
`GET /records/search` route and were not executed as code.

### Round-two outcome

Run ID `search-records-code-expansion-round2-20260903` completed all 200
requests. Every case correlated across the request, ModSecurity audit log,
demo-target bridge, backend lookup, and terminal model prediction.

- 78/200 were classified as `Code Injection` (39.00%);
- 122/200 were misclassified: 107 as `SQL Injection` and 15 as
  `Other Attacks`;
- no case was classified as `Normal`;
- confidence tiers were 108 `CRITICAL`, 23 `HIGH`, 62 `MEDIUM`, and 7
  `LOW`;
- the preserved 70 seeds plus the 78 new positives give 148/270
  classifier-positive rows overall (54.81%).

Mutation families with the strongest observed code-label rate were encoded
wrapper chains (13/14, 92.86%), computed-call wrappers (10/15, 66.67%),
separator expressions (10/15, 66.67%), and line-break boundaries (9/14,
64.29%). The weakest were operator chains (0/14), nested block context
(1/15), alternate delimiters (1/14), and comment boundaries (1/14). These
are observations about this model and fixture set, not a basis for changing
confidence thresholds or action mapping.

The raw complete results are in
`output/attack-tests/search-records-code-expansion-round2-20260903.csv` and
`output/attack-tests/search-records-code-expansion-round2-20260903.json`.
The grouped report is in
`output/attack-tests/search-records-code-expansion-round2-results-20260903.json`
and
`output/attack-tests/search-records-code-expansion-round2-results-20260903.md`.
The grouped report separates the preserved 70 seeds, the 78 newly confirmed
classifier-positive cases, and all 122 misclassified cases. It is the source
for the exact payload, seed ID, mutation, prediction, confidence, WAF result,
and correlation fields.

### Round-two reproduction

From the repository root, regenerate and validate the deterministic fixtures:

~~~powershell
.venv/Scripts/python.exe -m scripts.search_records_code_expansion_round2 --mode snapshot --baseline-report output/attack-tests/search-records-followup-results-20260903.json --output scripts/fixtures/search_records_code_seeds_round2.json
.venv/Scripts/python.exe -m scripts.search_records_code_expansion_round2 --mode catalog --seed-snapshot scripts/fixtures/search_records_code_seeds_round2.json --output scripts/fixtures/search_records_code_expansion_round2_catalog.json
~~~

Build the local backend image if Compose Buildx/Bake is unavailable, apply the
isolated Search Records test overlay, and run the bounded local tester:

~~~powershell
docker build --build-arg INSTALL_TRAINING_REQUIREMENTS=false -t injection-alert-system-backend-round2:local -f Dockerfile .
docker tag injection-alert-system-backend-round2:local injection-alert-system-backend:latest
New-Item -ItemType Directory -Force logs/modsecurity/search-records-test | Out-Null
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml -f docker-compose.search-records-test.yml --profile demo-target --profile target-cloudflare up -d --no-build --no-deps --force-recreate backend demo-target-modsecurity demo-target-bridge
docker exec injection-alert-system-backend-1 python -m scripts.search_records_followup_tester --catalog /app/scripts/fixtures/search_records_code_expansion_round2_catalog.json --audit-log /app/search-test-audit/modsec_audit.jsonl --origin http://demo-target-modsecurity:8080 --backend http://127.0.0.1:8000 --run-id search-records-code-expansion-round2-20260903 --environment local-search-records-waf-followup-round2 --family code_injection --max-rps 3 --max-runtime-seconds 600 --request-timeout-seconds 15 --audit-timeout-seconds 15 --lookup-timeout-seconds 25 --output-csv /tmp/search-records-code-expansion-round2.csv --output-json /tmp/search-records-code-expansion-round2.json
docker cp injection-alert-system-backend-1:/tmp/search-records-code-expansion-round2.csv output/attack-tests/search-records-code-expansion-round2-20260903.csv
docker cp injection-alert-system-backend-1:/tmp/search-records-code-expansion-round2.json output/attack-tests/search-records-code-expansion-round2-20260903.json
.venv/Scripts/python.exe -m scripts.search_records_code_expansion_round2 --mode report --seed-snapshot scripts/fixtures/search_records_code_seeds_round2.json --catalog scripts/fixtures/search_records_code_expansion_round2_catalog.json --result-report output/attack-tests/search-records-code-expansion-round2-20260903.json --output output/attack-tests/search-records-code-expansion-round2-results-20260903.json --output-markdown output/attack-tests/search-records-code-expansion-round2-results-20260903.md
~~~

Restore the ordinary Compose topology after testing:

~~~powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare up -d --no-build --no-deps --force-recreate backend demo-target-modsecurity demo-target-bridge
~~~

The round-two research basis was limited to defensive test design: MITRE
CWE-94 describes untrusted input crossing a code-syntax boundary, OWASP's
Injection Prevention Cheat Sheet recommends context-aware validation and
canonicalization, and the OWASP WSTG describes testing dynamic-code and
file/include boundaries. Those sources informed the mutation families; no
public target or live third-party system was used.

## Artifact index and completion status

Use the following order when reviewing the work so the preserved inputs are
not confused with generated results:

| Order | Purpose | Authoritative local files |
| --- | --- | --- |
| 1 | Original baseline and prior 70 positive seeds | `scripts/fixtures/search_records_followup_baseline.json`; `scripts/fixtures/search_records_code_seeds_round2.json` |
| 2 | Reproducible round-two input catalogue | `scripts/fixtures/search_records_code_expansion_round2_catalog.json` |
| 3 | Raw per-case round-two results | `output/attack-tests/search-records-code-expansion-round2-20260903.csv`; matching `.json` |
| 4 | Sorted/grouped round-two results | `output/attack-tests/search-records-code-expansion-round2-results-20260903.md`; matching `.json` |
| 5 | Historical first expansion and normal-traffic results | `output/attack-tests/search-records-code-expansion-20260903.*`; `output/attack-tests/search-records-normal-baseline-20260903.*` |
| 6 | Reproduction instructions and evidence notes | `docs/project-ops/SEARCH_RECORDS_ATTACK_TESTING.md`; `scripts/search_records_code_expansion_round2.py` |

The organization has been checked as follows:

- [x] 70 seed rows are preserved separately and uniquely identified.
- [x] 200 round-two catalogue rows are unique and cover all 70 seed IDs.
- [x] 200 result rows exist with full payload and wire-query fields.
- [x] Every round-two row has request, audit, bridge, backend, and terminal
  correlation evidence.
- [x] The grouped report separates preserved seeds, newly positive cases, and
  misclassified cases.
- [x] The normal Docker topology was restored after testing; backend,
  frontend, and Cloudflared were healthy at the final check.
- [ ] Detector quality is not complete: 122 of the 200 new variants were
  misclassified and remain pending model/fixture analysis.

The `output/` directory remains ignored by the repository's `.gitignore` for
future generated files. The selected attack-test evidence files listed above
were explicitly force-added for this requested push; raw runtime logs and
inspection dumps were not included. The deterministic generator, fixtures,
tests, and this documentation are intentionally kept as reproducible project
files and were not deleted or collapsed into one report.
