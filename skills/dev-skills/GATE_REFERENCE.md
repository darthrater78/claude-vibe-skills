# Gate & Session Reference

Loaded on demand by the dev-skills skill. This file holds the **execution
detail** for the six gates and the session-start procedure — the recipes, not
the triggers.

The triggers stay in `SKILL.md` and are in effect at all times: commit
discipline, the mandatory pre-flight, the two tracks, the gate state file, the
tracker, and shortcut detection. This file tells you *how to run* a gate once
the pre-flight says one is owed.

**Load this file when:**
- the session starts (session-start procedure, below)
- any gate is about to run, pass, or be marked ➖ N/A
- you are checking gate status and need a gate's pass criteria

Section numbers referenced here (Section 1, 2, 5.7, …) point at `SKILL.md`.

---

## Session start

When the skill loads:

**Self-check:** Verify that `GATE_REFERENCE.md`, `SECURITY_REFERENCE.md`,
`QUALITY_REFERENCE.md`, `SHELL_REFERENCE.md`, and `WORKFLOW_REFERENCE.md`
exist in this skill's base directory (shown when the skill loaded, e.g.
"Base directory for this skill: ..."). If any is missing, warn immediately:

> ⚠️ **Skill self-check failed:** [filename] not found in [base directory].
> The security/quality gate cannot run properly without it.

**Step 0 — Execution environment detection. Run this before anything else; it
changes how git works for the rest of the session.**

The skill's git behavior hinges on one question: **is Claude's working tree the
same clone as the user's terminal?** Resolve it into one of three environments:

| Environment | Signals | Consequences |
|---|---|---|
| **Local** | Claude Code CLI running on the user's own machine; Claude's cwd is the user's own project directory | Present git commands for the user to run (Section 5.8). Ask the shell question (step 2). Gate state file in `.gitignore`. |
| **Remote container** | the system prompt describes a managed, remote, or cloud execution environment; the session was started from the web or mobile app; the repo was cloned fresh into a container path; `gh` is absent | Claude executes git directly after approval. Skip the shell question. Use GitHub MCP tools in place of `gh`. Commit the gate state file to the branch. |
| **Termux** | the user names Termux, or an Android userland path | Clone flow per `SHELL_REFERENCE.md`. Ask the shell question. |

If the signals are ambiguous, ask — do not assume local:

> **Where is this session running?**
> 1. On my machine (Claude Code CLI)
> 2. Remote container (web or mobile session)
> 3. Termux (Android)

**Remote container specifics:**

1. **Nothing needs cloning — the repo is already there.** The container is
   provisioned with a fresh clone at session start. Never present `git clone`,
   and never treat a missing local repo as the user's problem to fix.
2. **The work exists only in the container until it is pushed.** Say this once,
   early:

   > ⚠️ **Remote session:** these edits live in this container. It is reclaimed
   > when the session ends, so anything uncommitted is lost. I'll commit and
   > push from here once you approve.

3. **`gh` is typically not installed.** Verify with `which gh`. If absent, every
   `gh` command in Gates 5 and 6 maps to a GitHub MCP tool (`mcp__github__*`):

   | `gh` command | MCP equivalent |
   |---|---|
   | `gh pr create` | `create_pull_request` |
   | `gh pr list` / `gh pr view` | `list_pull_requests` / `pull_request_read` |
   | `gh pr merge` | `merge_pull_request` |
   | `gh release create` / `gh release view` | `list_releases` / `get_release_by_tag` + release API |
   | `gh run list` / `gh run view` | `actions_list` / `actions_get` / `get_job_logs` |

   If neither `gh` nor GitHub MCP tools are present, say so *before* Gate 5
   rather than discovering it mid-ship.
4. **Skip step 2 (shell detection) at session start — and skip it for the tag
   and ref-deletion blocks too.** Every git command Claude runs here uses the
   container's own bash, so there is nothing to ask about up front. The
   tag-push and ref-deletion carve-out (Section 5.8) changes that at exactly
   one moment: a remote session that reaches Gate 6, or that needs to delete a
   branch or tag, *always* hands the user a block to run on their own
   machine — but that block needs a real clone path, not a shell choice.
   Everything in it below `cd` is a plain single-line `git` command (`git
   checkout`, `git pull`, `git tag`, `git push`) with no heredocs, no
   multi-line strings, no shell-specific syntax at all — it runs unmodified in
   every shell `SHELL_REFERENCE.md` lists. The only line that varies is `cd`,
   and a quoted path (`cd "<clone-path>"`) parses the same way regardless of
   which of the seven the user pastes it into.

   So ask only for the clone path, **when the block is about to be
   presented**, not at session start — a session that never releases and never
   deletes a ref never needs it:

   > Before I hand you this block — **what's the path to your local clone**,
   > so it starts in the right directory?

   Store it for the rest of the session. Presenting `cd <your-repo-path>` as a
   placeholder is a defect, not a neutral default: it is the one line the user
   cannot copy as given, in the one block they must run by hand.
