# claude-vibe-skills

One skill for disciplined vibe coding. Claude doesn't commit without your
say-so, doesn't ship without walking the gates, and can't quietly skip either.

```
🔢 VERSION  →  🔨 BUILD  →  🔒 SECURITY  →  📄 DOCS  →  📦 RELEASE  →  🚀 SHIP
```

**[⬇ Download `dev-skills.skill`](../../releases/latest/download/dev-skills.skill)** — current version `v2.18.0`

---

## Contents

- [What it does](#what-it-does) — the four rules
- [What's new](#whats-new) — highlights since v2.12
- [What it looks like](#what-it-looks-like) — a session, abridged
- [Install](#install) — claude.ai, Desktop, CLI, web
- [The six gates](#the-six-gates) — what each one checks
- [Two tracks](#two-tracks) — why a work commit isn't a release
- [How gates are enforced](#how-gates-are-enforced) — the state file, and why memory isn't trusted
- [Enforcement hook](#enforcement-hook-optional) — optional, blocks git at the tool call
- [Execution environments](#execution-environments) — local vs. container vs. Termux
- [Workflow detection](#workflow-detection-local-dev-vs-ci) — local dev vs. CI
- [Cost discipline](#cost-discipline) — what's automatic, what you have to ask for
- [Audit mode](#audit-mode) · [Shortcut detection](#shortcut-detection) · [What's inside](#whats-inside) · [For maintainers](#for-maintainers)

---

## What it does

**1. Commits require approval.** Claude never runs `git commit`, `git push`, or
`gh pr create` without your explicit say-so. No surprise commits after a single
edit. A vague "ok" doesn't count, and neither does a hook telling Claude the
tree is dirty.

**2. All work happens on branches.** Never directly on `main`/`master`. At
session start the skill finds the repo, offers to sync with origin, and flags
you if you're sitting on the default branch.

**3. Gates run before anything ships.** A work commit needs the security gate
and your approval. Anything that bumps a version, builds an artifact, merges,
tags, or publishes runs all six, in order. **Presenting a git command for you
to paste counts as running it** — the same pre-flight fires either way.

**4. Security and quality get scanned.** After every build, a full scan checks
for hardcoded secrets, injection vectors, spaghetti code, N+1 queries, and
more. Critical and High findings block the release.

---

## What's new

Highlights since v2.12. Full detail in [CHANGELOG.md](CHANGELOG.md).

- **Gate enforcement stopped being bypassable.** Presenting a git command for
  you to paste now counts as running it — same pre-flight, same tracker. An
  optional [hook](#enforcement-hook-optional) blocks git at the tool call
  itself, and gate state moved into a
  [file](#how-gates-are-enforced) so a compacted session can't "remember" a
  scan that never ran. *(2.12, 2.13)*
- **Ref operations always come back to you.** Tag pushes *and* ref deletions
  are handed over in every environment, containers included — Claude's
  credentials are routinely denied on exactly those two.
  [Why](#tag-pushes-and-ref-deletions-always-come-back-to-you) *(2.15.0, 2.15.2)*
- **Ref checks read the remote.** `git tag -l` and `git branch -r` both report
  absence that means nothing in a fresh clone; every check is now
  `git ls-remote`. *(2.15.0, 2.15.2)*
- **Unfinished releases get caught.** A missing tag for the *previous* version
  hard-blocks Gate 1, and session start compares released versions against
  remote tags — so a release that died between merge and tag surfaces before
  new work buries it. *(2.15.0)*
- **[Local dev and CI are detected separately](#workflow-detection-local-dev-vs-ci).**
  Gate 2 runs *your* build, not CI's — "CI will catch it" is explicitly
  rejected, because CI runs after the commit Gate 2 protects. *(2.15.0)*
- **[Windows security reached parity](#gate-3--security--quality-)** with Linux
  and Android: UAC elevation, DLL search-order hijacking, registry ACLs,
  unquoted service paths, code signing, reserved names. *(2.16.0)*
- **Lower per-turn cost.** Gate execution detail and shell mechanics moved out
  of the every-turn file into [references](#whats-inside) loaded on demand.
  *(2.14.0, 2.16.0)*
- **[Three cost behaviors that never fired now do](#cost-discipline).** The
  token estimate, the phase-transition handoff, and the usage-limit handoff were
  gated on judgment calls and on a token threshold that Claude Code for web
  never crosses. All three now trigger on observable events. *(2.16.1)*
- **[Subagent model delegation](#cost-discipline).** When spawning subagents,
  the cheapest model tier that fits the task is used — Haiku for lookups, Sonnet
  for code work, expensive models only when the session is already approved
  above the Sonnet ceiling. *(2.17.0)*
- **[Guided GitHub Actions workflows](#audit-mode).** New reference file with
  audit and creation procedures: point it at an existing `.github/workflows/`
  for a severity-graded review, or ask it to set one up and it detects your
  project's environment, asks every config question in one turn, and
  generates a template — Docker, Windows, Android, Linux, Home Assistant,
  Python, Node.js, or scripts — with SHA-pinned actions, least-privilege
  permissions, and dev/pre-release build support out of the box. *(2.18.0)*

---

## What it looks like

Trying to skip ahead surfaces the tracker instead of complying:

```
you ▸ just push it

     🔢 VERSION    ✅ v2.18.0 — all refs agree
     🔨 BUILD      ✅ scripts/validate.sh green
     🔒 SECURITY   ⬜ not run against the current diff
     📄 DOCS       ⬜
     📦 RELEASE    ⬜
     🚀 SHIP       ⬜

     Security hasn't run on these changes. Doing that first.
```

Gate state lives in a file, not in Claude's memory:

```
# .claude/dev-skills-gates.md
Track: release sequence
Version: 2.18.0

🔢 VERSION    ✅ all refs at 2.18.0; prev v2.17.0 tagged on remote
🔨 BUILD      ➖ N/A — skill repo, no build system
🔒 SECURITY   ✅ 0 Critical, 0 High
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜
```

Marks mean: ✅ passed · 🚫 blocked · ⏳ in progress · ⬜ pending · ➖ N/A.

---

## Install

Download `dev-skills.skill` from the [latest release](../../releases/latest),
then:

| Where | How |
|---|---|
| **[claude.ai](https://claude.ai)** (recommended) | **Customize** → **Skills** → upload the `.skill` file. Syncs to Desktop and Claude Code on the web automatically. |
| **Claude Desktop** (Win/macOS) | **Customize** → **Skills** → upload the `.skill` file. |
| **Claude Code (CLI)** | Skills uploaded via claude.ai sync automatically. To install by hand, see below. |
| **Claude Code on the web** | Syncs from claude.ai. Project skills committed to `.claude/skills/` also load when the repo is cloned. |

Manual CLI install — the `.skill` file is a zip:

```bash
mkdir -p ~/.claude/skills/dev-skills
unzip dev-skills.skill -d ~/.claude/skills/dev-skills/
```

The skill activates on its trigger phrases ("ship it", "commit", "audit",
"just push it", …) or when you invoke `/dev-skills` directly.

---

## The six gates

### Gate 1 — Version 🔢

No build starts until every version file (`package.json`, `pyproject.toml`,
`VERSION`, …) is bumped, consistent, and includes the repository URL. Greps the
whole project for hardcoded version strings — source, UI templates (XAML,
HTML), window titles, "About" dialogs, config files. Every match must be
updated. Any app that shows a repo link must link the current release notes.

> **A missing tag for the immediately preceding version hard-blocks this gate.**
> It doesn't mean someone forgot to tag — it means the last release never
> finished Gate 6, so the default branch carries a version that was never
> published. Bumping on top of it buries the gap one version deeper. Older gaps
> stay advisory.

### Gate 2 — Build 🔨

Runs the project's **local development workflow** — its own build and test
commands, not CI. Build failure stops everything. A project that has a build
system but no discoverable local build command *blocks* rather than passing as
➖ N/A: N/A is for projects with no build system, not for builds that couldn't
be found.

### Gate 3 — Security & Quality 🔒

Mandatory after every build. Loads both reference files and scans all source.

**Security:** hardcoded secrets · SQL injection · command injection · disabled
TLS · path traversal · missing auth · weak crypto · unsafe deserialization ·
dependency auditing (typosquatting, unpinned versions, known CVEs).

Plus platform-specific rules:

- **Windows** — UAC elevation, PowerShell injection, UNC path attacks, DLL
  hijacking, registry ACLs, unquoted service paths, code signing
- **Linux** — SUID misuse, container security, symlink races, systemd hardening
- **Android** — exported components, WebView RCE, Intent spoofing, insecure storage

**Code quality:** deep nesting · god functions · circular dependencies · hidden
side effects · N+1 queries · wrong data structures · string concat in loops ·
blocking I/O · unbounded caches · missing indexes · premature abstraction ·
container dependency drift (Dockerfiles hardcoding packages instead of
installing from dependency files; imports missing from declared dependencies).

Critical and High must be fixed. Medium and Low are surfaced for your decision.
**Passes at zero Critical, zero High.**

### Gate 4 — Docs 📄

Checks that README/CHANGELOG has an entry for this version, new features are
documented, removed features leave no stale references, and architecture docs
match the code.

### Gate 5 — Release 📦

Checks prerequisites first (GitHub remote exists, default branch pushed, `gh`
authenticated), then creates a feature branch, gets commit approval, pushes,
and opens a PR with release notes. Never falls back to direct commits on main —
if the infrastructure isn't set up, it blocks and helps you fix it.

### Gate 6 — Ship 🚀

Merges the PR, tags the merge commit, creates a GitHub release with artifacts,
then verifies all four post-ship conditions (tag on remote, release exists, PR
merged, assets attached). Shows the full ship summary and waits for explicit
confirmation — "yeah" is not enough; type "ship" or "confirm ship".

The tag push itself always comes back to you — see
[Execution environments](#execution-environments).

<details>
<summary><b>The git flow is identical across platforms — only the CI build differs</b></summary>

Merge, checkout, pull, tag, push, verify is the same on Linux, Windows, and
Android. What CI *builds* is not, so Gate 6 carries a table of it: runner,
release build command, artifact type, signing secrets, job shell, and the
platform-specific ship failure — a debug or unstripped binary on Linux, an
unsigned or self-signed executable on Windows, a debug-signed or wrongly named
APK on Android (`<app-name>-v<VERSION>.apk`; "debug" in the filename is a ship
failure).

It also names the two cross-platform traps that produce a release that looks
fine and isn't: CRLF line endings reaching a Windows runner, and case
sensitivity differing between Linux and Windows runners.

</details>

---

## Two tracks

Not every git operation is a release. The track is decided before gates are
checked, because a checklist that can't be answered tends to get dropped
entirely — and a dropped checklist is a leak.

| Track | What it covers | Gates required |
|---|---|---|
| **Work commit** | saving progress mid-session, on a branch | Security (on the changed code) + commit approval |
| **Release sequence** | version bump, artifact, merge to default branch, tag, or publish | all six, in order |

A work commit never becomes a release by accident. If the operation tags, merges
to the default branch, or publishes, it's a release sequence — regardless of it
being called "just a quick push".

Gates apply by default to any session that modified a tracked file. There is no
"too small to bother" exemption. A gate leaves the workflow exactly one way: by
being marked ➖ N/A for a *structural* reason (no build system, for example),
stated out loud on the tracker.

---

## How gates are enforced

**Gate state is a file, not a memory.** `.claude/dev-skills-gates.md` is written
at session start and updated on every transition. Long sessions get compacted,
and a tracker rebuilt from memory is rebuilt optimistically ("security ran
earlier, I think"). If the file is missing or stale, Claude re-derives each gate
from evidence — version files, build artifacts, the current diff, the changelog,
open PRs, remote tags — rather than assuming anything passed.

**Presenting a git command counts as running it.** Whether Claude executes
`git push` or prints it in a block for you to paste, the same pre-flight runs
and the tracker appears above the block. This closes the gap where the skill
could be followed to the letter and still skip every gate.

**Unfinished releases are caught at session start.** Gate 6 has four parts —
merge, tag, publish, verify — and a session can die between any two: a container
reclaimed, a usage limit, a tag push denied `403`. The work is then stranded on
the default branch, and the next session would never look for it, because it
starts with all gates pending for the version it's *about* to build. So session
start compares released versions against tags on the remote and reports any that
never shipped, before new work begins.

<details>
<summary><b>Why every ref check reads the remote, never a local list</b></summary>

Ref checks use `git ls-remote --tags origin` for tags and
`git ls-remote --heads origin` for branches — never `git tag -l` or
`git branch -r`.

Both local forms report absence that means nothing. `git tag -l` lists *local*
tags, and a fresh clone — every remote container, and any `--no-tags` or shallow
checkout — has none, so it returns empty on a repo with a hundred tags.
`git branch -r` lists cached remote-tracking refs, which go stale the moment
anyone else pushes or deletes a branch and nothing re-fetches.

This matters more than it looks: a check that reports *every* prior version as
untagged, or every branch as gone, is a check nobody reads — and a genuine
missing tag or live branch hides in that noise.

</details>

---

## Enforcement hook (optional)

`hooks/gate-preflight.sh` is a `PreToolUse` hook that **blocks** git write
operations whose required gates haven't passed, reading
`.claude/dev-skills-gates.md` for state. Where it's installed, the pre-flight
stops being advisory for anything Claude runs itself.

| Operation | Gates required before it runs |
|---|---|
| `git commit`, `git push` to a branch | Security |
| `gh pr create`, MCP `create_pull_request` | Version, Build, Security, Docs |
| `git tag`, `git push --tags`, `gh pr merge`, `gh release create`, MCP `merge_pull_request` | Version, Build, Security, Docs, Release |

Read-only git is never blocked. Install instructions, the settings snippet, and
failure modes are in [`hooks/README.md`](hooks/README.md). The hook ships in the
repo, not in the `.skill` bundle — it's installed separately.

**It covers what Claude executes — not commands presented for you to paste, and
not git you run yourself.** So it's strongest on remote container sessions,
where Claude executes git directly, and weakest on local sessions, where
presenting is the default. The prose rule that presenting a command counts as
performing it covers the rest.

---

## Execution environments

The skill detects where the session is running, because that determines whether
Claude's working tree and your terminal are the same clone:

| Environment | Git behavior |
|---|---|
| **Local** (Claude Code CLI) | Same clone — commands are **presented** for you to run, at no tool-call token cost |
| **Remote container** (web/mobile) | A clone your terminal never sees — Claude **executes** git directly. A pasted block would commit nothing, and container work is destroyed when the session ends |
| **Termux** (Android) | Presented, plus a clone flow — the repo may not be on the device |

### Tag pushes and ref deletions always come back to you

In **every** environment, remote containers included, `git tag` /
`git push origin v<X.Y.Z>` and any ref deletion (branch or tag) are presented as
a block for you to run. Claude never executes them, and never creates or deletes
a ref through a GitHub MCP tool.

The reason is permissions. Creating a `refs/tags/*` ref — especially one that
*triggers a workflow* — is commonly withheld even where ordinary branch pushes
succeed, and deleting a ref is a separate permission again. A token that pushes
commits all session can still return `403` on a branch delete.

The tag side carries the worse blast radius: the tag push is what fires the
release workflow, so a `403` there strands a merged, version-bumped default
branch with no release behind it. **Gate 6 stays ⏳ until the tag is confirmed on
the remote** with `git ls-remote` — never ✅ on the assumption that you ran the
block. Deleting and re-pushing a tag follows the same rule, and there's a GitHub
UI fallback (**Releases → Draft a new release → Choose a tag**) if you have no
local clone.

<details>
<summary><b>Remote container specifics</b></summary>

Containers arrive pre-cloned (no `git clone` step), commit the gate state file
with the work instead of gitignoring it, and fall back to GitHub MCP tools when
`gh` is unavailable.

They skip the shell question entirely — Claude runs every git command in the
container's own bash — and the tag/ref-deletion block needs only a clone path,
since everything below `cd` is a plain single-line `git` command with no
shell-specific syntax. So they ask for the clone path *when that block is about
to be presented*, rather than up front.

</details>

---

## Workflow detection: local dev vs. CI

Session start looks for two distinct workflows, because different gates depend
on each and a project can easily have one without the other.

| Workflow | What it is | Which gate uses it |
|---|---|---|
| **Local development** | what you run on your own machine to build and test — `scripts/`, `Makefile`, `package.json` scripts, `gradlew`, `tox.ini`, `CONTRIBUTING.md` | **Gate 2 (Build)** runs this |
| **CI build check** | compiles and tests on push or pull request | validates the PR opened by **Gate 5** |
| **CI release workflow** | builds artifacts and publishes on tag push (`on: push: tags:`) | fired by **Gate 6 (Ship)** |

Whichever is missing is surfaced against the gate it breaks, not reported as a
generic absence. No local dev workflow means Gate 2 has no command to run, so
"verified working" is a guess — and *"CI will catch it"* is explicitly rejected,
because CI runs **after** the commit Gate 2 exists to protect. No release
workflow means Gate 6 has no publish path.

When both exist they're checked for drift: CI should invoke the project's own
scripts (`bash scripts/validate.sh`, `npm test`, `./gradlew test`) rather than
reimplementing the build inline, or the two pass and fail independently until a
release breaks.

---

## Cost discipline

**Automatic — these fire on their own:**

- **Sonnet ceiling** — flags a session running on an expensive model and asks
  before proceeding
- **Effort fit** — recommends `/effort` changes when the task doesn't match the
  level
- **Subagent model delegation** — when spawning subagents, uses the cheapest
  model tier that fits the task (Haiku for lookups, Sonnet for code, Opus/Fable
  only when approved)
- **MCP awareness** — identifies unused MCP servers adding token overhead and
  shows how to disable them
- **Git command presentation** — on local sessions, presents git as a single
  copy-once block per operation rather than several, formatted for your shell
  (PowerShell, Git Bash, Termux, macOS, Linux, WSL) and always starting with the
  right `cd`. Remote container sessions execute directly instead, since a
  presented block would operate on the wrong clone
- **Token impact estimate** — part of the session-end checkpoint whenever the
  session modified a tracked file: what was saved, what was wasted, the biggest
  win next time
- **Handoff offers** — proposed at three observable points: a release sequence
  finished, you opened unrelated work with no release in flight, or the
  conversation was compacted. Also when a usage limit is actually signalled

**On request — ask by name:**

| Ask for it | What you get |
|---|---|
| "handoff summary" | A ~30-line summary — goal, current state, gate status, key files, decisions, next step — to paste into a fresh, cheap session and drop a long history |
| "how did we do?" | A rough token impact estimate: what was saved, what was wasted, biggest win next time |

---

## Audit mode

Say **"audit my project"**, **"scan this codebase"**, or **"security review"** to
run a full scan outside the gate workflow. Outputs findings by severity
(🚨 Critical, ⚠️ High, 📝 Medium, 💡 Low) with file:line, description, and fix
for each.

**"audit my workflows"** or **"review my CI"** runs the same severity-graded
review against `.github/workflows/` specifically — pinning, permissions,
credential hygiene, and drift between CI and the local dev workflow.

**"create a workflow"**, **"set up CI"**, or **"add GitHub Actions"** walks
you through generating one instead: it detects your project's environment,
asks every configuration question in a single turn, and generates a
template you review before anything is written.

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
| "looks good" | That's feedback on the diff, not commit approval — Claude asks explicitly |
| "don't worry about the gates this time" | Gates only leave the workflow as ➖ N/A, for structural reasons |
| "just tag it for me" | Tag pushes are always yours to run — the block is presented, not executed |

---

## What's inside

The skill uses tiered loading to keep token costs down:

| File | Size | Loaded when |
|---|---|---|
| `SKILL.md` | ~39KB | **Every turn** — commit discipline, gate pre-flight, the two tracks, gate state, shortcut detection, cost discipline, and the security layer that must fire unprompted: which patterns to flag on sight, the dependency-audit and attack-surface checklists |
| `GATE_REFERENCE.md` | ~42KB | When a gate runs, and at session start — each gate's checks and pass criteria, plus the session-start procedure |
| `SECURITY_REFERENCE.md` | ~27KB | Gate 3 + audit mode — the security rules in full, each with a bad/good code example |
| `QUALITY_REFERENCE.md` | ~20KB | Gate 3 + audit mode — the quality rules in full, each with a bad/good code example |
| `SHELL_REFERENCE.md` | ~12KB | Before writing any command block — `cd` formats, tag/ref-deletion rationale, Git Bash split invocations, Termux clone flow |
| `WORKFLOW_REFERENCE.md` | ~56KB | When a CI workflow is missing or the user asks for workflow help — GitHub Actions templates for Docker, Windows, Linux, Android, Home Assistant, Python, Node.js, and scripts, dev/pre-release builds, Cosign signing, Dependabot config, audit procedures, best practices, and review checklist |

The split follows one rule: **triggers load every turn, recipes load on demand.**
`SKILL.md` holds what has to fire without being asked. How to actually *run* a
gate lives in `GATE_REFERENCE.md`, loaded when the pre-flight says one is owed.
Security, quality, and shell formatting work the same way.

Security is the clearest case. *Knowing* that a `pickle.loads` on untrusted
input is worth flagging has to be resident — nobody asks for it, and Gate 3 runs
too late if the pattern was written an hour ago. The worked example of how to
fix it does not: that loads with the gate. So the flag-on-sight categories stay
in `SKILL.md` and the rules and examples live in `SECURITY_REFERENCE.md`.

Sizes in this table are verified by `scripts/validate.sh`. `SKILL.md` is paid for
on every request, so an understated figure hides a real per-turn cost.

---

## For maintainers

Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md). Build and check with:

```bash
bash scripts/build-skill.sh   # rebuild dev-skills.skill from source
bash scripts/validate.sh      # version consistency, size table, bundle-vs-source
```

Releases are published by CI: pushing a `v*` tag runs
`.github/workflows/release.yml`, which verifies the tagged commit is on the
default branch, rebuilds `dev-skills.skill` from the tagged source, publishes the
release with notes from `CHANGELOG.md`, and fails if the artifact doesn't end up
attached.

The default-branch check matters because a tag trigger fires for a tag on *any*
commit — without it, tagging an unreviewed branch would publish a real release
from unreviewed code. Both workflows pin `actions/checkout` to a commit SHA
rather than a mutable version tag, check out with `persist-credentials: false`,
and carry concurrency groups and timeouts.

---

## Migrating from the old skills

This single skill replaces all four previous ones:

| Old skill | Now |
|---|---|
| `dev-mode.skill` | No longer needed — this skill covers the same triggers |
| `cost-saver.skill` | Merged into [Cost discipline](#cost-discipline) |
| `vibe-coding-workflow.skill` | Merged into [The six gates](#the-six-gates) |
| `vibe-secure-vibe-coding.skill` | Merged into Gate 3's security rules |

Uninstall the old skills and install `dev-skills.skill`. Everything that worked
before still works — plus commit approval, code quality scanning, Windows/Linux
platform security, and lower token costs via tiered loading.

---

## Version

`v2.18.0` — see [CHANGELOG.md](CHANGELOG.md) for the full history.
