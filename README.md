# claude-vibe-skills

One skill for disciplined vibe coding: commit approval, versioned builds, security scanning, code quality checks, cost control, and a strict 6-gate release workflow.

## What it does

`dev-skills` enforces three things:

1. **Commits require approval.** Claude never runs `git commit`, `git push`, or `gh pr create` without your explicit say-so. No more surprise commits after a single change.

2. **Six gates before anything ships.** Every session that produces a build moves through version → build → security → docs → release → ship in order. No gate can be silently skipped.

3. **Security and quality scanning.** After every build, a full code scan runs automatically — checking for hardcoded secrets, injection vectors, spaghetti code, N+1 queries, and more. Critical and high findings block the release.

```
🔢 VERSION  →  🔨 BUILD  →  🔒 SECURITY  →  📄 DOCS  →  📦 RELEASE  →  🚀 SHIP
```

---

## Download

Download `dev-skills.skill` from the [latest release](../../releases/latest).

| File | Direct download |
|---|---|
| `dev-skills.skill` | [Download](../../releases/latest/download/dev-skills.skill) |

---

## Install

### Claude.ai (browser — recommended)

1. Download `dev-skills.skill` from the [latest release](../../releases/latest)
2. Go to [claude.ai](https://claude.ai) → **Customize** → **Skills** → upload the `.skill` file
3. The skill syncs to Claude Desktop and Claude Code on the web automatically

### Claude Desktop (Windows / macOS)

1. Download `dev-skills.skill` from the [latest release](../../releases/latest)
2. Open Claude Desktop → **Customize** → **Skills** → upload the `.skill` file

The skill activates on trigger phrases (see the trigger list in the skill description) or when invoked with `/dev-skills`.

### Claude Code (CLI)

Skills uploaded via claude.ai sync automatically. To install manually instead,
extract the `.skill` file (it's a zip) to `~/.claude/skills/dev-skills/`:

```bash
mkdir -p ~/.claude/skills/dev-skills
unzip dev-skills.skill -d ~/.claude/skills/dev-skills/
```

### Claude Code on the web (claude.ai/code)

Skills uploaded via claude.ai sync automatically. Project-level skills
committed to `.claude/skills/` in a repo also load when the repo is cloned.

---

## What's inside

The skill uses a two-tier loading strategy to keep token costs down:

| File | Size | Loaded when |
|---|---|---|
| `SKILL.md` | ~33KB | Every turn (gates, commit discipline, cost discipline, category-level security/quality awareness) |
| `SECURITY_REFERENCE.md` | ~14KB | Gate 3 + audit mode (full rule checklists + bad/good code examples) |
| `QUALITY_REFERENCE.md` | ~15KB | Gate 3 + audit mode (full rule checklists + bad/good code examples) |

`SKILL.md` carries the gate workflow, commit discipline, cost controls, and category-level security/quality awareness — enough for Claude to write secure, clean code by default. The detailed rule checklists and pattern-matching code examples live in the reference files, loaded on demand during Gate 3 scans and audit mode where they're needed most. This saves ~1,125 tokens per request compared to loading everything on every turn.

---

## The six gates

### Gate 1 — Version 🔢

No build starts until every version file (`package.json`, `pyproject.toml`, `VERSION`, etc.) is bumped, consistent, and includes the repository URL. Also greps the entire project for hardcoded version strings in source code, UI templates (XAML, HTML), window titles, "About" dialogs, and config files — every match must be updated. Any app that displays a repo link must also link to the current version's release notes.

### Gate 2 — Build 🔨

Runs the project's build command. Build failure stops everything.

### Gate 3 — Security & Quality 🔒

Mandatory after every build. Loads both reference files and scans all source code for:

**Security:**
- Hardcoded secrets, SQL injection, command injection, disabled TLS
- Path traversal, missing auth, weak crypto, unsafe deserialization
- Platform-specific: PowerShell injection, UNC path attacks, DLL hijacking (Windows); SUID misuse, container security, symlink races, systemd hardening (Linux); exported components, WebView RCE, Intent spoofing, insecure storage (Android)
- Dependency auditing: typosquatting, unpinned versions, known CVEs

**Code quality:**
- Deep nesting, god functions, circular dependencies, hidden side effects
- N+1 queries, wrong data structures, string concat in loops, blocking I/O
- Unbounded caches, missing indexes, unnecessary allocations, premature abstraction
- Container dependency drift: Dockerfiles hardcoding packages instead of installing from dependency files, imports missing from declared dependencies

Critical and High findings must be fixed. Medium and Low are surfaced for your decision. Gate passes at zero Critical and zero High.

### Gate 4 — Docs 📄

Checks that README/CHANGELOG has a version entry, new features are documented, removed features have no stale references, and architecture docs match the code.

### Gate 5 — Release 📦

Checks prerequisites first (GitHub remote exists, default branch is pushed, `gh` CLI is authenticated), then creates a feature branch, gets commit approval, pushes, and opens a PR with release notes. Never falls back to direct commits on main — if infrastructure isn't set up, it blocks and helps you fix it.

### Gate 6 — Ship 🚀

Merges the PR, tags the merge commit, creates a GitHub release with artifacts, and runs post-ship verification (tag on remote, release exists, PR merged, release assets attached). Android projects must include a properly named APK (`<app-name>-v<VERSION>.apk`) — "debug" in the filename is a ship failure. Shows the full ship summary and waits for explicit confirmation — "yeah" is not enough, type "ship" or "confirm ship".

---

## Cost discipline

The skill also keeps sessions cheap:

- **Sonnet ceiling** — flags if the session is running on an expensive model and asks before proceeding
- **Effort fit** — recommends `/effort` changes when the task doesn't match the level
- **MCP awareness** — identifies unused MCP servers adding token overhead and shows how to disable them
- **Phase transitions** — offers handoff summaries at natural breakpoints so you can start a fresh, cheap session
- **Token impact estimates** — rough end-of-task report showing what was saved and what was wasted
- **Git command presentation** — defaults to presenting git commands for manual execution to minimize tool-call token overhead; asks your shell environment (PowerShell, Git Bash, Termux, macOS, Linux, WSL) and formats all commands for that shell, always starting with the proper `cd` command
- **Usage limit handoff** — proactively offers a handoff summary when the account is nearing its usage cap so you can resume in a fresh session without losing progress

---

## Audit mode

Say "audit my project", "scan this codebase", or "security review" to trigger a full scan outside the gate workflow. Outputs findings by severity with file:line, description, and fix for each.

---

## Shortcut detection

| What you say | What happens |
|---|---|
| "just push it" | Gate tracker shown, all prior gates checked |
| "skip the version bump" | Hard stop — version is required |
| "we can do security later" | Security scan runs now, no exceptions |
| "just ship it" / "done" | All open gates walked through |
| "just commit this" | Shows what would be committed, waits for approval |

---

## Migrating from the old skills

This single skill replaces all four previous skills:
- `dev-mode.skill` — no longer needed (this skill covers the same triggers)
- `cost-saver.skill` — merged into Cost discipline
- `vibe-coding-workflow.skill` — merged into The six gates
- `vibe-secure-vibe-coding.skill` — merged into Security rules

Uninstall the old skills and install `dev-skills.skill`. Everything that worked before still works — plus commit approval, code quality scanning, Windows/Linux platform security, and lower token costs via two-tier loading.

---

## Version

`v2.9.0`

### Version history

**v2.9.0** — 2026-09-05
- Git command presentation (5.8) now defaults to presenting commands for manual execution to save tool-call token overhead — Claude never assumes direct execution without the user choosing it; gates 1, 5, and 6 reference this pattern
- Android APK artifact requirement in Gate 6: Android projects must include a properly named APK (`<app-name>-v<VERSION>.apk`) as a release asset — "debug" in the filename is a ship failure

**v2.8.0** — 2026-09-04
- Git command presentation (5.8): asks the user's shell environment (PowerShell, Git Bash, Termux, macOS, Linux, WSL) and adapts all presented git/gh commands to that shell — always starts with a `cd` to the project directory, never assumes the user is already there
- Usage limit handoff (5.9): proactively offers a handoff summary when the account is nearing its usage cap, including gate tracker state and shell environment so the next session can resume without re-asking

**v2.7.3** — 2026-09-03
- Added Android platform security checks: exported components, manifest hardening, WebView RCE, Intent validation, secure storage (EncryptedSharedPreferences/Keystore), network security config, certificate pinning, logging hygiene, ProGuard/R8
- Added Android quality patterns: main thread blocking (ANR prevention), Activity/Fragment lifecycle leaks, RecyclerView best practices, overdraw reduction

**v2.7.2** — 2026-09-03
- Gate 3 quality review now catches container dependency drift — Dockerfiles that hardcode package lists instead of installing from dependency files, and new imports missing from dependency declarations

**v2.7.1** — 2026-09-01
- Gate 6 (Ship) now actively scans for artifact evidence — checks build tooling (PyInstaller, Makefile, cargo, etc.), README download references, and prior release assets instead of passively assuming "no artifacts"

**v2.7.0** — 2026-08-31
- Replaced automated version update check with a static releases link — automated check was unreliable across environments
- Expanded cost discipline (Section 5.1) with five new rules: tool call batching, grep-before-read, git diff over full reads, minimize agent spawns, text over screenshots

**v2.5.0** — 2026-08-31
- Removed `alwaysApply: true` — feature does not work reliably; skill activates via trigger phrases or `/dev-skills` instead
- Gate 5 (Release) now checks prerequisites before PR workflow: GitHub remote must exist, default branch must be pushed, `gh` CLI must be authenticated — prevents silent fallback to direct commits on new repos
- Session-start MCP check now shows specific disable commands per active server (not just a generic `/mcp` suggestion)

**v2.4.0** — 2026-08-31
- Version field in SKILL.md frontmatter — session start banner now shows which version is loaded
- MCP server check at session start — reports active/deferred servers with `/mcp` toggle instructions

**v2.3.2** — 2026-08-30
- Gate 4 (Docs) now includes internal consistency check — cross-checks README descriptions against SKILL.md source of truth for renamed concepts, restructured workflows, and changed terminology

**v2.3.1** — 2026-08-30
- Gate 6 (Ship) now enforces distributable artifact rebuild before release creation and verifies release assets are attached

**v2.3.0** — 2026-08-30
- Gate 5/6 restructured: Release (PR prep) and Ship (merge+tag+publish with mandatory post-verification)
- Hook output is never commit approval — explicit guard added
- Auto mode cannot override commit discipline
- N/A gate mechanism (➖) for structurally inapplicable gates
- Session-end checkpoint catches uncommitted changes and untagged versions before winding down
- Self-check at session start verifies reference files exist
- Performance trim: moved ~104 lines of detailed security/quality rules from SKILL.md to on-demand reference files (~1,125 tokens/request savings)
- Reference files now include full rule checklists alongside code examples

**v2.2.0** — 2026-08-28
- Gate 1 now requires a release notes link alongside the repository link in any app that displays one (About dialogs, settings screens, footers, help menus)
- Fix: prevent hook output from being treated as commit approval

**v2.1.0** — 2026-08-28
- Gate pre-flight enforcement on every git write operation
- Source-code version string scanning (XAML, HTML, UI templates, About dialogs)