5. **Step 3 (sync offer) is usually unnecessary** — the clone is fresh as of
   session start. Still run `git fetch origin` before Gate 5 in case the branch
   moved during a long session.
6. **Gate state file goes on the working branch,** not in `.gitignore`
   (Section 2).
7. **Executing git here does not extend to tag pushes.** Container credentials
   are commonly denied (`403`) on `refs/tags/*`, and that is exactly the push
   that fires the release workflow. Present the tag block to the user even
   though everything else runs here — Section 5.8, "Tag pushes and ref
   deletions are the exceptions."

Report the detected environment in the session banner.

**Git repo detection — run at session start.** Check if the current working
directory is inside a git repository (`git rev-parse --is-inside-work-tree`).
If yes:

1. **Detect and store the repo URL.** Run `git remote -v` to capture the origin
   URL. Store it for the session — this URL is used in clone commands (Termux),
   `git remote add` recovery, release URLs, and PR links. Never assume or
   hardcode a repo URL — always derive from `git remote -v`.

   If no remote is configured:

   > ⚠️ **No remote configured.** This repo has no `origin` remote set.
   > What is the GitHub URL for this project? (e.g. `https://github.com/owner/repo`)

   Store the answer, and include `git remote add origin <url>` in the first
   command block presented to the user.

2. **Shell environment detection.** *Local and Termux sessions ask this now.
   Remote containers defer it until a tag block is due (step 0, item 4) — they
   do need it eventually, just not yet.* Ask the user which shell they work in —
   this determines how all git commands are formatted for the rest of the
   session:

   > **Which shell will you be running these commands in?**
   > 1. Windows PowerShell
   > 2. Linux PowerShell (pwsh)
   > 3. Git Bash (Windows)
   > 4. Termux (Android)
   > 5. macOS Terminal (zsh/bash)
   > 6. Linux Terminal (bash/zsh)
   > 7. WSL (Windows Subsystem for Linux)

   Store the answer for the rest of the session — don't ask again.

3. **Offer to sync with origin.** The user may be working with outdated files.
   Present the option before any work begins, formatted for the user's detected
   shell (Section 5.8):

   > 📡 **Git repo detected:** `<repo-name>` on branch `<current-branch>`
   > Want to sync with origin before we start? This ensures we're working
   > with the latest files.
   >
   > 1. **Yes — sync now** (fetch + pull from origin)
   > 2. **No — work with what's here**

   If the user chooses to sync, present the fetch/pull commands formatted for
   their shell. Report any conflicts or divergence.

4. **Check the branch.** If the user is on `main` or `master`, flag it:

   > ⚠️ **You're on `<branch>`.** This skill enforces branch-based development
   > — all work happens on feature/fix branches, then merges to the default
   > branch via PR. Want to create a working branch now?

   If yes, ask for a branch name or suggest one based on the task. Never
   proceed with implementation work directly on the default branch.

5. **Report the repo state** in the session start banner (see below).

6. **Workflow detection — two workflows, and both are needed.** A project has a
   *local development workflow* and a *CI workflow*. They are not substitutes
   for one another, and different gates depend on each. Detect both, and report
   both in the banner.

   **The local development workflow** — what a developer runs on their own
   machine to build, test, and lint before anything is pushed. Look for:
   `scripts/`, `Makefile` / `justfile` / `Taskfile.yml`, `package.json`
   `"scripts"`, `tox.ini`, `noxfile.py`, `gradlew`, `Cargo.toml`, `.csproj` /
   `.sln`, a `docker compose` dev stack, or build instructions in
   `CONTRIBUTING.md` / `README.md`.

   **Gate 2 (BUILD) runs this one.** It is the only thing that turns "the code
   should work" into "the code was run." A project with no local dev workflow
   has nothing for Gate 2 to execute.

   **The CI workflow** — what runs on the server. Two distinct kinds, and a
   project can easily have one without the other:
   - a **build check** — triggers on push or pull request, compiles and tests
   - a **release workflow** — triggers on tag push (`on: push: tags:`), builds
     artifacts and publishes the release

   **Gate 5's PR is validated by the build check; Gate 6 (SHIP) fires the
   release workflow.**

   Then flag whichever is missing. Each gap breaks a different gate, so name the
   gate rather than reporting a generic absence:

   | Missing | What it breaks | Surface |
   |---|---|---|
   | Local dev workflow | Gate 2 has no command to run — "verified working" becomes a guess | 💡 **No local build/test workflow found.** Gate 2 can only confirm this builds if there's something to run. How do you build and test this locally? |
   | CI build check | PRs merge without ever being compiled | 💡 **No CI build check detected.** PRs are not compiled before merge. A build check catches compile errors before they land on the default branch. Want me to create one? |
   | CI release workflow (and Gate 2 is not ➖ N/A) | Gate 6 has no publish path; release artifacts get built by hand | 💡 **No CI release workflow detected.** A release workflow would let CI build and publish artifacts when you push a version tag — no local release build needed. Want me to create `.github/workflows/release.yml`? |

   **When both exist, check that they agree.** CI should invoke the project's
   own scripts — `bash scripts/validate.sh`, `npm test`, `./gradlew test` — not
   reimplement them inline. A CI job carrying its own hand-rolled copy of the
   build is testing something the developer never runs locally, and the two
   drift apart silently until a release breaks. Flag the divergence:

   > ⚠️ **CI and local dev have drifted.** `validate.yml` runs its checks
   > inline, but `scripts/validate.sh` is what a developer runs. They can pass
   > and fail independently. CI should call the script.

   If the user asks for a workflow to be created, or accepts the suggestion,
   **load `WORKFLOW_REFERENCE.md`** from this skill's base directory. It holds
   environment-detection rules, template workflows for Docker, Windows,
   Android, Linux, Home Assistant, Python, Node.js, and script projects,
   dev/pre-release builds, and the procedure for asking all configuration
   questions in a single turn. Follow its workflow selection procedure
   rather than asking questions piecemeal.

   The generated workflow must be adapted from the project's actual build
   tooling. A workflow that does not run the project's real build is worse
   than none, because it goes green without proving anything.

