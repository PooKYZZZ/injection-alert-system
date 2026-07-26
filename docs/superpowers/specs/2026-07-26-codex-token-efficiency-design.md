# Codex Token-Efficient CyberTrace Setup

Date: 2026-07-26

## Goal

Apply the reviewed token-efficiency recommendations to the local Codex setup used
for CyberTrace while preserving a reversible path for specialized work. The
default setup should minimize unnecessary MCP, plugin, skill, subagent, and
output overhead. Specialized profiles should re-enable only the capability they
need.

## Current evidence

- Global Codex configuration is at `C:\Users\froi\.codex\config.toml`.
- CyberTrace is `G:\AI\PDDDD\injection-alert-system`.
- Installed CLI: Codex `0.142.0`; `codex --strict-config doctor --summary --no-color`
  accepts the edited base configuration.
- The current model remains `gpt-5.6-luna`. A fresh CLI runtime probe could not
  use it because this installed CLI reports that the model requires a newer
  Codex version. The model was therefore not changed.
- The configured Codebase Memory executable does not currently exist at
  `C:\Users\froi\AppData\Local\codebase-memory-mcp\codebase-memory-mcp.exe`.
- RTK is not installed or available on PATH.
- The standalone Context7 server remains disabled because no handshake or
  harmless lookup was run.
- The installed plugin list was inspected, but the CLI does not expose a
  verified generic plugin enable/disable setting. Plugin state is therefore
  `UNVERIFIED_NO_CHANGE`.
- `.codex/TASK_HANDOFF.md` now exists and is ignored by Git.

## Design

### 1. Lean global defaults

Keep native shell, search, file access, Memories, and the existing model family.
Set the default reasoning effort and response verbosity to low, and disable
multi-agent tools by default. Disable redundant or task-specific MCP servers:
Filesystem, the `context-mode` MCP server, Node REPL, GitHub, Supabase, OpenAI
Developer Docs, and the broken Codebase Memory server. Keep the server
declarations in place so
they can be re-enabled or repaired without reconstructing credentials and
commands.

Do not alter installed plugins or skill files. Disable the selected duplicate or
task-specific skill directories through configuration only; this is reversible
and avoids changing the installed skill/plugin cache.
GitHub CLI, repository Playwright, Semgrep, Gitleaks, and native shell commands
remain available as ordinary local tools.

The current official configuration reference lists `tool_output_token_limit`.
It is set to `8000`, and the installed CLI's strict configuration mode accepts
it. This is a configuration acceptance result, not a measured token-saving
result. The selected model also reports that `model_verbosity` is ignored by
that model, so the setting is retained but is not claimed as runtime-effective.
Compact command guidance and low model verbosity remain useful regardless.

### 2. Named profiles

Codex profile names omit the filename extension. For example, profile name
`cybertrace-pr` loads the exact file
`C:\Users\froi\.codex\cybertrace-pr.config.toml` as an overlay on the base
`config.toml`. Each profile must be parsed and started in a new Codex process;
a profile that parses but cannot expose its intended capability is not marked
working.

The five reversible profile overlays were created beside `config.toml`, but none
is marked working. They parse through `codex --profile <name> --strict-config
exec --help`, while fresh runtime probes fail before capability verification:
the installed CLI rejects the current model, and PR/DB probes additionally
reported their existing GitHub/Supabase authorization failures. They remain
`CONFIG_VALID_RUNTIME_UNVERIFIED` or `BROKEN`, never `VERIFIED_WORKING`, until
the CLI/model and connector authorization are independently resolved.

The intended profile scopes are:

- `cybertrace-pr.config.toml`: GitHub connector on; agents remain off.
- `cybertrace-db.config.toml`: Supabase overlay; standalone `context7` remains
  off because its handshake was not run. Agents remain off. This does not
  enable the separate `context-mode` MCP server, which stays off.
- `cybertrace-ui.config.toml`: at most one verified Playwright skill on. Generic
  plugin enablement is not changed unless the installed CLI confirms that key;
  otherwise browser-plugin state is `UNVERIFIED_NO_CHANGE`.
