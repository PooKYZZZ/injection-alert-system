# Cloudflare Target Ingress Isolation Runbook

**Status:** Repository preparation only. Manual Dashboard and network proof
remain required. Keep `WAF_SOURCE_VERIFICATION_MODE=unverified`.

## Preconditions

Use the repository root in PowerShell. Do not put a token in `.env`, a command
argument, a source file, a test fixture, or a log. Create the secret directory
outside the repository:

```powershell
$secretDir = Join-Path $env:USERPROFILE "CyberTrace-Secrets"
New-Item -ItemType Directory -Force -Path $secretDir | Out-Null
$env:CLOUDFLARED_TARGET_TOKEN_FILE = Join-Path $secretDir "cloudflared-target.token"
```

Do not print the file or its contents. The exact token is obtained only from
the Dashboard's **Add replica** workflow after the tunnel is created.

## Create the temporary Cloudflare tunnel

1. Create a remotely managed tunnel named `cybertrace-target-docker`.
2. Add `target-proof.cybertracesystems.com` with service URL
   `http://demo-target-modsecurity:8080`.
3. Protect the proof hostname with the appropriate Cloudflare Access policy;
   do not create a bypass policy for the proof host.
4. Use the tunnel's **Add replica** workflow to obtain the Docker token. Save
   it to `%USERPROFILE%\CyberTrace-Secrets\cloudflared-target.token` without
   displaying it. Confirm the file is outside the repository and readable only
   by the operator account.
5. Confirm Pseudo IPv4 is **Off** and no Worker is in this request path.

## Start the isolated target stack

Keep the existing Windows `cloudflared` process running; it continues to serve
`app.cybertracesystems.com`. The target overlay has no WAF host port.

```powershell
$env:WAF_SOURCE_VERIFICATION_MODE = "unverified"
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare config --format json | Out-File "$env:TEMP\cybertrace-target-compose.json" -Encoding utf8
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare up -d --build
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare ps
docker inspect --format '{{json .State.Health}}' injection-alert-system-cloudflared-1
```

The rendered configuration must show no `demo-target-modsecurity` `ports`,
only `cloudflared` and ModSecurity on the internal WAF ingress network, and
`172.30.20.2/32` as the sole real-IP trust value. Do not retain rendered output
containing environment-specific paths longer than needed.

The current target overlay defaults to `unverified` and sets
`CLOUDFLARE_TARGET_ISOLATION_ENABLED=true`. The cloudflared health check uses
exec form (`CMD cloudflared tunnel ready --metrics 127.0.0.1:20241`) because the
pinned image has no `/bin/sh`.

## Explicit future verified-mode proof switch

Do not run this during the current preflight. After the temporary proof has
been independently reviewed, the exact guarded command is:

```powershell
$env:CLOUDFLARE_TARGET_VERIFIED_PROOF = "true"
$env:WAF_SOURCE_VERIFICATION_MODE = "cloudflare_tunnel"
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare up -d --no-deps --force-recreate backend
```

The backend rejects `cloudflare_tunnel` unless the isolation overlay is active
and this explicit proof switch is true. The switch is rejected in
`unverified` mode and the default remains `unverified`. This command does not
enable PR7 enforcement.

The bridge must also be explicitly configured for the matching
`cloudflare_connecting_ip` provenance mode before a future verified proof.
The 2026-07-28 guarded attempt stopped at the evidence gate because the bridge
still had its safe default `WAF_SOURCE_PROVENANCE_MODE=direct_remote_addr`; the
resulting row correctly remained `DIRECT_REMOTE_ADDR` / `UNVERIFIED`. Do not
treat that attempt as a verified proof or enable enforcement based on it.

## Temporary proof sequence

Run every request first from home Wi-Fi and then from mobile data. Record only
hostname, timestamp, response status, transaction ID, and canonical source
values; redact Access and tunnel credentials.

1. Request `https://target-proof.cybertracesystems.com/` from both networks.
2. Submit a CRS-triggering synthetic request through the proof hostname.
3. Send forged `CF-Connecting-IP` and `X-Forwarded-For` headers; neither may
   replace the Cloudflare visitor value.
4. Attempt `http://127.0.0.1:8089` and `http://<LAN-IP>:8089` from the host and
   another LAN device. Both must fail.
5. From a disposable non-cloudflared container, attempt to resolve and reach
   `demo-target-modsecurity:8080` through the WAF ingress network. It must fail.
6. Correlate the same CRS transaction across ModSecurity audit evidence,
   bridge output, authenticated FastAPI lookup, and the persisted database.
   The required equality is:

   ```text
   persisted source_ip
   == ModSecurity transaction.client_ip
   == NGINX effective remote_addr
   == Cloudflare visitor identity
   ```

   Audit part `B` must remain excluded; the bridge must use
   `transaction.client_ip` and must not need raw `CF-Connecting-IP` from audit
   JSON.
7. Verify ordinary local/unverified mode remains `UNVERIFIED`, generic payloads
   cannot choose trusted provenance, and no token appears in Compose output or
   logs.
8. Confirm home/mobile source separation, direct-origin failure, host-level and
   cross-container forgery resistance, no Worker path, and Pseudo IPv4 Off.
   Hosted PR7 enforcement remains disabled.

## Final cutover after proof passes

1. In the new tunnel, replace only the temporary route with
   `target.cybertracesystems.com -> http://demo-target-modsecurity:8080`.
2. Remove `target.cybertracesystems.com` from the original Windows tunnel.
   Keep `app.cybertracesystems.com -> localhost:3000` there.
3. Repeat normal, CRS, and correlation checks.
4. Remove `target-proof.cybertracesystems.com` after final validation.
5. Keep verification `unverified` until a later explicit authorization.

## Rollback

1. Restore the original Windows route:
   `target.cybertracesystems.com -> localhost:8089`.
2. Keep `app.cybertracesystems.com -> localhost:3000` unchanged.
3. Stop only the target-only stack:

   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.demo-target.yml -f docker-compose.target-cloudflare.yml --profile demo-target --profile target-cloudflare down
   ```

4. Recreate the original hosted target stack with the existing
   `docker-compose.hosted-target.yml` and ignored `.env` configuration. Keep it
   `unverified`; the original gateway peer is not an authenticated tunnel.
5. Remove the temporary proof hostname and revoke/rotate the target token in
   Cloudflare if it was exposed or the cutover was abandoned.
