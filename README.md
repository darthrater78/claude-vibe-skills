# claude-vibe-skills

One skill for disciplined vibe coding: commit approval, branch-based development, versioned builds, security scanning, code quality checks, cost control, and a strict 6-gate release workflow.

## What it does

`dev-skills` enforces four things:

1. **Commits require approval.** Claude never runs `git commit`, `git push`, or `gh pr create` without your explicit say-so. No more surprise commits after a single change.

2. **Branch-based development.** All work happens on feature/fix branches — never directly on main/master. At session start, the skill detects the git repo, offers to sync with origin, and flags if you're on the default branch.

3. **Six gates before anything ships.** Every session that produces a build moves through version → build → security → docs → release → ship in order. No gate can be silently skipped.

4. **Security and quality scanning.** After every build, a full code scan runs automatically — checking for hardcoded secrets, injection vectors, spaghetti code, N+1 queries, and more. Critical and high findings block the release.

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

The skill uses a tiered loading strategy to keep token costs down:

| File | Size | Loaded when |
|---|---|---|
| `SKILL.md` | ~28KB | Every turn (gates, commit discipline, cost discipline, category-level security/quality awareness) |
| `SECURITY_REFERENCE.md` | ~14KB | Gate 3 + audit mode (full rule checklists + bad/good code examples) |
| `QUALITY_REFERENCE.md` | ~15KB | Gate 3 + audit mode (full rule checklists + bad/good code examples) |
| `SHELL_REFERENCE.md` | ~3KB | Section 5.7 — when git commands need shell-specific formatting |

`SKILL.md` carries the gate workflow, commit discipline, cost controls, and category-level security/quality awareness — enough for Claude to write secure, clean code by default. Shell-specific command formatting, detailed security/quality rule checklists, and pattern-matching code examples live in reference files, loaded on demand where they're needed most.

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

`v2.10.1`

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
