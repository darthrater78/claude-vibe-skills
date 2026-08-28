# claude-vibe-skills

One skill for disciplined vibe coding: commit approval, versioned builds, security scanning, code quality checks, cost control, and a strict 6-gate release workflow — all enforced automatically, every session.

## What it does

`dev-skills` is an always-on skill that enforces three things:

1. **Commits require approval.** Claude never runs `git commit`, `git push`, or `gh pr create` without your explicit say-so. No more surprise commits after a single change.

2. **Six gates before anything ships.** Every session that produces a build moves through version → build → security → docs → release → push in order. No gate can be silently skipped.

3. **Security and quality scanning.** After every build, a full code scan runs automatically — checking for hardcoded secrets, injection vectors, spaghetti code, N+1 queries, and more. Critical and high findings block the release.

```
🔢 VERSION  →  🔨 BUILD  →  🔒 SECURITY  →  📄 DOCS  →  📦 RELEASE  →  🚀 PUSH
```

---

## Download

Download `dev-skills.skill` from the [latest release](../../releases/latest).

| File | Direct download |
|---|---|
| `dev-skills.skill` | [Download](../../releases/latest/download/dev-skills.skill) |

---

## Install

### Claude Desktop (Windows / macOS)

1. Download `dev-skills.skill` from the [latest release](../../releases/latest)
2. Open Claude Desktop → **Customize** → **Import skill**
3. Select `dev-skills.skill`
4. **Fully close and restart Claude Desktop** (quit from system tray, not just close the window)

The skill activates automatically based on trigger phrases — just talk to Claude normally.

### Claude Code (CLI)

Skills installed in Claude Desktop are automatically available in Claude Code on the same machine.

Alternatively, extract the `.skill` file (it's a zip) to `~/.claude/skills/dev-skills/`:

```bash
mkdir -p ~/.claude/skills/dev-skills
unzip dev-skills.skill -d ~/.claude/skills/dev-skills/
```

### Ad hoc use (no install)

Drop the `.skill` file into a Claude Desktop chat, or reference it in Claude Code:

```bash
claude "@path/to/dev-skills.skill let's build this"
```

Session-only — nothing is installed.

---

## What's inside

The skill uses a two-tier loading strategy to keep token costs down:

| File | Size | Loaded when |
|---|---|---|
| `SKILL.md` | ~28KB | Every turn (terse rules, gates, cost discipline) |
| `SECURITY_REFERENCE.md` | ~9KB | Gate 3 + audit mode (bad/good code examples) |
| `QUALITY_REFERENCE.md` | ~13KB | Gate 3 + audit mode (structure + performance examples) |

The terse rules in `SKILL.md` are enough for Claude to write secure, clean code by default. The reference files load on demand during security scans and audits, where pattern-matching against examples matters most.

---

## The six gates

### Gate 1 — Version 🔢

No build starts until every version file (`package.json`, `pyproject.toml`, `VERSION`, etc.) is bumped, consistent, and includes the repository URL. Also greps the entire project for hardcoded version strings in source code, UI templates (XAML, HTML), window titles, "About" dialogs, and config files — every match must be updated.

### Gate 2 — Build 🔨

Runs the project's build command. Build failure stops everything.

### Gate 3 — Security & Quality 🔒

Mandatory after every build. Loads both reference files and scans all source code for:

**Security:**
- Hardcoded secrets, SQL injection, command injection, disabled TLS
- Path traversal, missing auth, weak crypto, unsafe deserialization
- Platform-specific: PowerShell injection, UNC path attacks, DLL hijacking (Windows); SUID misuse, container security, symlink races, systemd hardening (Linux)
- Dependency auditing: typosquatting, unpinned versions, known CVEs

**Code quality:**
- Deep nesting, god functions, circular dependencies, hidden side effects
- N+1 queries, wrong data structures, string concat in loops, blocking I/O
- Unbounded caches, missing indexes, unnecessary allocations, premature abstraction

Critical and High findings must be fixed. Medium and Low are surfaced for your decision. Gate passes at zero Critical and zero High.

### Gate 4 — Docs 📄

Checks that README/CHANGELOG has a version entry, new features are documented, removed features have no stale references, and architecture docs match the code.

### Gate 5 — Release 📦

Creates a feature branch, gets commit approval, pushes, opens a PR with release notes, waits for your approval, merges (never squash-merges), tags, and creates a GitHub release.

### Gate 6 — Push 🚀

Shows the full push summary and waits for your explicit typed confirmation. "yeah" is not enough — type "push" or "confirm push".

---

## Cost discipline

The skill also keeps sessions cheap:

- **Sonnet ceiling** — flags if the session is running on an expensive model and asks before proceeding
- **Effort fit** — recommends `/effort` changes when the task doesn't match the level
- **MCP awareness** — identifies unused MCP servers adding token overhead and shows how to disable them
- **Phase transitions** — offers handoff summaries at natural breakpoints so you can start a fresh, cheap session
- **Token impact estimates** — rough end-of-task report showing what was saved and what was wasted

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
- `dev-mode.skill` — no longer needed (this skill is always-on)
- `cost-saver.skill` — merged into Section 5 (Cost discipline)
- `vibe-coding-workflow.skill` — merged into Section 2 (The six gates)
- `vibe-secure-vibe-coding.skill` — merged into Section 4 (Security rules)

Uninstall the old skills and install `dev-skills.skill`. Everything that worked before still works — plus commit approval, code quality scanning, Windows/Linux platform security, and lower token costs via two-tier loading.

---

## Using without Claude Desktop (browser claude.ai)

Skills are not natively supported in the browser. As a workaround:

1. Download the `.skill` file
2. Open it as a ZIP (rename to `.zip` or use any zip tool)
3. Copy the contents of `SKILL.md`
4. Paste at the start of your Claude conversation:

   > "Please follow these instructions for this session: [paste SKILL.md content]"

Won't persist across conversations or auto-trigger — you'll need to paste each time.

---

## Version

`v2.1.0`