- `cybertrace-security.config.toml`: GitHub connector on for PR review; local security CLI
  tools remain the primary path; the missing Codebase Memory server remains off.
- `cybertrace-research.config.toml`: OpenAI Developer Docs and web-research
  skill overlay, with higher reasoning retained only as configuration. The
  selected model is not runtime-verified by the installed CLI. Agent
  enablement remains disabled because the user explicitly prohibited subagents.

Each profile is a TOML overlay selected with `codex --profile <name>`; for
example, `codex --profile cybertrace-pr`. The installed CLI does not apply
profile overlays to `codex mcp list`, so that command cannot prove effective
profile MCP state. A new runtime process is required, but the current CLI/model
combination prevents that proof. The default profile remains the lean
configuration.

The exact state matrix is:

| Profile | MCP servers enabled | Plugins enabled | Extra skills enabled | Agents | Model / effort |
| --- | --- | --- | --- | --- | --- |
| default | none of `codebase-memory`, `context-mode`, `context7`, `filesystem`, `github`, `node_repl`, `openaiDeveloperDocs`, `supabase` | unchanged unless generic plugin syntax is verified | none; retain only governance, security, GitHub, and frontend skills | off | current model preserved; CLI-unverified / low |
| `cybertrace-pr` | `github` overlay; effective runtime unverified; `BROKEN` probe | unchanged | default set | off | current model / low |
| `cybertrace-db` | `supabase` overlay; `context7` remains off; effective runtime unverified; `BROKEN` probe | unchanged | default set | off | current model / low |
| `cybertrace-ui` | none; `CONFIG_VALID_RUNTIME_UNVERIFIED` | unchanged | one repository-local Playwright directory | off | current model / low |
| `cybertrace-security` | `github` overlay; effective runtime unverified; `BROKEN` probe | unchanged | default set | off | current model / medium |
| `cybertrace-research` | `openaiDeveloperDocs` overlay; effective runtime unverified; `BROKEN` probe | unchanged | one repository-local web-research directory | off | current model / high |

The installed plugin list exposes these plugin IDs, but the generic top-level
`plugins."<plugin-id>".enabled` key is not assumed. It will not be written
unless strict validation and current CLI documentation confirm it. Therefore
their state is recorded as `UNVERIFIED_NO_CHANGE` in this task. The exact
plugin IDs observed are
`documents@openai-primary-runtime`, `pdf@openai-primary-runtime`,
`spreadsheets@openai-primary-runtime`, `presentations@openai-primary-runtime`,
`template-creator@openai-primary-runtime`, `sites@openai-bundled`,
`browser@openai-bundled`, `chrome@openai-bundled`,
`computer-use@openai-bundled`, and `visualize@openai-bundled`. No plugin state
was changed, including the UI profile; all plugin claims remain
`UNVERIFIED_NO_CHANGE`.

The exact skill directories disabled in the default profile are
`C:\Users\froi\.codex\skills\doc`, `C:\Users\froi\.codex\skills\pdf`,
`C:\Users\froi\.codex\skills\playwright`,
`C:\Users\froi\.codex\skills\playwright-interactive`,
`C:\Users\froi\.codex\skills\screenshot`,
`C:\Users\froi\.codex\skills\vercel-deploy`,
`G:\AI\PDDDD\injection-alert-system\.agents\skills\playwright-cli`, and
`G:\AI\PDDDD\injection-alert-system\.agents\skills\web-research-agent`.
Each directory exists and contains a readable `SKILL.md`. The UI profile names
only the repository-local Playwright directory and the research profile names
only the repository-local web-research directory; neither is runtime-verified
because the profile probes stopped at the model error. The existing governance,
security, GitHub, and frontend skills remain installed and enabled.

The installed CLI rejected `[agents] enabled = false` as an unsupported
configuration section. The accepted fallback is `[features] multi_agent =
false`, which disables multi-agent capability in the default configuration.
No agents were enabled or tested, per the user's explicit instruction.

### 3. CyberTrace continuity and routing