7. **Unfinished release check — did the last release actually ship?** Gate 6 has
   four parts (merge, tag, publish, verify) and a session can die between any two
   of them: a container reclaimed, a usage limit, or a tag push denied `403`
   (Section 5.8). When that happens the work is stranded on the default branch
   and **nothing in a later session goes looking for it** — the next session
   starts with all gates ⬜ pending *for the version it is about to build*, and
   never asks about the one before.

   Section 8's session-end check only covers the current version, and only if the
   session gets a chance to wind down. A container that is simply reclaimed never
   winds down. So the check belongs here, at start, where it always runs.

   Compare released versions against tags on the remote:

   ```
   git ls-remote --tags origin | sed 's#.*refs/tags/##' | grep -v '\^{}' | sort -V
   git log --oneline -- VERSION        # or the project's version file
   ```

   Every version with a changelog entry and no tag is an unfinished Gate 6:

   > ⚠️ **Unfinished release detected.** v1.2.2 and v1.2.3 are in `CHANGELOG.md`
   > and on the default branch, but neither is tagged on the remote — Gate 6
   > never completed for them, so no release was published.
   >
   > Want me to finish them (tag their merge commits, let CI publish) before we
   > start new work?

   Report it in the banner and let the user decide. Do not silently continue: a
   gap here means the *next* release is about to be stacked on an unpublished
   one, and Gate 1 will hard-block on it anyway.

**Write the gate state file.** Create `.claude/dev-skills-gates.md` with all six
gates ⬜ pending (format in Section 2). On local sessions add it to `.gitignore`;
on remote containers it is committed with the work. This file — not the
conversation — is the source of truth for gate state for the rest of the session.

Then show the gate tracker:

```
Dev Skills v2.18.0 active.

Repo: <repo-name> | Branch: <current-branch> | Remote: <origin url or "NOT SET">
Env: <local / remote container / Termux> | Git: <presented for you to run / run by Claude here>
Shell: <detected shell, or "container bash"> | Last sync: <just now / not synced>
CI: release <✅ workflow name / ❌ none> | build check <✅ workflow name / ❌ none>
Local dev: <✅ build/test command / ❌ not found>
Releases: <✅ all versions tagged / ⚠️ N unfinished: vX.Y.Z, ...>

🔢 VERSION    ⬜
🔨 BUILD      ⬜
🔒 SECURITY   ⬜
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜

Commits require explicit approval. Security scan runs after every build.
All work on branches — merge to default branch via PR only.
```

**Important:** The version shown must match the `version` field in `SKILL.md`'s
frontmatter. If they differ, the skill was not repackaged after a version bump —
surface this to the user.

**Release notes for this version:**
https://github.com/darthrater78/claude-vibe-skills/releases/tag/v2.18.0
**Updates:** Check for new versions at
https://github.com/darthrater78/claude-vibe-skills/releases

**MCP check — run at session start, every time.** Scan your context for active
MCP tool prefixes (`mcp__<server>__`). Report what's connected:

```
MCP servers active: [list names derived from tool prefixes]
To disable for this session: /mcp → toggle off any you don't need
```

Rules for the MCP check:
- **Only name servers whose `mcp__<server>__` tool prefixes are literally in your
  context.** Never infer or guess.
- Distinguish **active** (full tool definitions loaded — expensive, thousands of
  tokens per request) from **deferred** (name-only, schemas loaded on demand —
  cheap). Report deferred as a count only: "N deferred (low overhead)".
- If active servers look irrelevant to the work ahead, say so: "Consider
  disabling [name] — not needed for this task. Run `/mcp` to toggle."
- `/mcp` is the in-session command. It toggles servers on/off without leaving
  the session. This is the primary recommendation for disabling during a session.
- For permanent removal, see Section 5.5.

Then: "What are we building?"

---

---

## The six gates — execution detail

The pre-flight, the two tracks, the gate state file, and the re-derivation
table live in `SKILL.md` Section 2. What follows is how each gate is actually
run and what makes it pass.

### Gate 1 — Version 🔢

No build starts until versioning is resolved.

