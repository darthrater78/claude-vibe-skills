# claude-vibe-skills

One skill for disciplined vibe coding: commit approval, branch-based development, versioned builds, security scanning, code quality checks, cost control, and a strict 6-gate release workflow.

## What it does

`dev-skills` enforces four things:

1. **Commits require approval.** Claude never runs `git commit`, `git push`, or `gh pr create` without your explicit say-so. No more surprise commits after a single change.

2. **Branch-based development.** All work happens on feature/fix branches — never directly on main/master. At session start, the skill detects the git repo, offers to sync with origin, and flags if you're on the default branch.

3. **Gates before anything ships.** A work commit needs the security gate and your approval. Anything that bumps a version, builds an artifact, merges, tags, or publishes runs the full six — version → build → security → docs → release → ship, in order. No gate can be silently skipped, and presenting a git command for you to paste counts as running it.

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
| `SKILL.md` | ~38KB | **Every turn** — commit discipline, the gate pre-flight, the two tracks, gate state, shortcut detection, always-on security awareness, cost discipline |
| `GATE_REFERENCE.md` | ~40KB | When a gate runs, and at session start — each gate's checks and pass criteria, plus the session-start procedure |
| `SECURITY_REFERENCE.md` | ~22KB | Gate 3 + audit mode (full rule checklists + bad/good code examples) |
| `QUALITY_REFERENCE.md` | ~20KB | Gate 3 + audit mode (full rule checklists + bad/good code examples) |
| `SHELL_REFERENCE.md` | ~5KB | Section 5.7 — when git commands need shell-specific formatting (local and Termux sessions) |

The repo also ships `hooks/gate-preflight.sh`, an optional enforcement hook — it is not part of the skill bundle and is installed separately (see below).

The split follows one rule: **triggers load every turn, recipes load on demand.** `SKILL.md` holds what has to fire without being asked — commit discipline, the gate pre-flight, the two tracks, shortcut detection, always-on security awareness, cost controls. How to actually *run* a gate lives in `GATE_REFERENCE.md`, loaded when the pre-flight says one is owed. Security and quality checklists and shell formatting work the same way.

Sizes in this table are verified by `scripts/validate.sh`. `SKILL.md` is paid for on every request, so an understated figure hides a real per-turn cost.

Releases are published by CI: pushing a `v*` tag runs `.github/workflows/release.yml`, which verifies the tagged commit is on the default branch, rebuilds `dev-skills.skill` from the tagged source, publishes the release with notes taken from `CHANGELOG.md`, and fails if the artifact does not end up attached. The default-branch check matters because a tag trigger fires for a tag on *any* commit — without it, tagging an unreviewed branch would publish a real release from unreviewed code. Both workflows pin `actions/checkout` to a commit SHA rather than a mutable version tag, check out with `persist-credentials: false`, and carry concurrency groups and timeouts.

---

## How gates are enforced

Gate state is not something Claude remembers — it is a file, `.claude/dev-skills-gates.md`, written at session start and updated on every gate transition. Long sessions get compacted and a tracker rebuilt from memory is rebuilt optimistically, so the file is the source of truth. If it is missing or stale, Claude re-derives each gate from evidence (version files, build artifacts, the current diff, the changelog, open PRs, remote tags) rather than assuming anything passed.

**Presenting a git command counts as running it.** Whether Claude executes `git push` or prints it in a block for you to paste, the same pre-flight runs and the tracker appears above the block. This closes the gap where a skill could be followed to the letter and still skip every gate.

**Two tracks, so the checklist is always answerable:**

| Track | What it covers | Gates required |
|---|---|---|
| **Work commit** | saving progress mid-session on a branch | Security (on the changed code) + commit approval |
| **Release sequence** | version bump, artifact, merge to default branch, tag, or publish | all six, in order |

Gates apply by default to any session that modified a tracked file. There is no "too small to bother" exemption — a gate leaves the workflow only by being marked ➖ N/A for a structural reason (no build system, for example), stated on the tracker.

**Unfinished releases are caught at session start.** Gate 6 has four parts — merge, tag, publish, verify — and a session can die between any two of them: a container reclaimed, a usage limit, a tag push denied `403`. The work is then stranded on the default branch, and the next session would otherwise never look for it, because it starts with all gates pending for the version it is *about* to build. So session start compares released versions against tags on the remote and reports any that never shipped, before new work begins.

Every tag check reads the remote (`git ls-remote --tags origin`), never `git tag -l` — the latter lists *local* tags and returns empty in any fresh clone, which is every remote container. A check that reports every prior version as untagged is a check nobody reads, and a genuine missing tag hides in that noise.

---

## Enforcement hook (optional)

`hooks/gate-preflight.sh` is a `PreToolUse` hook that **blocks** git write operations whose required gates have not passed, reading `.claude/dev-skills-gates.md` for state. Where it is installed, the pre-flight stops being advisory for anything Claude runs itself.

| Operation | Gates required before it runs |
|---|---|
| `git commit`, `git push` to a branch | Security |
| `gh pr create`, MCP `create_pull_request` | Version, Build, Security, Docs |
| `git tag`, `git push --tags`, `gh pr merge`, `gh release create`, MCP `merge_pull_request` | Version, Build, Security, Docs, Release |

Read-only git is never blocked. Install instructions, the settings snippet, and failure modes are in [`hooks/README.md`](hooks/README.md).

It covers what Claude executes — not commands presented for you to paste, and not git you run yourself. So it is strongest on remote container sessions, where Claude executes git directly, and weakest on local sessions, where presenting commands is the default. The prose rule that presenting a command counts as performing it covers the rest.

---

## Execution environments

The skill detects where the session is running, because it determines whether Claude's working tree and your terminal are the same clone:

