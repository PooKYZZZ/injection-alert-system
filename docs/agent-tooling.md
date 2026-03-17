# Agent Tooling Playbook

Use this file when the task depends on **tool choice**, **MCP routing**, **browser automation**, **documentation lookup**, **GitHub data**, or **large outputs** that could waste context.

This file is written for the current Codex setup:

- model: `gpt-5.4`
- reasoning effort: `medium`
- personality: `pragmatic`
- sandbox: `workspace-write`
- Windows sandbox: `elevated`
- network access: enabled in workspace-write
- configured MCP servers:
  - `filesystem`
  - `codebase-memory`
  - `serena`
  - `github`
  - `openaiDeveloperDocs`
  - `context-mode`
- configured but currently disabled:
  - `playwright`
  - `context7`

## Why this file exists

Root `AGENTS.md` should stay focused on **repo truth**:
- project identity
- stack
- commands
- architecture boundaries
- security rules
- business rules
- verification expectations

Detailed MCP and CLI routing belongs here so the root file stays high-signal and does not become a giant tool manual.

## Core principles

- Choose the **smallest capable tool** for the task.
- Prefer **authoritative tools** over generic ones.
- Prefer **structured or indexed retrieval** over dumping raw output into context.
- Prefer **CLI-first workflows** when the official tool explicitly recommends them for coding agents.
- Prefer **repo-aware symbolic tools** before broad filesystem scans.
- Use a **real browser** only when browser behavior actually matters.
- For large data, prefer **context-preserving** tools and narrowed queries.

## Current routing summary

### Keep using MCP for these
- `filesystem`
- `codebase-memory`
- `serena`
- `github`
- `openaiDeveloperDocs`
- `context-mode`

### Prefer CLI-first for these
- `playwright-cli` instead of Playwright MCP for normal browser work in Codex
- `ctx7` instead of Context7 MCP for framework/library docs in Codex

### Why
- Playwright’s official repos say coding agents are often better served by the CLI path than Playwright MCP.
- Context7 officially supports both MCP and CLI + Skills, and the CLI path is appropriate for coding-agent doc lookup.
- codebase-memory supports both MCP and CLI, but keeping MCP available is still useful because it gives Codex a structured code graph tool surface.
- Serena is primarily an MCP-driven coding-agent toolkit even though it is launched via CLI.
- OpenAI Developer Docs is a hosted remote MCP server, so MCP is the intended access path.
- Filesystem is an MCP server started from CLI, not a separate “CLI-first replacement.”
- context-mode is specifically useful when raw output would otherwise pollute context.

## Preferred tool by task

### 1) `context-mode`
Use first when the task is likely to produce **large output** or raw data that should not enter context directly.

Use for:
- logs
- large JSON
- large Markdown
- long command output
- fetched pages
- repo research with many files
- reading generated outputs
- repeated querying over the same large content

Prefer it for:
- “read these logs and summarize”
- “inspect this large JSON payload”
- “read a long Markdown report”
- “fetch a page and query it without pasting everything into context”
- “run multiple commands and summarize the results”

Use these patterns conceptually:
- one big command → sandbox execution
- many commands → batched execution
- one large file → execute/process file in sandbox
- one large document used multiple times → index then search
- one web page used multiple times → fetch, index, then search

Use `context-mode` before:
- raw shell commands that will print a lot
- direct large file reads
- broad web fetches that dump content into context

Avoid it when:
- you need direct file mutation
- the output is trivially small
- a symbolic/indexed repo tool is clearly better

Important:
- context-mode’s own docs say instruction-only routing is weaker than hook-enforced routing.
- In this setup, treat context-mode as a strong preference and best practice, not magical guaranteed enforcement.

### 2) `openaiDeveloperDocs`
Use for anything specifically about:
- OpenAI products
- Codex
- ChatGPT
- Responses API
- models
- official OpenAI MCP behavior
- OpenAI tool/config/docs usage

Prefer this over generic web search for official OpenAI product questions.

Use it for:
- “How does Codex MCP config work?”
- “What is the official OpenAI docs MCP URL?”
- “How should AGENTS.md be structured in Codex?”
- “What does OpenAI say about MCP?”

Do not use generic web search first when this server can answer the question from official docs.

