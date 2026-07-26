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
- The global configuration currently enables Filesystem, the `context-mode` MCP
  server, Node REPL,
  GitHub, OpenAI Developer Docs, Supabase, and a Codebase Memory server.
- The configured Codebase Memory executable does not currently exist at
  `C:\Users\froi\AppData\Local\codebase-memory-mcp\codebase-memory-mcp.exe`.
- RTK is not installed or available on PATH.
- CyberTrace has useful repository-local governance skills, but also has local
  Playwright and web-research skills that are not needed for normal coding.
- `.codex/TASK_HANDOFF.md` does not currently exist and is not yet ignored.

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

Disable non-coding plugins and duplicate local skills without deleting their
files. This is reversible and avoids changing the installed skill/plugin cache.
GitHub CLI, repository Playwright, Semgrep, Gitleaks, and native shell commands
remain available as ordinary local tools.

The current official configuration reference lists `tool_output_token_limit`.
Add it at `8000` as an experimental starting value, then validate it with the
installed CLI's strict configuration mode. If this installed CLI rejects it,
remove it and record `NOT_SUPPORTED_BY_INSTALLED_CLI` with the exact error.
Compact command guidance and low model verbosity remain useful regardless.

### 2. Named profiles

Codex profile names omit the filename extension. For example, profile name
`cybertrace-pr` loads the exact file
`C:\Users\froi\.codex\cybertrace-pr.config.toml` as an overlay on the base
`config.toml`. Each profile must be parsed and started in a new Codex process;
a profile that parses but cannot expose its intended capability is not marked
working.

Create these global profiles beside `config.toml`:

- `cybertrace-pr.config.toml`: GitHub connector on; agents remain off.
- `cybertrace-db.config.toml`: Supabase and the separate `context7` MCP server
  on; agents remain off. This does not enable the separate `context-mode` MCP
  server, which stays off.
- `cybertrace-ui.config.toml`: at most one verified Playwright skill on. Generic
  plugin enablement is not changed unless the installed CLI confirms that key;
  otherwise browser-plugin state is `UNVERIFIED_NO_CHANGE`.
- `cybertrace-security.config.toml`: GitHub connector on for PR review; local security CLI
  tools remain the primary path; the missing Codebase Memory server remains off.
- `cybertrace-research.config.toml`: OpenAI Developer Docs and web-research
  skill on, with higher reasoning only if the selected model is verified. Agent
  enablement remains disabled unless a harmless runtime test is authorized and
  succeeds; this task does not perform that test.

Each profile is a TOML overlay selected with `codex --profile <name>`; for
example, `codex --profile cybertrace-pr`. The overlay changes only the relevant
`mcp_servers.<name>.enabled`, `plugins."<plugin-id>".enabled`,
`skills.config[].enabled`, `agents.enabled`,
`agents.max_concurrent_threads_per_session`, `model`, and
`model_reasoning_effort` values. The default profile remains the lean
configuration. Profiles require a new Codex process/session to load.

The exact state matrix is:

| Profile | MCP servers enabled | Plugins enabled | Extra skills enabled | Agents | Model / effort |
| --- | --- | --- | --- | --- | --- |
| default | none of `codebase-memory`, `context-mode`, `context7`, `filesystem`, `github`, `node_repl`, `openaiDeveloperDocs`, `supabase` | unchanged unless generic plugin syntax is verified | none; retain only governance, security, GitHub, and frontend skills | off | current verified model / low |
| `cybertrace-pr` | `github` | none | default set | off | Luna / low |
| `cybertrace-db` | `supabase`, `context7` | none | default set | off | Luna / low |
| `cybertrace-ui` | none | unchanged unless generic plugin syntax is verified | at most one verified Playwright skill directory | off | current verified model / low |
| `cybertrace-security` | `github` | none | default set, including security skills | off | Luna / medium |
| `cybertrace-research` | `openaiDeveloperDocs` | unchanged | `G:\AI\PDDDD\injection-alert-system\.agents\skills\web-research-agent` if verified | off unless separately authorized and runtime-tested | current verified model / high if supported |

The installed plugin list exposes these plugin IDs, but the generic top-level
`plugins."<plugin-id>".enabled` key is not assumed. It will not be written
unless strict validation and current CLI documentation confirm it. Therefore
their state is recorded as `UNVERIFIED_NO_CHANGE` in this task. The exact
plugin IDs observed are
`documents@openai-primary-runtime`, `pdf@openai-primary-runtime`,
`spreadsheets@openai-primary-runtime`, `presentations@openai-primary-runtime`,
`template-creator@openai-primary-runtime`, `sites@openai-bundled`,
`browser@openai-bundled`, `chrome@openai-bundled`,
`computer-use@openai-bundled`, and `visualize@openai-bundled`. The UI profile
re-enables only `browser@openai-bundled`; Chrome remains disabled.

The exact skill directories disabled in the default profile are
`C:\Users\froi\.codex\skills\doc`, `C:\Users\froi\.codex\skills\pdf`,
`C:\Users\froi\.codex\skills\playwright`,
`C:\Users\froi\.codex\skills\playwright-interactive`,
`C:\Users\froi\.codex\skills\screenshot`,
`C:\Users\froi\.codex\skills\vercel-deploy`,
`G:\AI\PDDDD\injection-alert-system\.agents\skills\playwright-cli`, and
`G:\AI\PDDDD\injection-alert-system\.agents\skills\web-research-agent`.
Each directory must exist and contain a readable `SKILL.md` before an entry is
added. The UI/research profiles re-enable only a verified directory and never
both Playwright directories. The existing governance, security, GitHub, and
frontend skills remain installed and enabled.

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
  credentials redacted. For profile checks, prefix the same commands with
  `codex --profile <name>`.
- Run `git check-ignore -q .codex/TASK_HANDOFF.md` and require success.
- Run `git diff --check` and
  `.venv\Scripts\python.exe -m pytest -q tests/unit/test_docs_navigation.py`.
- Validate each profile's feature states from its redacted config and command
  output against the state matrix. The default must show agents and all listed
  MCPs/plugins disabled; each profile may differ only in the allowlisted MCP,
  plugin, skill, agent, model, and effort values in its row.
- Report unavailable Codebase Memory and RTK as `NOT_RUN`, not as successful.

## Rollback

Before changing the global configuration, create and verify a dated backup at
`C:\Users\froi\.codex\config.toml.bak-20260726-token-efficiency`. Roll back by
restoring that file or by re-enabling the affected MCP/plugin/skill entries.
Do not overwrite an existing backup; use a timestamped variant. Record its
timestamp, byte length, and SHA-256 hash. The existing
`config.toml.bak-20260316-192832` is older historical evidence, not the primary
rollback source. The installed plugin and skill files are not deleted.