**Check ALL of these:**
1. Find every version-carrying file in the project: `package.json`, `pyproject.toml`,
   `Cargo.toml`, `VERSION`, `setup.cfg`, `build.gradle`, `pom.xml`, manifest files,
   `Info.plist`, `AndroidManifest.xml`, `.csproj`, `AssemblyInfo.cs`, etc.
2. **Search source code for hardcoded version strings.** Grep the project for the
   current version number (e.g. `1.0.0`, `v1.0.0`). Check XAML, HTML, UI templates,
   "About" dialogs, splash screens, window titles, headers, footers, constants, and
   config files. Every instance must be updated — not just the manifest files.
   A missed version string in the app's UI is a gate failure.
3. Every version reference must show the same version and it must be bumped from
   the previous release.
4. Version must follow semver (MAJOR.MINOR.PATCH).
5. **Repository link is mandatory.** Every project that has an app manifest
   (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.) must include the
   `repository` / `homepage` / `[project.urls]` field pointing to the GitHub repo
   it belongs to. If missing, add it before passing this gate.
6. **Release notes link is mandatory.** Every app that displays a repository link
   (in an "About" dialog, settings screen, footer, help menu, etc.) must also
   include a link to the current version's release notes. Use the pattern
   `https://github.com/<owner>/<repo>/releases/tag/v<VERSION>` — the version in
   the URL must match the version being built. If the app already shows a repo
   link but has no release notes link, add one before passing this gate.

7. **Previous version tags must exist.** Run `git ls-remote --tags origin` —
   **not `git tag -l`**, which reads local tags and returns empty in any fresh
   clone (SKILL.md Section 2). Compare the tags against the versions in
   `CHANGELOG.md` / the version history.

   **A missing tag for the immediately preceding version is a hard block.** It
   does not mean "someone forgot to tag" — it means the last release never
   finished Gate 6, so the default branch carries a version that was never
   published. Bumping on top of it buries the gap one version deeper, which is
   exactly how two and three versions go missing in a row:

   > 🚫 **VERSION GATE BLOCKED — the previous release never shipped.**
   > v1.2.2 is in the changelog and on the default branch, but has no tag on
   > the remote. Gate 6 did not complete for it — most often a tag push that
   > came back `403` (Section 5.8) or a session that ended between merge and
   > tag.
   >
   > Finish it before bumping: tag its merge commit and let the release
   > publish, or state explicitly that v1.2.2 is being abandoned and why.

   Retroactively tagging is usually a one-liner — find the merge commit that
   bumped `VERSION` to that release (`git log --oneline -- VERSION`) and tag it.
   That block goes to the user like any tag push (Section 5.8).

   **Older gaps are advisory,** not blocking: note them, fix them if the merge
   commits are identifiable, flag them otherwise. The distinction is that the
   *previous* version is the one this release is built on top of.

If any check fails:

> 🚫 **VERSION GATE BLOCKED**
> Issues found:
> - [specific issue, e.g. "package.json version is 1.0.0 but VERSION file says 1.0.1"]
> - [e.g. "MainWindow.xaml still shows v1.0.0 in the title bar"]
> - [e.g. "package.json missing repository field"]
> - [e.g. "About dialog has repo link but no release notes link"]
> - [e.g. "v1.2.2 has no git tag — needs retroactive tagging"]
>
> Current version: [version or "none found"]
> What version should this build be? (patch / minor / major)

Update ALL version files, add missing repo links and release notes links before marking passed.

### Gate 2 — Build 🔨

**This gate runs the local development workflow** detected at session start
(session start, step 6) — the project's own build and test commands, not CI.
CI runs later and on a different machine; it cannot tell you now whether the
code you just wrote works. Run the project's build command only after Gate 1
is ✅. If the build fails, fix and rebuild — do not advance.

If no local dev workflow was found, this gate has nothing to execute. That is
not ➖ N/A — N/A is for projects with no build system at all, not for projects
whose build you cannot find. Ask:

> 🚫 **BUILD GATE BLOCKED — no local build/test command found.**
> This project has a build system but I can't tell how it's run locally.
> What do you run to build and test this on your own machine?

Never substitute "CI will catch it" for running the build. CI runs after the
commit; this gate exists to stop a broken commit from being made.

**If the build or validation script stalls instead of finishing**, and the
shell is Git Bash, read `SHELL_REFERENCE.md` — "Git Bash stalls on spawn-heavy
scripts". A stall there is a fork-emulation limit, not a script defect and not
a gate failure; the script is run in split invocations and the gate passes
normally. A stalled run is never a pass on its own, and it is never a reason
to hand the check to CI.

**A test build is mandatory before any commit.** When building an app, create a
test/dev version and verify it runs correctly before staging or committing anything.
This means:
1. Build the project (dev/test mode where applicable)
2. Launch or preview the app — confirm it starts, the golden path works, and
   no regressions are visible
3. Only after the test build is verified working does this gate pass

If the app cannot be tested locally (e.g. requires external infrastructure),
say so explicitly rather than skipping — the user decides whether to proceed.

