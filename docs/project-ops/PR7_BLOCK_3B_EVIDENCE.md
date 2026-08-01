# PR7 Block 3B Evidence

Status: **Substantially implemented and externally demonstrated for the approved CRITICAL enforcement objective**

## Implemented and verified

- The portal writes only `evidence_id`, stage, method, fixed path, and timestamp
  to an optional append-only JSONL file.
- `request_received` is written before the existing PR6 check.
- `protected_work_started` is written only inside the existing ALLOW-owned
  protected-work callback.
- Sentinel configuration is inert unless both a path and a testing/development
  application environment are present. Invalid IDs and write failures do not
  affect enforcement.
- The 3B overlay requires explicit enforcement credentials, Cloudflare source
  trust, the target-isolation proof input, WAF ingest/snapshot credentials, and
  the portal test sentinel path; it does not publish the portal or WAF origin.
- The executable Block 3 preflight verifies the locked model hashes, final
  portal commit, pinned Python/WAF/container inputs, and rejects degraded or
  mock model-health responses before a proof run can be accepted.
- `docker-compose.pr7-block3b.yml` joins the pinned Cloudflare connector,
  exact `172.30.20.2/32` real-IP peer, PR7 WAF runtime, portal, bridge,
  backend, and disposable PostgreSQL on the existing segmented networks.
- The merged Compose model validates and publishes neither WAF nor portal.
- On 2026-07-31 the signed-in Cloudflare dashboard was inspected in the Codex
  browser. The `cybertrace-target-docker` tunnel still has the expected
  `target-proof.cybertracesystems.com` route, but its status was **Down** after
  disposable-stack cleanup. This is configuration inspection only and is not
  external request evidence.

## Verification

- Portal: `npm run test:unit` — 38 passed.
- Portal: `npm run typecheck` — passed.
- Portal: `npm run lint` — passed with the existing Next.js deprecation notice.
- Portal: `npm run build` — passed.
- CyberTrace focused and full regression suites pass; guarded external and
  disposable E2E remain explicitly skipped unless opted in.
- Full CyberTrace suite with the notification worker disabled for the local
  SQLite test boundary: **1043 passed, 60 skipped**.
- 3B and 3C merged Compose models: `docker compose ... config --quiet` — passed.

## Manual external proof and closure decision

The trusted Cloudflare topology was exercised manually on 2026-07-31. Home
broadband and phone mobile-data egress were observed as distinct external
sources. The controlled proof established that:

- normal external traffic reached the portal;
- static CRS returned HTTP 403;
- forged forwarding headers produced no observed trust bypass;
- a mobile-specific CRITICAL PR7 rule was created;
- the matching mobile source and protected path were blocked at the WAF before
  expiry, with no upstream portal work;
- the same source and path were allowed after absolute expiry;
- static CRS remained active after the dynamic PR7 rule expired; and
- portal sentinel evidence recorded protected work only after the dynamic block
  had expired and access was restored.

The bounded external artifacts remain ignored local evidence under
`artifacts/pr7-block3/external/`; they are not committed repository files. The
automated source-agent workflow is implemented but was not rerun because
Cloudflare Access client credentials were not loaded in the automation shell.

Section 3B is accepted as substantially implemented and externally
demonstrated for the approved CRITICAL enforcement objective. The earlier
controlled manual proof establishes trusted source propagation,
source-specific WAF blocking, absolute expiry, portal restoration, and static
CRS continuity. The automated external source-agent rerun and complete
confidence-tier matrix are deferred and are not blockers for this PR.

The full external Normal/LOW/MEDIUM/HIGH/CRITICAL matrix, direct-origin
dashboard screenshots, Pseudo IPv4 screenshots, Worker-overlap screenshots,
and hosted/production rollout proof remain deferred manual operational
evidence. No claim of a complete external confidence matrix or hosted or
production readiness is made, and hosted/production enforcement remains
disabled.

## Runtime contract

The backend and bridge currently target the pinned Python 3.14 digest recorded
in `docs/project-ops/pr7-block3-artifact-lock.json`. The project metadata,
Dockerfiles, and GitHub Actions Python jobs target one Python 3.14 runtime
contract.
