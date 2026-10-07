# Docker Compose layout

Compose files are grouped here by purpose:

- `base.yml` defines the default dashboard and backend services.
- `overlays/` contains local database, demo-target, hosted-target, and
  Cloudflare-specific additions.
- `tests/` contains disposable test overrides, including the source-correlation
  proof pair.
- `scenarios/` contains bounded multi-service proof and integration stacks.

Backend, bridge, and PR7 WAF image definitions live in `docker/images/`.
Windows convenience launchers live in `scripts/windows/`; their implementation
remains in `scripts/`.

## Local environment file

Keep local credentials in `.local/env/.env`, which is ignored by Git. Create it
from the committed template at the repository root:

```powershell
New-Item -ItemType Directory -Force .local/env | Out-Null
Copy-Item .env.example .local/env/.env
```

Edit the copied file locally; never commit it. The frontend's separate
`frontend/.env.local` remains in the frontend directory.

## Compose commands

Run commands from the repository root. The explicit project directory keeps
bind mounts, build contexts, and service environment files anchored to the
repository after these files were moved. `--env-file` supplies interpolation
values. These commands are intended to run from the repository root; scripts
pass the equivalent absolute project and environment paths.

Start the ordinary application with the local PostgreSQL overlay:

```powershell
docker compose --project-directory . --env-file .local/env/.env `
  -p injection-alert-system `
  -f docker/compose/base.yml `
  -f docker/compose/overlays/local.yml up -d --build
```

Add the optional technical WAF and demo target when needed:

```powershell
docker compose --project-directory . --env-file .local/env/.env `
  -p injection-alert-system `
  -f docker/compose/base.yml `
  -f docker/compose/overlays/local.yml `
  -f docker/compose/overlays/demo-target.yml `
  --profile technical-waf --profile demo-target up -d --build
```

Use the dedicated launchers in `scripts/windows/` for the complete local or
Cloudflare target workflows. Do not combine test overrides with a hosted
deployment configuration.