**Projects with CI release workflows.** If the project has a GitHub Actions
workflow that builds release artifacts on tag push (check
`.github/workflows/` for `on: push: tags:`), the local build gate covers
only the **debug/test build**. The release artifact is built by CI during
Gate 6 — do not build it locally. Gate 2 passes when the debug build
compiles and the app is verified working.

> ✅ **BUILD GATE PASSED** — debug build verified working (release build deferred to CI)

**Projects with no build step** (config repos, skill repos, documentation-only
repos, pure script collections): mark this gate ➖ N/A with an explanation:

> ➖ **BUILD GATE N/A** — this is a [skill/config/docs] repo with no build system.

Do not silently skip — always show the N/A status on the tracker.

> ✅ **BUILD GATE PASSED** — test build verified working
> Output: [artifact path]

### Gate 3 — Security & Quality 🔒

**Mandatory after every build.** Two steps, both must pass: security scan and
quality review.

**Before scanning, load both reference files from this skill's base directory**
(shown when the skill loaded, e.g. "Base directory for this skill: ..."):
1. Read `SECURITY_REFERENCE.md` in the skill's base directory — bad/good code
   examples for every security pattern.
2. Read `QUALITY_REFERENCE.md` in the skill's base directory — bad/good code
   examples for structure and performance anti-patterns.
Use these examples to pattern-match against the code being reviewed.

#### Step 1 — Security scan

Run a full scan of all source files. Check for every pattern category in
Sections 4.1–4.3 and the full rule checklists in `SECURITY_REFERENCE.md` (loaded
above). Also run the project's native audit tool (`npm audit`,
`pip audit`, `cargo audit`, etc.) if available.

**Hard stops (must fix before proceeding):**
- 🚨 Critical: hardcoded secrets, SQL injection, `shell=True` with user input,
  disabled TLS, `pickle` on untrusted data, RCE vectors
- ⚠️ High: path traversal, missing auth, `debug=True` in prod, weak crypto for
  passwords, `random` for tokens, no input validation on endpoints

**Show and let user decide:**
- 📝 Medium: bare `except`, no type hints, mutable defaults, `assert` for validation,
  logging sensitive data, unpinned deps
- 💡 Low: missing `encoding=` on `open()`, string paths, missing static analysis in CI

Security step passes at zero Critical and zero High:

> ✅ **Security scan passed** — 0 Critical, 0 High
> Medium: N (shown above, user accepted) | Low: N

#### Step 2 — Quality review

Scan the changed code for every quality pattern in `QUALITY_REFERENCE.md` (loaded
above) and the checklist below:

**Structure issues (flag and fix):**
- Deep nesting (>3 levels) — flatten with early returns
- God functions (>~40 lines or multiple responsibilities) — split
- Circular dependencies — restructure
- Hidden side effects in getters or utility functions — rename or separate
- Copy-pasted logic that should be shared — extract

**Performance issues (flag and fix):**
- N+1 queries — batch with IN/ANY or joins
- Wrong data structures (lists for lookups instead of sets/dicts)
- String concatenation in loops — use join/builders
- Recomputation in loops (regex, config, API calls) — compute once
- Allocations in hot paths — move constants to module level
- Loading everything when a subset is needed — SELECT specific columns, paginate
- Blocking I/O on async event loops — use async alternatives
- Unbounded caches — use lru_cache with maxsize
- Missing database indexes on queried columns
- Event listeners never cleaned up — add teardown

**Container / build issues (flag and fix):**
- Dockerfile hardcodes package names instead of installing from dependency file — switch to `pip install -r requirements.txt` / `npm ci`
- New import added but package missing from dependency file — add it
- Dockerfile and dependency file list different packages — reconcile to one source of truth

Report quality findings separately from security:

> **Quality review — changed code:**
> ⚠️ `app.py:45` — N+1 query inside loop (fetches orders per user)
>    Fix: batch with `WHERE user_id = ANY(%s)`
> ⚠️ `utils.py:120` — function is 80 lines with 5 responsibilities
>    Fix: split into validate_input, transform_data, save_result
> ✅ No deep nesting issues
> ✅ No circular dependencies

Quality issues don't hard-block the gate (they're not security vulnerabilities),
but they must be surfaced and the user must acknowledge them. Fix what's
reasonable within the current scope — flag the rest as known technical debt.

#### Gate 3 combined output

Both steps must complete before the gate passes:

> ✅ **SECURITY & QUALITY GATE PASSED**
> Security: 0 Critical, 0 High | Medium: N | Low: N
> Quality: N structure issues, N performance issues (shown above, user accepted)

If the user says "skip security" or "we can do security later":

> 🚫 **SECURITY GATE BLOCKED**
> Security scan is mandatory after every build. Running now.

Then run it. Do not ask again.

### Gate 4 — Docs 📄

After security passes, check:
1. **Version history / changelog** — the README or CHANGELOG must have an entry for
   this version with the date and a summary of changes. Mandatory for every release.
2. **New or changed features** — if the session added, removed, or changed any
   user-facing behavior (new flags, commands, changed defaults, removed features),
   the README usage/feature docs must reflect it.
