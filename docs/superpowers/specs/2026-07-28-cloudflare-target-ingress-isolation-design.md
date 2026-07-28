# Cloudflare Target Ingress Isolation

## Purpose and boundary

This prerequisite isolates the target-only Cloudflare tunnel from the existing
Windows-hosted application tunnel. It prepares the repository for a later PR7
T0 decision without enabling `cloudflare_tunnel` verification, PR7 enforcement,
or any PR7 schema/migration work.

## Effective topology

The new target overlay creates two dedicated networks:

- `cloudflare-target-egress`: non-internal; attached only to `cloudflared`.
- `cloudflare-target-waf-ingress`: `internal: true`, explicit IPAM on
  `172.30.20.0/28`; attached only to `cloudflared` and
  `demo-target-modsecurity`. `cloudflared` receives `172.30.20.2` and
  ModSecurity trusts only `172.30.20.2/32`.

ModSecurity remains attached to the existing private application network so it
can reach `demo-portal`. The target overlay removes every host-published port
from `demo-target-modsecurity`; target traffic can enter only through the
containerised Cloudflare tunnel.

## Cloudflared and secret handling

The overlay pins the inspected `cloudflare/cloudflared:2026.7.1` release (and
its digest when available), runs `tunnel --no-autoupdate run`, and reads the
tunnel token from a host path outside the repository through a read-only
Compose secret/mount. The token is never represented in `.env`, command
arguments, rendered configuration, logs, or snapshots.

## Source-verification contract

The existing `SourceProvenance.CLOUDFLARE_CONNECTING_IP` value and
`cloudflare_tunnel` mode remain unchanged. The bridge is the authoritative
adapter for ModSecurity audit evidence: it derives the source only from
canonical `transaction.client_ip`, identifies the event as ModSecurity audit
evidence, and assigns provenance server-side. Authenticated internal ingest and
the isolated deployment boundary are required before a verified status can be
possible. Caller payloads cannot choose trusted provenance or `VERIFIED`.

The bridge continues to exclude audit part B and does not need to recover the
raw `CF-Connecting-IP` header from audit JSON. Ordinary local/direct and
unverified modes remain `UNVERIFIED`.

## Validation and manual proof

Tests cover rendered topology, static address and real-IP trust, no host port,
secret non-disclosure, direct/cross-container isolation, provenance forgery,
canonical persistence, existing Cloudflare/direct-source behavior, and mapped
IPv6 policy. The manual runbook documents creation of the
`cybertrace-target-docker` tunnel, temporary proof hostname, Cloudflare Access,
home/mobile and forgery probes, source correlation, cutover, and rollback.

This repository preparation does not change the live Cloudflare Dashboard or
the existing `app.cybertracesystems.com` Windows tunnel.