Add the ignored `.codex/TASK_HANDOFF.md` template with sections for goal,
current state, relevant files, decisions, completed changes, verification, next
step, and work not to repeat. Extend `AGENTS.md` with concise routing rules:
read only task-relevant files, use compact commands, run narrow tests first,
avoid repeated exploration, do not read secrets/generated directories, and
update the handoff before compaction or ending a long task.

Update the ignored local `agent-tooling.md` with the profile map and compact
output rules so this information does not enlarge the tracked repository
instructions.

### 4. Measurement and unresolved follow-ups

Add the tracked note
`docs/project-ops/CODEX_TOKEN_EFFICIENCY.md` with a ten-task A/B protocol covering baseline,
lean profile, and optional RTK. Record task correctness, turns, tool calls,
files reread, compactions, repeated tests, and quota movement. Do not claim a
percentage reduction until the runs are actually completed.

The ten tasks must be comparable bounded CyberTrace tasks drawn from these
categories: one documentation edit, one backend test fix, one frontend test
fix, one BFF change, one security review, one Git inspection, one log triage,
one Docker/Compose inspection, one Playwright/UI check, and one architecture
investigation. The initial experiment is 20 runs total: each category once in
the current baseline cohort and once with the lean profile. Repeat a category
only when the paired tasks are not comparable. A run is successful only when
the task passes its normal acceptance check without a human correction or a
hidden failure. RTK is a separate future cohort and is excluded from the
initial calculation until an approved installation is available.

Do not install, uninstall, delete, rebuild, or repair LeanCTX, Context Mode,
another graph tool, RTK, or Codebase Memory. Do not attempt a Codebase Memory
rebuild until the missing executable or an authoritative installation source is
located. Mark Codebase Memory `DISABLED_PENDING_SAFE_REPAIR`, RTK `NOT_RUN`,
and unverified generic plugin states `UNVERIFIED_NO_CHANGE` rather than hiding
the evidence gap.

## Verification

- Inspect `codex --help`, `codex doctor --help`, `codex mcp --help`, and
  `codex plugin --help` before selecting verification commands. Use only syntax
  accepted by this installed CLI. Parse the edited global config and every
  profile with the supported strict-validation command and require a successful
  exit code. If a proposed command is unavailable, record it as unavailable and
  use direct TOML parsing plus the closest supported runtime inspection.
- Confirm the default MCP/plugin/skill states with `codex mcp list`,
  `codex plugin list`, and `codex --strict-config doctor --json` while keeping
  credentials redacted. For profiles, `codex --profile <name> --strict-config
  exec --help` proves configuration parsing only; the runtime probes failed on
  the installed CLI/model mismatch. `codex --profile <name> mcp list` was also
  observed to show the base state rather than apply the profile overlay.
- Run `git check-ignore -q .codex/TASK_HANDOFF.md` and require success.
- Run `git diff --check` and
  `.venv\Scripts\python.exe -m pytest -q tests/unit/test_docs_navigation.py`.
- Validate each profile's feature states from its redacted config and command
  output against the state matrix. The default must show all listed MCPs
  disabled and multi-agent disabled. Profile status must be one of
  `CONFIG_VALID_RUNTIME_UNVERIFIED` or `BROKEN`; none is `VERIFIED_WORKING`.
- Report the accepted `tool_output_token_limit = 8000`, the unsupported
  `[agents]` section, the model runtime mismatch, disabled Context7,
  Codebase Memory `DISABLED_PENDING_SAFE_REPAIR`, RTK `NOT_RUN`, and generic
  plugin states `UNVERIFIED_NO_CHANGE` explicitly.

## Rollback

Before changing the global configuration, create and verify a dated backup at
`C:\Users\froi\.codex\config.toml.bak-20260726-token-efficiency`. Roll back by
restoring that file or by re-enabling the affected MCP/plugin/skill entries.
Do not overwrite an existing backup; use a timestamped variant. Record its
timestamp, byte length, and SHA-256 hash. The existing
`config.toml.bak-20260316-192832` is older historical evidence, not the primary
rollback source. The installed plugin and skill files are not deleted.