3. **Removed features** — scan the README for references to anything removed in this
   session. Stale descriptions of removed features are a hard stop.
4. **Architecture / dependency docs** — if the project documents external calls,
   timeout tables, architecture, or dependencies, verify they still match the code.
5. **Internal consistency** — if the README describes how the project works (gate
   names, workflows, install steps, feature summaries, diagrams), cross-check every
   description against the actual source of truth (SKILL.md, code, config). Renamed
   concepts, restructured workflows, and changed terminology must be reflected
   everywhere — not just in the changelog. Read the full README and flag any
   description that no longer matches.

Show what was checked:

> ✅ **DOCS GATE PASSED**
> - Version history: v1.2.3 entry added with date and changes
> - New features: [list any docs updated]
> - Removed features: [list any stale refs cleaned up, or "none"]
> - Architecture/tables: [updated / no changes needed]
> - Internal consistency: [README descriptions match source of truth, or list fixes]

If documentation is missing or stale:

> 🚫 **DOCS GATE BLOCKED**
> The following documentation issues must be resolved:
> - [specific issue, e.g. "README still references feature X which was removed"]
> - [specific issue, e.g. "README calls Gate 6 'Push' but it was renamed to 'Ship'"]
> - [specific issue, e.g. "No version history entry for v1.2.3"]
>
> Fixing now...

Fix any issues found. Rebuild if doc fixes affected source files.

### Gate 5 — Release 📦

This gate prepares the release: branch, commit, PR, and release notes draft.
Execution (merge, tag, publish) happens in Gate 6.

**Steps:**
1. Create a feature branch if not on one (`release/vX.Y.Z`, `feature/desc`, `fix/desc`)
2. **Sync with origin before committing.** Run `git fetch origin` and compare
   the local branch with its remote counterpart. If the remote is ahead, pull
   before staging. Present the sync commands formatted for the user's shell
   (Section 5.8). This prevents committing on top of stale history, which causes
   merge conflicts and can clobber others' work.

   > 📡 **Pre-commit sync:** Fetching latest from origin...
   > [status: up to date / N commits behind / diverged]

   If diverged, resolve before proceeding. Do not skip this step.
3. **Get commit approval** (per `SKILL.md` Section 1) — show what's staged, get explicit yes
4. **Verify remote is configured.** Run `git remote -v`. If no origin is set,
   include `git remote add origin <url>` (using the URL stored at session start)
   in the command block before any push commands. This prevents the "default repo
   has not been set" error.
5. **Present commands per Section 5.8** — format the commit, push, and PR creation
   commands for the user's shell environment. The user runs them manually or asks
   Claude to execute directly.
6. After the branch is pushed and PR created, draft release notes and show the
   PR + notes to the user:

   > 📝 **PR created — review before shipping:**
   >
   > **v1.2.3**
   > - [change 1 from this session]
   > - [change 2 from this session]
   >
   > PR: [url]
   >
   > Do these accurately describe what's in this build? Reply "yes" to ship,
   > or tell me what to change.

7. Wait for explicit approval of the PR content and release notes

**Never commit directly to main/master.** All work happens on feature/fix/release
branches and merges via PR. If the session is on the default branch when Gate 5
is reached, create a branch first.

> ✅ **RELEASE GATE PASSED** — PR [url] ready, release notes approved
> Pending: merge, tag, and publish (Gate 6)

### Gate 6 — Ship 🚀

Merge, tag, and publish. All three happen here, not in Gate 5.

**Pre-ship summary — explicit confirmation required.** "Yeah" or "ok" is not
enough — the user must say "ship", "yes push", or "go ahead."

> **Ready to ship:**
> Branch: `release/v1.2.3` → `main` | PR: [url]
> Tag: `v1.2.3` | Artifact: [path/size, or "none"]
> Type **"ship"** to confirm, or tell me what to adjust.

**CI release detection — check before manual steps.** Look for a release
workflow in `.github/workflows/` that triggers on tag push (`on: push: tags:`)
and creates a GitHub release. If found, follow the **CI-driven path** below.
If not, follow the **manual path**.

#### CI-driven path

When a CI release workflow exists.

**The git flow is identical on every platform.** Linux, Windows, and Android
differ in what CI *builds*; they do not differ in the sequence of git operations
that gets there:

```
merge the PR → checkout the default branch → pull
             → tag → push the tag → CI builds and publishes → verify
```

Do not invent a platform-specific git flow. If a project's release seems to need
something other than "push a tag, let CI publish," that is a CI design problem
to fix, not a git flow to work around by hand.

**What actually differs per platform:**

