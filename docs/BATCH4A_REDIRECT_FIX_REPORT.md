# BATCH 4A Redirect Fix Report

## Verdict

PASS: Browser-safe POST redirects fixed for scoped routes.

## Files Changed

- `lib/redirect.ts`
- `app/support/submit/route.ts`
- `app/appointments/submit/route.ts`
- `app/comments/submit/route.ts`
- `app/login/submit/route.ts`
- `app/records/[recordNo]/request-copy/submit/route.ts`
- `app/success/page.tsx`
- `docs/BATCH4A_REDIRECT_FIX_REPORT.md`

## Root Cause

PASS: Existing successful POST handlers built absolute redirect URLs from `request.url`.

Evidence from `docs/LIVE_PLAYWRIGHT_TEST_REPORT.md`:

- Browser landed on `chrome-error://chromewebdata/`.
- Direct POST created DB refs.
- Manual route proof opened status pages.

Conclusion: redirect target host could inherit a Docker/internal origin not usable by the browser.

## Redirect Helper Behavior

`lib/redirect.ts` adds `browserRedirect(request, path)`.

PASS:

- Uses `NextResponse.redirect(url, 303)`.
- Uses `x-forwarded-host` first.
- Falls back to `host`.
- Uses `x-forwarded-proto` when safe.
- Forces `http` for `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`.
- Uses `https` fallback for non-local hosts.
- Normalizes `0.0.0.0` to `localhost`.
- Normalizes Docker-only hosts `portal`, `web`, `app` to `localhost:<port>`.
- Accepts same-origin paths for current localhost, mapped Docker ports, and future tunnel/domain hosts.

## Route Redirects Fixed

PASS:

- Support: `/success?type=support&ref=<SUP ref>`
- Appointment: `/success?type=appointment&ref=<APT ref>`
- Comments: `/comments?posted=1`
- Login: `/success?type=login`
- Copy request: `/transactions/status?ref=<TXN ref>&success=copy`

## Success Page Fields Visible

PASS:

- Request type visible.
- Status visible as `Request Received`.
- Generated reference visible when `ref` query is present.
- Next action link visible.
- Login page body includes exactly: `Demo login received. Authentication is disabled in this mock portal.`
- Password is not added to URL or success page body.

## Command Results

PASS: `npm run typecheck`

- Result: exit 0.

PASS: `npm run lint`

- Result: exit 0.
- Warning: `next lint` is deprecated and will be removed in Next.js 16.

PASS: `npm run build`

- Result: exit 0.

PASS: `npx prisma generate`

- Result: exit 0.
- Warning: `package.json#prisma` config is deprecated for Prisma 7.

PASS: `npx prisma db seed`

- Result: exit 0.
- Output: `Database seeded successfully.`
- Warning: `package.json#prisma` config is deprecated for Prisma 7.

PASS: `docker compose build`

- Result: exit 0.
- Warning: npm audit reported `2 moderate severity vulnerabilities`.

PASS: `docker compose up -d --force-recreate`

- Result: exit 0.
- Output: `Container cybertrace-demo-portal Started`.

## Browser Redirect Probe

PASS: Local browser probe against Docker app at `http://localhost:3000`.

- Support: `http://localhost:3000/success?type=support&ref=SUP-2026-2035`
- Appointment: `http://localhost:3000/success?type=appointment&ref=APT-2026-5119`
- Login: `http://localhost:3000/success?type=login`
- Comments: `http://localhost:3000/comments?posted=1`
- Copy request: `http://localhost:3000/transactions/status?ref=TXN-2026-7555&success=copy`

WARN:

- First copy-request probe failed because the probe used `fill()` on a `<select>`.
- Corrected probe used `selectOption()` and passed.

## Remaining Issues

WARN:

- Existing `tests/live-portal.spec.ts` still expects `/comments?success=true`; batch requirement is `/comments?posted=1`.
- `next lint` deprecation remains.
- Prisma `package.json#prisma` deprecation remains.
- Docker install step reports 2 moderate npm audit vulnerabilities.

## Sources Checked

No external research needed. Existing project evidence and framework APIs were sufficient.
