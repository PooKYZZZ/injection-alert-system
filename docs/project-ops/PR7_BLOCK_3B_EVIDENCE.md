# PR7 Block 3B Evidence

Status: **Implemented locally; live external proof NOT_RUN**

## Implemented and verified

- The portal writes only `evidence_id`, stage, method, fixed path, and timestamp
  to an optional append-only JSONL file.
- `request_received` is written before the existing PR6 check.
- `protected_work_started` is written only inside the existing ALLOW-owned
  protected-work callback.
- Sentinel configuration is inert unless both a path and a testing/development
  application environment are present. Invalid IDs and write failures do not
  affect enforcement.
- `docker-compose.pr7-block3b.yml` joins the pinned Cloudflare connector,
  exact `172.30.20.2/32` real-IP peer, PR7 WAF runtime, portal, bridge,
  backend, and disposable PostgreSQL on the existing segmented networks.
- The merged Compose model validates and publishes neither WAF nor portal.

## Verification

- Portal: `npm run test:unit` — 35 passed.
- Portal: `npm run typecheck` — passed.
- Portal: `npm run lint` — passed with the existing Next.js deprecation notice.
- Portal: `npm run build` — passed.
- CyberTrace focused suites: 143 passed, 1 guarded Block 3A E2E skipped.
- 3B and 3C merged Compose: `docker compose ... config --quiet` — passed.

## External-only evidence

The following is **NOT_RUN** because this checkout has no authorized live
Cloudflare account session, proof-hostname configuration evidence, or two
genuinely distinct external client networks:

- Pseudo IPv4 and Worker-route prerequisite inspection.
- Two-source source-equivalence correlation.
- Live forged-header matrix through Cloudflare.
- External direct-origin probes.
- Live Normal/LOW/MEDIUM/HIGH/CRITICAL matrix.

No external, hosted, production, or two-source claim is made.
