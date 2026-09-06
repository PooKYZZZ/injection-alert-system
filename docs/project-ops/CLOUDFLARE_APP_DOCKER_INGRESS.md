# Docker-managed app Cloudflare ingress

## Purpose

This document records the local Docker wiring required when the Cloudflare
published application route is:

```text
app.cybertracesystems.com -> http://frontend:3000
```

The route is configured in the Cloudflare dashboard. This repository change
only makes the `frontend` service name reachable from the Docker-managed
`cloudflared` connector.

The target Cloudflare overlay pins the official `cloudflare/cloudflared`
`2026.8.3` multi-architecture image by digest. The tunnel command keeps
`--no-autoupdate`, so future upgrades are deliberate, reviewable Compose
changes followed by a controlled container recreation.

## Local topology

The frontend remains on the Compose `default` network so it can reach
`backend:8000`. The app ingress overlay adds a separate internal network that
contains only `frontend` and `cloudflared`:

```text
frontend -------- default -------- backend
    |
    +--- app_cloudflare_ingress --- cloudflared
                                      |
                                      +--- target_waf_ingress --- demo-target-modsecurity
                                      +--- target_cloudflare_egress --- Cloudflare
```

The overlay does not attach `cloudflared` to the whole default network, and it
does not add the app ingress network to the backend or target WAF.

## Startup

Use `scripts/start_full_cloudflare_target.ps1` or
`START_FULL_CLOUDFLARE_TARGET.bat`. The launcher now includes:

```text
docker-compose.app-cloudflare.yml
```

The token remains a Compose secret loaded from the operator's external token
file. Do not copy it into this document, `.env`, or a command argument.

## Verification

After startup, verify the merged model and runtime membership:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml -f docker-compose.app-cloudflare.yml --profile demo-target --profile target-cloudflare config --quiet
docker network inspect injection-alert-system_app_cloudflare_ingress
docker network inspect injection-alert-system_default
```

The rendered model must show:

* `frontend` on `default` and `app_cloudflare_ingress`;
* `cloudflared` on `app_cloudflare_ingress`, `target_cloudflare_egress`, and
  `target_waf_ingress`;
* `backend` absent from `app_cloudflare_ingress`; and
* `demo-target-modsecurity` absent from `app_cloudflare_ingress`.

The Cloudflare dashboard route and the public hostname still require a live
manual check. A green tunnel status alone does not prove that the frontend
origin is reachable.
