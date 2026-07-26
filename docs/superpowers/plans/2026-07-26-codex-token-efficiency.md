# Codex Token-Efficient CyberTrace Setup Implementation Plan

> **For agentic workers:** Execute inline in this session. Do not dispatch subagents.

**Goal:** Apply the evidence-backed lean Codex setup and create only specialized profiles whose configuration can be validated locally.

**Architecture:** Keep global defaults lean and reversible. Use profile overlays only for verified MCP or skill paths; leave generic plugin enablement and unverified external capabilities unchanged. Keep repository continuity rules in ignored handoff/tooling files and the durable routing rules in `AGENTS.md`.

**Tech Stack:** Codex CLI on Windows, TOML configuration, PowerShell verification, Git, CyberTrace Markdown documentation, Python documentation-navigation test.

---

### Task 1: Preserve the global configuration

**Files:**
- Create: `C:\Users\froi\.codex\config.toml.bak-20260726-token-efficiency` or a non-overwriting timestamped variant.
- Read: `C:\Users\froi\.codex\config.toml`

- [x] Confirm the requested backup name did not already exist.
- [x] Copy the current configuration without printing credential values.
- [x] Verify the backup exists, is readable, and record byte length and SHA-256 hash.

### Task 2: Apply the verified lean global defaults

**Files:**
- Modify: `C:\Users\froi\.codex\config.toml`

- [x] Add low reasoning/verbosity while preserving the unverified current model.
- [x] Add `tool_output_token_limit = 8000`; installed strict validation accepts it.
- [x] Disable multi-agent capability with accepted `features.multi_agent = false`.
- [x] Disable Filesystem, `context-mode`, Node REPL, GitHub, Supabase, OpenAI Developer Docs, standalone Context7, and Codebase Memory.
- [x] Add `skills.config` entries only for existing directories containing readable `SKILL.md`.
- [x] Leave generic plugin enablement unchanged; the installed schema did not verify a generic key.

### Task 3: Create only evidence-backed profile overlays

**Files:**
- Create: `C:\Users\froi\.codex\cybertrace-pr.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-db.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-ui.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-security.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-research.config.toml`

- [x] Use extensionless profile names with the installed CLI's `--profile` option.
- [x] Enable only configured MCP overlays whose declarations exist locally.
- [x] Keep Context7 disabled because no standalone handshake and lookup succeeded.
- [x] Keep Codebase Memory disabled as `DISABLED_PENDING_SAFE_REPAIR`.
- [x] Keep agents disabled in every profile; no subagent test was run.
- [x] Name at most one repository-local Playwright skill directory in the UI profile.
- [x] Preserve the current model because runtime availability was not verified.
- [!] Profile files parse, but runtime capability is `CONFIG_VALID_RUNTIME_UNVERIFIED` or `BROKEN`; none is marked working.

### Task 4: Add CyberTrace continuity guidance

**Files:**
- Create: `G:\AI\PDDDD\injection-alert-system\.codex\TASK_HANDOFF.md`
- Modify: `G:\AI\PDDDD\injection-alert-system\.gitignore`
- Modify: `G:\AI\PDDDD\injection-alert-system\AGENTS.md`
- Modify: `G:\AI\PDDDD\injection-alert-system\agent-tooling.md`

- [x] Add and populate the handoff template and ignore it in Git.
- [x] Add concise rules for bounded reading, compact output, narrow tests, no repeated work, and handoff updates.
- [x] Keep secrets, generated directories, and raw logs out of normal context.
- [x] Document the verified/default/profile state and explicit unresolved items in the ignored tooling guide.

### Task 5: Add the measurement protocol without running the benchmark

**Files:**
- Create: `G:\AI\PDDDD\injection-alert-system\docs\project-ops\CODEX_TOKEN_EFFICIENCY.md`

- [x] Define 10 paired bounded task categories and a 20-run initial baseline-versus-lean cohort.
- [x] Define fields for correctness, turns, tool calls, files reread, compactions, repeated work, and quota movement.
- [x] Exclude RTK until it is separately and safely installed; do not claim savings.

### Task 6: Verify and report

- [x] Inspect supported CLI help before using verification commands.
- [x] Run strict validation for the base config and each profile parse.
- [x] Run redacted `codex mcp list` and `codex plugin list`; record the profile-list limitation.
- [x] Verify every skill directory and `SKILL.md`.
- [x] Run `git check-ignore -q .codex/TASK_HANDOFF.md`, `git diff --check`, and the targeted documentation-navigation test.
- [x] Confirm no credential values appear in reports and global config files are not repository changes.
- [x] Report precise partial, unverified, broken, not-run, and no-change states.
