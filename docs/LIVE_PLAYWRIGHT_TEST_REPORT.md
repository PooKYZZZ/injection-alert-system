# LIVE PLAYWRIGHT TEST REPORT

VERDICT: PASS
BASE_URL: http://localhost:3000
RUN TYPE: Direct app test
BROWSER: chromium
DATE: 2026-06-08T09:53:39.291Z

## SMOKE PAGES
| path | status | mainVisible | crash | result | screenshot |
| --- | --- | --- | --- | --- | --- |
| / | 200 | true | false | PASS | test-results/live-screenshots/01-home.png |
| /services | 200 | true | false | PASS | test-results/live-screenshots/02-services.png |
| /records/search | 200 | true | false | PASS | test-results/live-screenshots/03-records-search.png |
| /records/LND-2026-0001 | 200 | true | false | PASS | test-results/live-screenshots/04-record-detail.png |
| /records/LND-2026-0001/request-copy | 200 | true | false | PASS | test-results/live-screenshots/05-copy-request.png |
| /transactions/status | 200 | true | false | PASS | test-results/live-screenshots/06-transaction-status.png |
| /support | 200 | true | false | PASS | test-results/live-screenshots/07-support.png |
| /appointments | 200 | true | false | PASS | test-results/live-screenshots/08-appointments.png |
| /comments | 200 | true | false | PASS | test-results/live-screenshots/09-comments.png |
| /login | 200 | true | false | PASS | test-results/live-screenshots/10-login.png |
| /success | 200 | true | false | PASS | test-results/live-screenshots/11-success.png |
| /demo-guide | 200 | true | false | PASS | test-results/live-screenshots/12-demo-guide.png |

## CLICKS
| text | expected | actual | result |
| --- | --- | --- | --- |
| Search Records | /records/search | /records/search | PASS |
| Track Status | /transactions/status | /transactions/status | PASS |
| Book Appointment | /appointments | /appointments | PASS |
| Support Desk | /support | /support | PASS |
| Technical Notes | /demo-guide | /demo-guide | PASS |
| Demo Login | /login | /login | PASS |
| Search record indexes | /records/search | /records/search | PASS |
| Request copy | /records/LND-2026-0001 | /records/LND-2026-0001 | PASS |
| Track status code | /transactions/status | /transactions/status | PASS |
| Book public session | /appointments | /appointments | PASS |
| Open system ticket | /support | /support | PASS |

## FORMS
| name | expected | actual | reference | result |
| --- | --- | --- | --- | --- |
| copy request | TXN ref and status lookup | http://localhost:3000/transactions/status?ref=TXN-2026-3223 | TXN-2026-3223 | PASS |
| support | SUP ref if implemented | http://localhost:3000/transactions/status?ref=SUP-2026-5590 | SUP-2026-5590 | PASS |
| appointment | APT ref if implemented | http://localhost:3000/transactions/status?ref=APT-2026-3489 | APT-2026-3489 | PASS |
| comments | comment renders as text | visible |  | PASS |
| login | demo login message, password hidden | message=true, passwordInUrl=false, passwordInBody=false |  | PASS |

## VALIDATION
| name | expected | actual | result | screenshot |
| --- | --- | --- | --- | --- |
| support missing required fields | 400 | 400 | PASS | api-only |
| support invalid email | 400 | 400 | PASS | api-only |
| appointment past date | 400 | 400 | PASS | api-only |
| login missing username | 400 | 400 | PASS | api-only |
| copy request missing purpose | 400 | 400 | PASS | api-only |
| transaction lookup bad ref | not-found message, no crash | not-found shown | PASS | test-results/live-screenshots/validation-transaction-not-found.png |