| | Linux | Windows | Android |
|---|---|---|---|
| Runner | `ubuntu-latest` | `windows-latest` | `ubuntu-latest` |
| Release build | `make release`, `cargo build --release`, `go build -ldflags="-s -w"`, `pyinstaller` | `dotnet publish -c Release`, `msbuild /p:Configuration=Release`, `pyinstaller` | `./gradlew assembleRelease` (APK) or `bundleRelease` (AAB) |
| Artifact | tarball, `.deb` / `.rpm`, AppImage, bare binary | `.exe`, `.msi`, `.zip` | `.apk` / `.aab` |
| Signing secrets | GPG detached signature, optional (`GPG_PRIVATE_KEY`, `GPG_PASSPHRASE`) | Authenticode (`SIGNING_CERT_BASE64`, `CERT_PASSWORD`) | release keystore (`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`, `KEY_PASSWORD`) |
| Job shell | `bash` (default) | set `shell: bash` explicitly, or write real PowerShell — never assume | `bash` |
| Ship failure | artifact missing, or a debug/unstripped build shipped as the release | unsigned, or signed with a self-signed test certificate | debug-signed, unsigned, or `debug` in the filename |

Two cross-platform traps worth naming, because each produces a release that
looks fine and is not:

- **Line endings.** Without `.gitattributes` normalizing them, a Windows runner
  can check out CRLF shell scripts that then die with `bad interpreter`. Fix it
  in the repo, not with a `dos2unix` step in the job.
- **Case sensitivity.** Linux runners are case-sensitive; Windows runners are
  not. A wrong-case path works on the developer's Windows machine and fails only
  in CI, and only on the Linux job.

**Steps:**

1. **Verify secrets are configured** for the target platform (table above).
   Check with `gh secret list`, or GitHub MCP where `gh` is absent. If secrets
   are missing:

   > 🚫 **SHIP GATE BLOCKED — CI signing secrets not configured.**
   > The release workflow needs these repository secrets: [list missing].
   > Add them at: `https://github.com/<owner>/<repo>/settings/secrets/actions`

   A workflow that builds unsigned artifacts because a secret is absent usually
   still goes green. Check the secrets, not just the run.

2. **Merge the PR** (per Section 5.8 — Claude executes this in a remote
   container, presents it locally):
   ```
   gh pr merge <number> --merge --delete-branch
   git checkout main && git pull origin main
   ```