### 3) `codebase-memory`
This is the default codebase understanding tool for **architecture-scale** questions.

Use for:
- architecture discovery
- dependency tracing
- symbol relationships
- hotspots
- route/module relationships
- blast radius analysis
- change impact
- codebase-wide structural navigation

Best for questions like:
- “Where does this feature flow through the codebase?”
- “What symbols are affected if I change this service?”
- “What are the main entry points?”
- “What files/modules are coupled to this component?”
- “Trace call paths / impact / architecture”

Prefer this before:
- broad filesystem scans
- manual grep across the whole repo
- reading many files one by one

Keep in mind:
- codebase-memory also has a CLI mode, but MCP remains useful here because Codex can directly use the structured graph tools.

### 4) `serena`
Use when you know or partly know the symbol or code object you need and want **precise semantic navigation or edits**.

Use for:
- symbol-aware lookup
- class/function/method targeting
- precise code navigation
- structured edits when the file/symbol is partly known

Best for questions like:
- “Find the function that builds this payload”
- “Edit this specific method”
- “Locate the exact symbol implementing X”
- “Rename or adjust a symbol-aware implementation path”

Prefer Serena over raw filesystem reads when:
- the task is centered on code symbols, not general codebase structure
- the exact file is not yet certain but the symbol is partly known

### 5) `filesystem`
Use for **exact file reads/writes** when symbolic tools are not the better fit.

Use for:
- reading the exact contents of a known file
- writing or editing specific files
- checking local file presence/paths
- small direct reads where a symbolic/indexed tool is unnecessary

Do not use it as the first choice for:
- broad repo exploration
- architecture discovery
- codebase-wide analysis
- large output inspection

Use it after you already know the file you need, or when the task is simple and direct.

### 6) `github`
Use for live GitHub data and repository metadata.

Use for:
- issues
- pull requests
- releases
- branches
- remote file contents
- repository metadata
- GitHub-side code search across repos
- GitHub workflow/repo context that does not live only in the local checkout

Prefer it over generic web search for GitHub-native data.

Use it for:
- “Find the latest release”
- “Read this PR”
- “Search issues for this error”
- “Check branches or release tags”
- “Read a remote file in another repo”

Current setup uses the **remote hosted GitHub MCP server** with `GITHUB_PERSONAL_ACCESS_TOKEN`.

### 7) `ctx7` CLI
Use for framework/library/product documentation when version-sensitive technical docs matter.

This is the preferred doc-lookup path for:
- FastAPI
- Next.js
- React
- Tailwind
- shadcn/ui
- Zustand
- TanStack Query
- Zod
- PyTorch
- Transformers
- Supabase
- Docker
- OWASP CRS
- ModSecurity
- and similar tools

Workflow:
1. resolve the library:
   - `ctx7 library <name> <query>`
2. fetch docs for the chosen library ID:
   - `ctx7 docs <libraryId> <query>`

Use `ctx7` before generic web search for official/product documentation, especially when version drift matters.

Current config note:
- `context7` MCP is configured but disabled.
- For Codex work, prefer the CLI-first `ctx7` path.

### 8) `playwright-cli`
Use for browser automation, rendering checks, screenshots, and UI validation that truly require a browser.

Default to `playwright-cli` for:
- open/goto
- click/type
- snapshot
- screenshot
- console/network inspection
- basic browser interaction in Codex

Prefer `playwright-cli` over Playwright MCP unless the task specifically needs:
- a long-lived MCP browser session
- a workflow built around persistent MCP browser state
- MCP-native browser tooling for a reason that clearly outweighs the CLI path

Current config note:
- Playwright MCP is configured but disabled.
- For Codex, treat `playwright-cli` as the normal browser path.

## Practical routing rules

### Use `context-mode` first when:
- expected output is larger than a small terminal screen
- reading logs, big JSON, big Markdown, or fetched pages
- a task would otherwise require dumping lots of raw content
- you need to run multiple inspection commands and summarize them

### Use `codebase-memory` first when:
- the task is “understand the codebase”
- the task is “trace relationships”
- the task is “find blast radius / architecture / hotspots”
- the task is broader than one symbol or one file

### Use `serena` first when:
- the task is centered on a symbol
- a precise semantic edit or exact symbol lookup is needed