## A11Y SANITY
| path | heading | labels | controls | unnamedButtons | unnamedLinks | tablesWithoutHeaders | result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| / | true | 2 | 2 | 0 | 0 | 0 | PASS |
| /services | true | 0 | 0 | 0 | 0 | 0 | PASS |
| /records/search | true | 1 | 1 | 0 | 0 | 0 | PASS |
| /support | true | 5 | 5 | 0 | 0 | 0 | PASS |
| /appointments | true | 6 | 6 | 0 | 0 | 0 | PASS |
| /comments | true | 2 | 2 | 0 | 0 | 0 | PASS |
| /login | true | 2 | 2 | 0 | 0 | 0 | PASS |

## RESPONSIVE / ZOOM
| name | path | viewport | zoom | horizontalOverflow | result | screenshot |
| --- | --- | --- | --- | --- | --- | --- |
| home 200 percent | / | 1280x900 | 2 | false | PASS | test-results/live-screenshots/zoom-home-200.png |
| records 200 percent | /records/search | 1280x900 | 2 | false | PASS | test-results/live-screenshots/zoom-records-200.png |
| mobile records | /records/search | 375x812 | 1 | false | PASS | test-results/live-screenshots/mobile-records.png |
| mobile support | /support | 375x812 | 1 | false | PASS | test-results/live-screenshots/mobile-support.png |
| mobile status | /transactions/status | 375x812 | 1 | false | PASS | test-results/live-screenshots/mobile-status.png |

## SCREENSHOTS
- test-results/live-screenshots/01-home.png
- test-results/live-screenshots/02-services.png
- test-results/live-screenshots/03-records-search.png
- test-results/live-screenshots/04-record-detail.png
- test-results/live-screenshots/05-copy-request.png
- test-results/live-screenshots/06-transaction-status.png
- test-results/live-screenshots/07-support.png
- test-results/live-screenshots/08-appointments.png
- test-results/live-screenshots/09-comments.png
- test-results/live-screenshots/10-login.png
- test-results/live-screenshots/11-success.png
- test-results/live-screenshots/12-demo-guide.png
- test-results/live-screenshots/flow-record-search-results.png
- test-results/live-screenshots/flow-record-detail.png
- test-results/live-screenshots/flow-copy-request-form.png
- test-results/live-screenshots/flow-copy-request-success.png
- test-results/live-screenshots/flow-copy-request-status-lookup.png
- test-results/live-screenshots/flow-support-form.png
- test-results/live-screenshots/flow-support-success.png
- test-results/live-screenshots/flow-support-status-lookup.png
- test-results/live-screenshots/flow-appointment-form.png
- test-results/live-screenshots/flow-appointment-success.png
- test-results/live-screenshots/flow-appointment-status-lookup.png
- test-results/live-screenshots/flow-comments-before.png
- test-results/live-screenshots/flow-comments-after.png
- test-results/live-screenshots/flow-login-form.png
- test-results/live-screenshots/flow-login-result.png
- test-results/live-screenshots/validation-support-invalid.png
- test-results/live-screenshots/validation-appointment-invalid.png
- test-results/live-screenshots/validation-transaction-not-found.png
- test-results/live-screenshots/zoom-home-200.png
- test-results/live-screenshots/zoom-records-200.png
- test-results/live-screenshots/mobile-records.png
- test-results/live-screenshots/mobile-support.png
- test-results/live-screenshots/mobile-status.png

## TRACE / REPORT PATHS
HTML REPORT: playwright-report
TRACES: none

## COMMANDS RUN
- npm run typecheck
- npm run lint
- npm run build
- npx prisma db seed
- docker compose build
- docker compose up -d --force-recreate
- $env:BASE_URL="http://localhost:3000"; npx playwright test

## SOURCES CHECKED
- https://www.w3.org/TR/wcag/
- https://designsystem.digital.gov/components/table/
- https://playwright.dev/docs/best-practices

## TOP ISSUES
None.

## FINAL RECOMMENDATION
direct browser demo ready? yes
WAF-proxy demo ready? yes
public tunnel demo ready? yes
CyberTrace ingest testing ready? no