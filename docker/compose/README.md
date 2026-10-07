# Compose file layout

The repository-root `docker-compose.yml` is the canonical default stack, and
`docker-compose.local.yml` is the local/CI override. Keep both at the root so
Docker Compose discovery and the CI commands continue to work unchanged. The
active target/deployment overlays also remain at the root because the existing
launch scripts use those paths. The source-correlation proof pair remains there
as a documented topology.

The remaining test and proof-scenario files are grouped by purpose:

- `tests/` contains disposable test overrides and proof-environment settings.
- `scenarios/` contains multi-service WAF/ML validation stacks.

Run commands from the repository root. When a file under this directory is the
first or only Compose file, pass `--project-directory .` so relative build,
environment, and bind-mount paths continue to resolve from the repository
root. When combining an overlay with the normal stack, list the root
`docker-compose.yml` first, then the overlay. Do not use these disposable test
overrides as hosted deployment configuration.