### Use `filesystem` first when:
- you already know the exact file
- you need exact file content
- you need direct writes

### Use `github` first when:
- the truth lives on GitHub rather than only in the local repo
- you need issues, PRs, releases, branches, or remote repo context

### Use `openaiDeveloperDocs` first when:
- the question is about OpenAI/Codex official behavior or docs

### Use `ctx7` first when:
- the question is “how does framework/library X work?”
- version-sensitive docs matter

### Use `playwright-cli` first when:
- real browser behavior matters

## Fallback order

If the preferred tool cannot complete the task:

1. choose the next smallest capable authoritative tool
2. narrow the request instead of broadening it
3. avoid raw output dumps unless unavoidable
4. only use generic web search when no better authoritative tool exists

Examples:
- If `codebase-memory` is not the right fit for a precise symbol edit, switch to `serena`.
- If `serena` is not the right fit because you need exact file contents, switch to `filesystem`.
- If `ctx7` does not answer a docs question fully, supplement with web search.
- If a browser is unnecessary, do not escalate to `playwright-cli`.
- If output gets large, route through `context-mode`.

## Anti-patterns

Do not:
- start with broad filesystem scans when a symbolic/indexed tool fits
- dump huge logs or JSON into context directly
- use generic web search for GitHub data that `github` can provide
- use generic web search first for official OpenAI questions when `openaiDeveloperDocs` can answer
- use Context7 MCP just because it exists when `ctx7` CLI is the intended lower-context path here
- use Playwright MCP by default for everyday Codex browser tasks
- read large docs or pages raw when `context-mode` can fetch/index/search them
- use `filesystem` as a substitute for architecture analysis
- use `serena` as a substitute for broad codebase graph exploration

## Task examples

### Example: “Find where alert confidence thresholds are enforced”
1. start with `codebase-memory`
2. if you need exact symbol targeting, switch to `serena`
3. once the file is known, use `filesystem` to read/edit

### Example: “Check latest official OpenAI guidance for Codex MCP”
1. use `openaiDeveloperDocs`
2. only supplement with web search if something is missing

### Example: “Look up the correct Next.js or Zod pattern”
1. use `ctx7 library ...`
2. use `ctx7 docs ...`
3. supplement with web search only if needed

### Example: “Inspect a huge test log”
1. use `context-mode`
2. summarize/narrow
3. only read exact file contents directly if needed for editing

### Example: “Open the app and verify rendering”
1. use `playwright-cli`
2. only prefer Playwright MCP if a long-lived MCP session is specifically needed

### Example: “Check a PR / issue / release”
1. use `github`
2. do not start with web search

## Notes on current local setup

The following reflect the current Codex config:

### Active MCP servers
- `filesystem`
- `codebase-memory`
- `serena`
- `github`
- `openaiDeveloperDocs`
- `context-mode`

### Disabled MCP servers
- `playwright`
- `context7`

### Why those are disabled
Because this setup prefers:
- `playwright-cli` for normal browser tasks
- `ctx7` CLI for normal library/framework docs lookup

### Environment assumptions
- workspace-write sandbox
- Windows elevated sandbox enabled
- network access allowed in workspace-write

When a task depends on OS-specific behavior, keep Windows in mind first.

## Validation habits

When using tooling:
- narrow the question before expanding scope
- prefer one strong call over many weak exploratory calls
- if output is truncated, request a narrower slice instead of rerunning everything
- stop once you know the exact file, symbol, or command you need
- treat repo-aware and official-doc tools as primary sources

## If tool choice is still unclear

Choose in this order:

1. Is the question about official OpenAI/Codex behavior?
   - use `openaiDeveloperDocs`

2. Is it about framework/library docs?
   - use `ctx7`

3. Is it about browser/UI behavior?
   - use `playwright-cli`

4. Is it broad repo understanding or impact analysis?
   - use `codebase-memory`

5. Is it a precise symbol/code navigation task?
   - use `serena`

6. Is it an exact file read/write task?
   - use `filesystem`

7. Is it GitHub-side metadata or repo state?
   - use `github`

8. Is the output likely to be large?
   - route through `context-mode`

If two tools seem valid, prefer the one that:
- is more authoritative for the source
- returns less raw output
- reduces context waste
- avoids unnecessary exploration