| Environment | Git behavior |
|---|---|
| **Local** (Claude Code CLI) | Commands are presented for you to run — same clone, and it costs no tool-call tokens |
| **Remote container** (web/mobile) | Claude commits and pushes directly — except tag pushes. Your terminal is a different machine with a different clone; a pasted block would commit nothing, and container work is destroyed when the session ends |
| **Termux** (Android) | Clone flow — the repo may not be on the device |

Remote containers also skip the shell question, arrive pre-cloned (no `git clone` step), commit the gate state file with the work instead of gitignoring it, and fall back to GitHub MCP tools when `gh` is unavailable.

**Tag pushes are the one operation that always comes back to you.** In every environment, `git tag` and `git push origin v<X.Y.Z>` are presented as a block for you to run — never executed by Claude, never created through a GitHub MCP tool. The credentials Claude runs under are routinely denied on tag refs: a token that pushes branch commits all session gets `403` on `git push origin v1.2.3`, because creating a `refs/tags/*` ref — and creating a ref that *triggers a workflow* — is a separate permission, commonly withheld even where `contents: write` is granted. And the blast radius is worse than an ordinary denial, since the tag push is what fires the release workflow: a 403 there strands a merged, version-bumped default branch with no release behind it. Gate 6 stays ⏳ until the tag is confirmed on the remote with `git ls-remote` — never ✅ on the assumption you ran it. Deleting and re-pushing a tag follow the same rule, and there's a GitHub UI fallback (**Releases → Draft a new release → Choose a tag**) if you have no local clone.

---

## Two workflows: local dev and CI

Session start detects two distinct workflows, because different gates depend on each and a project can easily have one without the other.

| Workflow | What it is | Which gate uses it |
|---|---|---|
| **Local development** | what you run on your own machine to build and test — `scripts/`, `Makefile`, `package.json` scripts, `gradlew`, `tox.ini`, `CONTRIBUTING.md` instructions | **Gate 2 (Build)** runs this |
| **CI build check** | compiles and tests on push or pull request | validates the PR opened by **Gate 5** |
| **CI release workflow** | builds artifacts and publishes on tag push (`on: push: tags:`) | fired by **Gate 6 (Ship)** |

Whichever is missing is surfaced against the gate it breaks, not reported as a generic absence. No local dev workflow means Gate 2 has no command to run, so "verified working" is a guess — and "CI will catch it" is explicitly rejected, because CI runs *after* the commit Gate 2 exists to protect. No release workflow means Gate 6 has no publish path.

When both exist, they are checked for drift: CI should invoke the project's own scripts (`bash scripts/validate.sh`, `npm test`, `./gradlew test`) rather than reimplementing the build inline, or the two pass and fail independently until a release breaks.

---

## The six gates

### Gate 1 — Version 🔢

No build starts until every version file (`package.json`, `pyproject.toml`, `VERSION`, etc.) is bumped, consistent, and includes the repository URL. Also greps the entire project for hardcoded version strings in source code, UI templates (XAML, HTML), window titles, "About" dialogs, and config files — every match must be updated. Any app that displays a repo link must also link to the current version's release notes.

**A missing tag for the immediately preceding version hard-blocks this gate.** It doesn't mean someone forgot to tag — it means the last release never finished Gate 6, so the default branch carries a version that was never published. Bumping on top of it buries the gap one version deeper. Older gaps stay advisory.

### Gate 2 — Build 🔨

Runs the project's **local development workflow** — its own build and test commands, not CI. Build failure stops everything. A project with a build system but no discoverable local build command blocks the gate and asks, rather than passing as ➖ N/A: N/A is for projects with no build system, not for builds that couldn't be found.

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

Merges the PR, tags the merge commit, creates a GitHub release with artifacts, and runs post-ship verification (tag on remote, release exists, PR merged, release assets attached). Shows the full ship summary and waits for explicit confirmation — "yeah" is not enough, type "ship" or "confirm ship". The tag push itself always comes back to you (see above).

**The git flow is identical on Linux, Windows, and Android** — merge, checkout, pull, tag, push, verify. Only what CI *builds* differs, and Gate 6 carries a table of it: runner, release build command, artifact type, signing secrets, job shell, and the platform-specific ship failure — a debug or unstripped binary on Linux, an unsigned or self-signed executable on Windows, a debug-signed or wrongly named APK on Android (`<app-name>-v<VERSION>.apk`; "debug" in the filename is a ship failure). It also names the two cross-platform traps that produce a release that looks fine and is not: CRLF line endings reaching a Windows runner, and case sensitivity differing between Linux and Windows runners.

---

## Cost discipline

The skill also keeps sessions cheap:

- **Sonnet ceiling** — flags if the session is running on an expensive model and asks before proceeding
- **Effort fit** — recommends `/effort` changes when the task doesn't match the level
- **MCP awareness** — identifies unused MCP servers adding token overhead and shows how to disable them
- **Phase transitions** — offers handoff summaries at natural breakpoints so you can start a fresh, cheap session
- **Token impact estimates** — rough end-of-task report showing what was saved and what was wasted
- **Git command presentation** — on local sessions, presents git commands for manual execution, as a single copy-once block per operation rather than split across several to minimize tool-call token overhead; asks your shell environment (PowerShell, Git Bash, Termux, macOS, Linux, WSL) and formats all commands for that shell, always starting with the proper `cd` command. Remote container sessions execute directly instead, since a presented block would operate on the wrong clone
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
| "just give me the commands" | Same gates as executing them — tracker shown above the block |
| "don't worry about the gates this time" | Gates only leave the workflow as ➖ N/A for structural reasons |

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

`v2.15.0`

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
