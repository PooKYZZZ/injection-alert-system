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

- [ ] Confirm the requested backup name does not already exist.
- [ ] Copy the current configuration without printing credential values.
- [ ] Verify the backup exists, is readable, and record byte length and SHA-256 hash.

### Task 2: Apply the verified lean global defaults

**Files:**
- Modify: `C:\Users\froi\.codex\config.toml`

- [ ] Add `model_reasoning_effort = "low"` and `model_verbosity = "low"` while preserving the current model unless availability is directly verified.
- [ ] Add `tool_output_token_limit = 8000`; run installed strict validation and remove it with `NOT_SUPPORTED_BY_INSTALLED_CLI` evidence if rejected.
- [ ] Disable `features.multi_agent` and `[agents].enabled` using accepted keys.
- [ ] Set `enabled = false` for Filesystem, `context-mode`, Node REPL, GitHub, Supabase, OpenAI Developer Docs, standalone Context7, and Codebase Memory.
- [ ] Add `skills.config` entries only for existing directories containing readable `SKILL.md`; use directory paths, never file paths.
- [ ] Do not add generic top-level plugin enablement keys because the installed schema has not verified them.

### Task 3: Create only evidence-backed profile overlays

**Files:**
- Create: `C:\Users\froi\.codex\cybertrace-pr.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-db.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-ui.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-security.config.toml`
- Create: `C:\Users\froi\.codex\cybertrace-research.config.toml`

- [ ] Use extensionless profile names with the installed CLI's `--profile` option.
- [ ] Enable only configured MCP servers whose declarations exist locally.
- [ ] Keep Context7 disabled unless its standalone handshake and harmless lookup succeed.
- [ ] Keep Codebase Memory disabled as `DISABLED_PENDING_SAFE_REPAIR`.
- [ ] Keep agents disabled in every profile because this task explicitly forbids subagents; record research-agent enablement as `NOT_RUN`.
- [ ] Re-enable at most one verified Playwright skill directory in the UI profile; do not enable both global and repository-local Playwright skills.
- [ ] Preserve the current model when the account model list cannot be directly verified.

### Task 4: Add CyberTrace continuity guidance

**Files:**
- Create: `G:\AI\PDDDD\injection-alert-system\.codex\TASK_HANDOFF.md`
- Modify: `G:\AI\PDDDD\injection-alert-system\.gitignore`
- Modify: `G:\AI\PDDDD\injection-alert-system\AGENTS.md`
- Modify: `G:\AI\PDDDD\injection-alert-system\agent-tooling.md`

- [ ] Add the handoff template and ignore it in Git.
- [ ] Add concise rules for bounded reading, compact output, narrow tests, no repeated work, and handoff updates.
- [ ] Keep secrets, generated directories, and raw logs out of normal context.
- [ ] Document the verified/default/profile state and explicit unresolved items in the ignored tooling guide.

### Task 5: Add the measurement protocol without running the benchmark

**Files:**
- Create: `G:\AI\PDDDD\injection-alert-system\docs\project-ops\CODEX_TOKEN_EFFICIENCY.md`

- [ ] Define 10 paired bounded task categories and a 20-run initial baseline-versus-lean cohort.
- [ ] Record correctness, turns, tool calls, files reread, compactions, repeated work, and quota movement.
- [ ] Exclude RTK until it is separately and safely installed; do not claim savings.

### Task 6: Verify and report

- [ ] Inspect supported CLI help before using verification commands.
- [ ] Run strict TOML validation for the base config and each created profile where supported.
- [ ] Run `codex mcp list` with redacted output and inspect effective profile states where the CLI exposes them.
- [ ] Verify every skill directory and `SKILL.md`.
- [ ] Run `git check-ignore -q .codex/TASK_HANDOFF.md`, `git diff --check`, and the targeted documentation-navigation test.
- [ ] Confirm no credential values appear in reports and global config files are not repository changes.
- [ ] Report `VERIFIED_WORKING`, `VERIFIED_PARTIAL`, `CONFIG_VALID_RUNTIME_UNVERIFIED`, `BROKEN`, `NOT_RUN`, and `UNVERIFIED_NO_CHANGE` precisely.