3. **Tag and push — the user runs this block.** Tag pushes are denied (`403`)
   to Claude's credentials far more often than they succeed, and this is the
   push that starts the release build (Section 5.8, "Tag pushes and ref
   deletions are the exceptions"). Present it, in one block, with the sync in
   front so the tag lands on the merged commit:

   **If the clone path is not known yet — every remote session, by design
   (step 0, item 4) — ask for it before writing this block.** A `cd` the user
   has to edit is a broken first line.

   ```
   cd "<clone-path>"
   git checkout main
   git pull origin main
   git tag v1.2.3
   git push origin v1.2.3
   ```

   > 📌 **Pushing that tag is what starts the release build.** Run the block
   > above and tell me when it's done — I'll watch the workflow from here.

   No local clone (web or mobile session)? Offer the UI instead: **Releases →
   Draft a new release → Choose a tag → create it on the default branch.** Same
   ref, same trigger.

   🚀 SHIP stays ⏳ until the tag is confirmed on the remote. Confirm it
   yourself — reading refs is not a write and is not restricted:
   ```
   git ls-remote --tags origin v1.2.3
   ```

   **If the push instead reports `error: src refspec v1.2.3 does not match
   any`, that is not a `403` and not a permissions problem.** It means `git tag
   v1.2.3` never actually ran — or ran in a different directory than the one
   this block is pushing from — so there is no local tag for `push` to send.
   Two sessions have misread this message as the credential denial above and
   gone looking for a permissions fix; the fix here is simpler: from inside
   `<clone-path>`, re-run `git tag v1.2.3`, then push again.

4. **Wait for CI to complete.** Monitor with:
   ```
   gh run list --limit 3
   gh run watch <run-id>
   ```
   Or `actions_list` / `actions_get` / `get_job_logs` via GitHub MCP.

5. **Add release notes.** CI typically creates the release with the artifact
   attached but no notes. Add them:
   ```
   gh release edit v1.2.3 --notes "..."
   ```
   Or if the user prefers, edit via the GitHub UI.

6. **Post-ship verification (mandatory).** Same as manual path — all four
   checks must pass:
   - **Tag on remote:** `git ls-remote --tags origin v1.2.3`
   - **Release exists:** `gh release view v1.2.3`
   - **PR merged:** state is "merged"
   - **Assets match:** CI-built artifact attached with the right name and a
     plausible size, checked against the platform row above. **Linux:** the
     release build, not a debug or unstripped one. **Windows:** signed with a
     real certificate, not unsigned or self-signed. **Android:** the filename
     contains the version and does NOT contain `debug`.

   If CI failed:
   > 🚫 **SHIP GATE BLOCKED — CI release workflow failed.**
   > Check logs: `gh run view <run-id> --log-failed`
   > Fix the issue, then delete and re-push the tag. **Deleting and re-pushing
   > a tag are both ref writes — they go to the user in one block, same as the
   > original push:**
   > ```
   > cd "<clone-path>"
   > git tag -d v1.2.3
   > git push origin :refs/tags/v1.2.3
   > # after the fix is merged to the default branch:
   > git checkout main && git pull origin main
   > git tag v1.2.3
   > git push origin v1.2.3
   > ```

> ✅ **SHIP GATE PASSED** — PR merged, tag pushed, CI release published
> Verified: tag ✅ | release ✅ | PR merged ✅ | CI assets ✅

#### Manual path (no CI release workflow)

**Artifact detection — actively scan, never assume "none".** Check:
1. **Build tooling:** PyInstaller specs, Makefile targets, `setup.py` entry_points,
   `cargo build --release`, `go build`, `dotnet publish`, webpack/vite configs,
   `.skill` source dirs, `scripts/`, `build/`
2. **README:** download links, install instructions referencing binaries/packages
3. **Prior releases:** `gh release view <previous-tag>` — if prior releases had
   assets, this one should too

If any indicator exists: rebuild from committed source, verify version/dates
match, include in release. A release missing expected artifacts is a ship failure.
README download links (e.g. `../../releases/latest/download/file.ext`) that point
to missing assets are also a ship failure.

**Android APK requirement.** When the project is an Android app (`build.gradle`,
`AndroidManifest.xml`, or Gradle with Android plugins):
1. Build release APK: `./gradlew assembleRelease` — never a debug build
2. **Verify APK signing — debug signature is a ship failure.** Run:
   ```
   apksigner verify --print-certs <apk-file>
   ```
   or if `apksigner` is unavailable:
   ```
   keytool -printcert -jarfile <apk-file>
   ```
   Check the output:
   - 🚨 **Ship failure** if the signer CN contains `Android Debug`, `debug`, or
     the SHA-256 matches the well-known debug keystore fingerprint
   - 🚨 **Ship failure** if the APK is unsigned (no signature block at all)
   - ✅ Pass only if signed with a release keystore whose CN matches the project's
     expected identity (e.g. the organization or developer name)

   The default debug keystore (`~/.android/debug.keystore`, password `android`,
   alias `androiddebugkey`) is generated automatically by Android tooling. Any APK
   signed with it can be re-signed by anyone — it provides zero authenticity.
   **Never ship a debug-signed APK.**
3. Name it `<app-name>-v<VERSION>.apk` — rename Gradle's generic output if needed.
   **"debug" in the filename = wrong variant = ship failure.**
4. Attach as release asset — an Android release without an APK is a ship failure
5. Verify the APK appears in release assets with correct name and reasonable size

**Platform expectations.** The Linux / Windows / Android table in the CI-driven
path above applies here too — it describes what a correct release artifact looks
like, not how CI happens to produce it. Check the artifact against its platform
row before publishing.

**Execution — present commands per Section 5.8.** The tag push goes to the user
even when Claude is executing the rest (Section 5.8, "Tag pushes and ref
deletions are the exceptions"), so this splits into two blocks:

Claude runs (or presents, on a local session):
```
gh pr merge <number> --merge --delete-branch
git checkout main && git pull origin main
```

The user runs — stop here until they confirm the tag is on the remote:
```
cd "<clone-path>"
git checkout main
git pull origin main
git tag v1.2.3
git push origin v1.2.3
```

If this reports `error: src refspec v1.2.3 does not match any` instead of a
`403`, the tag was never created locally — see the troubleshooting note under
the CI-driven path's tag step above. Re-run `git tag v1.2.3` from inside
`<clone-path>` and push again.

Then, once `git ls-remote --tags origin v1.2.3` shows the tag:
```
gh release create v1.2.3 <artifacts> --title "v1.2.3" --notes "..."
```

**Post-ship verification (mandatory):** The gate does not pass without all four:
1. **Tag on remote:** `git ls-remote --tags origin v1.2.3` returns the tag
2. **Release exists:** visible via `gh release view v1.2.3`
3. **PR merged:** state is "merged", not just "closed"
4. **Assets match:** expected artifacts are attached per detection above

> ✅ **SHIP GATE PASSED** — PR merged, tag v1.2.3 pushed, release published
> Verified: tag ✅ | release ✅ | PR merged ✅ | assets ✅

If any check fails, fix and re-verify — do not pass with failures outstanding.

**Post-merge cleanup.** After the PR is merged and verified, clean up branches:
1. Delete the local feature branch: `git branch -d <branch-name>`
2. Prune stale remote-tracking refs: `git remote prune origin`
3. Present cleanup commands formatted for the user's shell (Section 5.8)

This prevents stale branches from accumulating. `--delete-branch` on `gh pr merge`
handles the remote branch; these steps handle the local side.

#### Updating an existing release (`--clobber`)

If an artifact is uploaded to an existing release, the notes are now stale:

> 🚫 **SHIP GATE BLOCKED — notes are stale**
> Update with `gh release edit <tag> --notes "..."` or bump to vN+1.

Pass only after the notes are updated or the user explicitly acknowledges why not.

#### No release mechanism

> 🚫 **SHIP GATE BLOCKED**
> Builds that aren't released are invisible. Where should this be published?

If genuinely no mechanism exists, the user must confirm explicitly.
Prior gates incomplete → block and surface the missing gate.

---

