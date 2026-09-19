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
`QUALITY_REFERENCE.md`, `SHELL_REFERENCE.md`, `WORKFLOW_REFERENCE.md`,
`SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`, `SECURITY_ANDROID.md`, and
`QUALITY_ANDROID.md` exist in this skill's base directory (shown when the
skill loaded, e.g. "Base directory for this skill: ..."). If any is missing,
warn immediately:

> ⚠️ **Skill self-check failed:** [filename] not found in [base directory].
> The security/quality gate cannot run properly without it.

**Version check — run every time the skill loads, before anything else.**
Running an outdated copy means gates in this session can be missing fixes,
tightened checks, or corrected mistakes that already shipped upstream — this
is not optional and does not wait for the user to ask.

1. **Installed version** — the `version:` field in this skill's own
   `SKILL.md` frontmatter (e.g. `2.19.0`).
2. **Latest published version** — read the upstream remote directly, the same
   way every other ref check in this skill works (never a cached local
   clone, never a number from memory):

   ```
   git ls-remote --tags https://github.com/darthrater78/claude-vibe-skills.git \
     | sed 's#.*refs/tags/##' | grep -v '\^{}' | sort -V | tail -1
   ```

   If this can't reach the network (offline, sandboxed, egress blocked), say
   so once in the banner ("⚠️ version check skipped — no network access") and
   continue. A session isn't blocked entirely by a check it has no way to make.
3. **Compare** (strip the leading `v`, semver order).
   - **Current:** fold a single confirmed line into the banner — no separate
     callout needed.
   - **Behind:** this cannot be quiet, easy to skim past, or foldable into
     routine banner text. An outdated copy means every gate this session
     runs may be silently missing a fix, a tightened check, or a corrected
     mistake — treat it with the same severity as a failed security gate,
     not an FYI:

     - **It is the first thing in the first message** — before a greeting,
       before acknowledging what the user asked, before the session banner.
       Nothing goes above it.
     - **Bracket it with a full-width warning line** so it cannot be
       mistaken for routine output, and repeat the version numbers at both
       ends so they're visible even if the middle gets scrolled past:

       > 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
       > **STOP — dev-skills is out of date: running v2.17.0, latest is v2.19.0.**
       >
       > Gates run in this session may be missing fixes released since
       > v2.17.0. This is not a routine notice — proceeding means every gate
       > below runs on code this skill's own maintainers have already
       > patched.
       >
       > Release notes for what changed since v2.17.0:
       > https://github.com/darthrater78/claude-vibe-skills/releases
       >
       > **To update:** download the new `dev-skills.skill` from
       > https://github.com/darthrater78/claude-vibe-skills/releases/latest
       > and replace this copy (README → Install) — re-upload on
       > claude.ai/Desktop if that's how it was installed, or re-run the
       > manual CLI unzip into `~/.claude/skills/dev-skills/` (or the
       > project's `.claude/skills/`).
       >
       > **Continue this session on v2.17.0 (outdated), or pause to update
       > to v2.19.0 first?**
       > 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨

     Wait for an explicit answer before moving on to "What are we building?" —
     same as any other session-start finding that changes what happens next
     (branch check, unfinished release check). Don't just print the warning
     and keep going.

     **If the user chooses to continue anyway, the warning doesn't get to
     disappear after this one message.** Carry a short, compact tag —
     `⚠️ outdated (v2.17.0, latest v2.19.0)` — on every later display of the
     gate tracker this session (gate transitions, Section 7 status checks,
     the session banner, handoff summaries per Section 5.6/5.9). This is not
     the loud bracketed warning repeated every time — that would be noise —
     it's a one-line reminder that the condition is still true, the same
     pattern already used for an unfinished release or uncommitted work
     (Section 8): surfaced once loudly, then kept visibly present, never
     silently dropped.
4. This check is unconditional — it runs even in sessions with no git repo
   detected for the *host* project (step 0 below is about that project's own
   repo; this check targets the skill's own upstream repo, which is unrelated
   and always checked the same way).

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

**Native Linux local sessions — offer Remote Control (`--rc`) once, in either
mode.** When step 0 resolves to **local** and the host is native Linux, say so
once and offer it. "Native Linux" is narrower than `uname -s` reporting `Linux`,
which Termux and WSL both do — confirm it is neither (no `com.termux` in
`$PREFIX`, no `microsoft` in `/proc/version`) and that this is not a remote
container.

The suggestion is the **interactive** form, `--rc` / `/rc`, not server mode:

> 💡 **This is a local Linux session.** Starting Claude Code with
> `claude --rc` (or running `/rc` in this one) keeps your terminal session
> exactly as it is *and* publishes it to claude.ai/code and the Claude desktop
> and mobile apps, so you can pick the same session up from either surface.
> Everything still executes here on your machine.

Which invocation matters, so do not offer them interchangeably:

| Command | What it gives | Offer it? |
|---|---|---|
| `claude --rc` / `claude --remote-control` | a normal interactive terminal session that is *also* reachable from the web and desktop apps — you can type in either place | **yes, this one** |
| `/rc` / `/remote-control` | the same, for a session already open | yes — the in-session form |
| `claude remote-control` | server mode: serves sessions to the apps with no local interactive prompt | no — it takes the terminal away, which is the opposite of the point |

It is one line, once per session (Section 5, cost discipline): if the user
declines or ignores it, drop it. It changes nothing about gates, tracks, or the
mode — a session is reachable from more places, not governed differently. Two
failure cases worth naming rather than debugging blind: Remote Control needs an
eligible login (`/login`), and on Team and Enterprise plans it stays off until
an Owner enables it in Claude Code admin settings.

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
   deletions are the exceptions." Semi-autonomous mode does not change this;
   it only adds the full pre-tag report above the block ("Semi-autonomous mode
   — execution", below).
8. **Docker-in-a-web-container — scoped to projects that actually need
   Docker to build.** If the project has a Docker build signal (`Dockerfile`,
   `docker-compose.yml`/`compose.yaml` — the same signal
   `hooks/gate-preflight.sh`'s `produces_compiled_artifact` checks for),
   don't assume the container can build or run it just because the `docker`
   binary is on `PATH`. Measure the daemon, not the binary (see the
   measurement rule below): `docker info` (or `docker version --format
   '{{.Server.Version}}'`). `which docker` only proves the CLI exists — a
   web container commonly ships the client with no daemon behind it, which
   looks identical to "Docker available" until something tries to actually
   build.

   If `docker info` fails in this environment, say so plainly and offer a
   choice — this is a real limitation, not something to route around
   silently:

   > ⚠️ **Docker isn't usable in this container** — the `docker` CLI is
   > present but `docker info` can't reach a daemon, so I can't build or
   > verify the image here. Two ways forward:
   > 1. **Work commit now** — save this progress on the branch (no version
   >    bump, no artifact) so you can pull it down on a machine with a
   >    working Docker daemon and finish Gate 2 there.
   > 2. **CI-only BUILD** — if this repo already has a release workflow that
   >    builds and tests the image in CI, Gate 2 can pass on that basis
   >    (Gate 2, "CI-only" below) instead of a local build.
   >
   > Which do you want?

   This is a different step from the local-artifact-handoff offer below —
   that offer is about letting a human try an already-built artifact by
   hand; this is about whether the artifact can be built and verified in
   this environment at all. Don't conflate marking BUILD "handoff n/a
   (remote container)" with actually resolving this — a container that
   can't build Docker still owes the user this choice before BUILD passes.

Report the detected environment in the session banner.

**Measure, don't infer — for every environment capability recorded anywhere
(gate file, banner, handoff summary).** `which <tool>` proves a binary is on
`PATH`; it proves nothing about whether the thing behind it actually works
(the Docker case above is the concrete failure mode this caught: binary
present, daemon unreachable). Record exactly what was checked and what it
returned — "`docker info`: daemon unreachable", not "no docker"; "push to
`fix/x` succeeded", not "push allowed" — and re-measure at the start of
every session, or whenever the execution context changes (a handoff moves
work from a container to a local clone, or vice versa). A capability noted
in a prior session or a handoff summary is a claim about *that* context, not
a fact about this one — never carry it forward as still true without
re-checking.

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

4. **Check the branch.** Determine the repo's actual default branch — don't
   assume `main` or `master` by name (`git remote show origin` reports
   `HEAD branch: <name>`, or `gh repo view --json defaultBranchRef -q
   .defaultBranchRef.name`). If the user is on that branch, flag it:

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
gates ⬜ pending and `Mode: manual` (format in Section 2). Every session starts
manual — do not carry a mode forward from a handoff summary, a prior session, or
the harness's own permission setting. On local sessions add it to `.gitignore`;
on remote containers it is committed with the work. This file — not the
conversation — is the source of truth for gate state for the rest of the session.

Then show the gate tracker:

```
Dev Skills v2.26.0 active.

Repo: <repo-name> | Branch: <current-branch> | Remote: <origin url or "NOT SET">
Mode: manual (say "auto mode" to have me run the commands and the tag push)
Env: <local / remote container / Termux> | Git: <presented for you to run / run by Claude here>
Shell: <detected shell, or "container bash"> | Last sync: <just now / not synced>
CI: release <✅ workflow name / ❌ none> | build check <✅ workflow name / ❌ none>
Local dev: <✅ build/test command / ❌ not found>
Releases: <✅ all versions tagged / ⚠️ N unfinished: vX.Y.Z, ...>
Skill version: <✅ current (vX.Y.Z) / ⚠️ check skipped, no network / 🚨 see warning above>

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
https://github.com/darthrater78/claude-vibe-skills/releases/tag/v2.26.0
**Updates:** checked automatically every session start (above) — this line is
only the fallback if that check was skipped for lack of network access:
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

## Semi-autonomous mode — execution

The contract is in `SKILL.md` (Operating modes): the user opts in explicitly,
Claude runs the commands instead of presenting them, the tag push and its
follow-on actions are Claude's, and **commit approval is untouched**. This
section is how that runs.

### Entering the mode

The user asks for it. Confirm in one short message — not a lecture — what
changes and what does not, then record it:

> **Semi-autonomous mode on.** I'll run the git commands myself from here —
> commits, pushes, the PR, the merge, watching CI, verification — and I won't
> hand you command blocks unless something fails. What stays yours: **every
> commit still needs your explicit yes**; **the tag push and any ref deletion
> are still yours to run**, because my credentials get `403`'d on exactly those,
> and I'll hand that one block over with a full report of everything I did; and
> anything that needs a decision still comes to you. Say "manual mode" to switch
> back.

Write `Mode: semi-autonomous (approved <date>) — commits and the tag still
require the user's approval` into
`.claude/dev-skills-gates.md` in the same turn. A mode that is agreed to in
conversation and not written down is a mode that disappears at the next
compaction.

On a remote container, the clone-path question (session start, step 0, item 4)
still applies — this mode does not remove the tag block, so a release still
reaches the one moment that needs it.

### Checkpoint 1 — the commit approval

Manual mode asks in three places during a release sequence — Gate 1's version
bump, Gate 5's release-notes approval, Gate 6's pre-ship confirmation.
Semi-autonomous mode carries the first two into one approval at the commit; the
third becomes the pre-tag report below.

> **Ready to commit — this is the one approval for the release.**
>
> **Version:** 2.25.0 → 2.26.0 (MINOR — one `feat`, no breaking change)
> **Commit:** `feat(skill): add semi-autonomous mode`
> **Changes:** [files, line counts, what each does]
> **Gates:** 🔢 ✅ · 🔨 ✅ · 🔒 ✅ 0 Critical / 0 High · 📄 ✅ · 📦 ⬜ · 🚀 ⬜
> **Release notes (v2.26.0):**
> - [entry]
> - [entry]
>
> On your yes: commit, push the branch, open the PR, and merge it once CI is
> green. Then I'll come back with a full report of everything that happened and
> hand you the tag block to run. I'll stop sooner if anything fails or needs a
> decision.

Three rules about that message:

1. **It is an approval of the sequence it describes, and nothing else.** If the
   scope moves afterwards — more commits land, the notes change, the bump
   changes — present it again. Do not stretch one yes over a second release.
2. **It is not a summary to skim past.** The user is approving content they will
   not see again before it is public. The diff summary and the release notes go
   in it in full, not "see above."
3. **A work commit gets the short form.** No version, no notes, no ship plan —
   the diff, the message, and what Claude will do with it (commit and push to
   the branch). Most commits are work commits; do not run a release checkpoint
   for one, and a work commit has no second checkpoint because it never tags.

### Checkpoint 2 — the pre-tag report, and the tag block

**The tag is the one action in this sequence that publishes, and the user runs
it** — in this mode as in manual, because Claude's credentials are denied on
`refs/tags/*` (Section 5.8). Between the two checkpoints Claude has been running
unattended: commits, pushes, a PR, CI runs, a merge. Semi-autonomous mode pays
for that autonomy here, with a full accounting handed over *with* the tag block
— not a summary, and not a bare set of commands to paste.

**Claude never creates or pushes the tag ref itself, in either mode.** Run
Gate 6 step 2's merge confirmation and the version guard first, then report and
hand over the block:

> **Ready to tag v2.26.0 — full report of everything since your commit
> approval.**
>
> **Commits** (3)
> - `257b224` feat(skill): add semi-autonomous mode — 6 files, +412/−38
> - `4c1a88e` fix(hook): … — 1 file, +4/−2
> - `9ab0e12` chore: tracker — 1 file
>
> **Pushes:** `feature/x` → origin, 3 times (no force, no rewrite)
> **PR:** #48 "…" — opened, 2 review comments addressed, merged as `c3a49f7`
> **CI:** `validate` ✅ on 257b224 · ✅ on 9ab0e12 · ✅ on merge commit c3a49f7
>   (one earlier ❌ on 4c1a88e — shellcheck SC2086, fixed in 9ab0e12)
> **Gates:** 🔢 ✅ all refs 2.26.0, v2.25.0 tagged on remote · 🔨 ✅ validate.sh
>   green, bundle rebuilt · 🔒 ✅ 0 Critical / 0 High, docs-only diff ·
>   📄 ✅ CHANGELOG + README · 📦 ✅ PR #48 merged
> **Version guard:** `VERSION` in merged commit c3a49f7 reads `2.26.0`, matches
>   the tag about to be created ✅
> **Deviations from what you approved:** the CI failure above added one commit
>   that was not in the original diff; nothing else changed.
>
> **What the tag does:** pushing `v2.26.0` fires `.github/workflows/release.yml`,
> which builds the bundle and publishes the GitHub release with the notes you
> approved.
>
> **This one is yours to run** — my credentials get `403`'d on tag refs:
>
> ```
> cd "<clone-path>"
> git checkout main && git pull origin main \
>   && grep -q '^2.26.0$' VERSION \
>   && git tag v2.26.0 && git push origin v2.26.0
> ```
>
> Tell me when it's done and I'll take it from there — watch the run, add the
> notes, verify, and commit the SHIP record. The branch deletion is yours too;
> I'll give you that block at the end.

**Rules for this report:**

1. **Every action, not the highlights.** Commits with SHAs and messages, every
   push and whether any rewrote history, the PR and what happened on it, every
   CI run with its conclusion, the merge commit, each gate with the evidence
   that passed it, the version guard result.
2. **Failures, retries, and deviations are the part that matters most.** A run
   that failed and was fixed, a gate that had to be re-run, anything that
   differs from what the user approved at the commit — state it plainly. A
   report that only lists successes is the report nobody needed.
3. **Reconstruct it from evidence, not memory** (`git log`, `gh pr view`,
   `gh run list`, `git ls-remote`, the gate file). If the session was compacted,
   re-derive; a gap you cannot close is something to say, not something to omit.
4. **The block goes in the same message, below the report** (Section 1: the
   tracker and the report go above the block, never after it). Ask for the
   clone path first if it is not known — a `cd` the user has to edit is a
   broken first line. If the user asks for changes instead of running it,
   nothing about the tag moves: handle the request and report again.
5. **Do not take "done" at face value.** 🚀 SHIP stays ⏳ until Claude has
   confirmed the tag on the remote *and* checked what it points at against the
   merge commit (Gate 6, step 3). Reading refs is not a write and is not
   restricted.
6. **It runs for pre-release tags too.** A `-dev`/`-rc` tag publishes an
   artifact; that is the trigger for this checkpoint, not the version's shape.

### Running the sequence

After the yes, the gates run in the normal order with the normal pass criteria.
What changes is only the execution:

| Step | Manual mode | Semi-autonomous mode |
|---|---|---|
| Commit | presented | Claude runs it |
| Branch push | presented (executed in a container) | Claude runs it |
| PR create | presented | Claude runs it |
| Release notes approval | separate ask (Gate 5, step 6) | folded into checkpoint 1 |
| PR merge | presented | Claude runs it, after the merge-confirmation checks — without `--delete-branch` |
| Pre-ship confirmation | separate "type ship" (Gate 6) | **checkpoint 2 — the full pre-tag report, handed over with the block** |
| Tag + tag push | **the user's, in every environment** | **the user's, in every environment** |
| Watch CI, add notes, verify | Claude, either way | Claude, either way |
| Branch cleanup (a ref deletion) | presented | presented — the user's in both modes |
| Tracker SHIP ✅ commit | presented | Claude runs it |

**The last column is where the mode's value is, and the two rows that don't move
are why it is still called semi-autonomous.** Everything Claude can actually do
with its own credentials, it does; the two ref operations the remote denies stay
where they have always been.

**Everything that was a check stays a check.** In particular, Gate 6 step 2's
merge confirmation (`state` reads `MERGED`, and CI ran green *on the merge
commit*) is not a formality that existed because a human was about to paste a
block — it is what stops the tag from landing on the previous commit. Run it
before tagging, exactly as written. The version guard that manual mode chains
into the tag block (`grep -q` against the version file) becomes a check Claude
performs before `git tag`: read the version out of the merged commit, compare it
to the tag being created, and stop if they differ.

**Pre-release tags are handed over the same way.** A dev, alpha, beta, or rc
tag (`v1.2.3-dev.1` — `WORKFLOW_REFERENCE.md`, "Dev releases") is a tag push, so
both modes hand it to the user, with the pre-tag report above it in this one.
What it is *not* is a shortcut around the track rules: a pre-release tag still publishes an artifact,
so it is a release sequence with all six gates, not a work commit. The one thing
it relaxes is the branch — a pre-release tag is expected on a feature branch,
and the workflow's tag-on-default-branch check skips it by design.

**Report progress as a running line, not a narration.** One message when the
sequence starts, one at the pre-tag report, one when it finishes, and one
whenever it stops. Between those, the tracker file is the record — and it is
also where the pre-tag report is reconstructed from, which is another reason to
keep it current as each gate transitions rather than at the end.

### When it stops

Semi-autonomous mode falls back to manual behavior for the operation that failed. The
session stays semi-autonomous; the tracker is updated before Claude reports.

| What happened | What Claude does |
|---|---|
| A required gate is not ✅ or ➖ N/A | Stop, surface the blocking gate by name, run it. Never edit the tracker to clear it |
| Branch push returns `403` | Present the block, report it plainly. No retry, no re-route, no different ref |
| The tag or a ref deletion is due | Not a failure — the block goes to the user by design, with the report above it (checkpoint 2) |
| `src refspec ... does not match any` | Not a permissions failure: the tag was never created. Re-run `git tag`, then push (Gate 6, step 3) |
| CI fails on the PR | Stop before merging. Report the failing job and its output, propose a fix, wait |
| The release workflow fails after the tag | Stop. Recovery needs a tag deletion, which needs its own approval (`SKILL.md`, Operating modes) |
| A Critical or High security finding | Hard stop, same as manual |
| A decision with more than one defensible answer | Ask. Semi-autonomous mode is not permission to pick for the user |

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

**Before asking, check the commit types since the last tag** (`SKILL.md`
§1.1) — `git log <last-tag>..HEAD --oneline` — and use them as a signal:
any `!`/`BREAKING CHANGE:` → suggest MAJOR; any `feat` with no breaking
change → suggest MINOR; only `fix`/`chore`/`docs`/etc. → suggest PATCH.
State which commits drove the suggestion and let the user confirm — commits
that don't follow the convention (or a mixed history) just mean no signal,
not a wrong answer; ask plainly in that case.

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

**A run only counts as evidence if the tree it ran against didn't move
under it.** An edit landing mid-run — the session itself, or anything
else touching the working tree — invalidates the result even when the run
finishes green, because the pass no longer says anything about the code
that's about to be committed. Capture `git status --porcelain` and `git
rev-parse HEAD` immediately before starting the build/test run and again
immediately after it finishes; if either differs, the run does not count —
the gate is still pending, rerun against the now-settled tree. A project's
own build/check script can make this cheap to verify by printing both
snapshots itself rather than relying on Claude to remember to check.

**A test build is mandatory before any commit.** When building an app, create a
test/dev version and verify it runs correctly before staging or committing anything.
This means:
1. Build the project (dev/test mode where applicable)
2. Launch or preview the app — confirm it starts, the golden path works, and
   no regressions are visible
3. Only after the test build is verified working does this gate pass

If the app cannot be tested locally (e.g. requires external infrastructure),
say so explicitly rather than skipping — the user decides whether to proceed.

**When the obstacle is structural, not missing infrastructure — a third
state.** The case above is a build that needs something normally available
elsewhere. A different case: the build system exists and is correct, but
*this specific environment* cannot run it — no Android SDK in the container,
a network policy blocking the package registry, the wrong host OS for a
native build. That is not ➖ N/A (a build system exists) and it is not a
generic "can't test locally" either — it gets its own state, permitted only
when all three hold, and stated on the tracker:

1. The obstacle is structural, not a missing setup step — state it
   concretely ("`dl.google.com` denied by network policy"), never "it didn't
   work here."
2. The CI verdict covers **the exact tree being merged**, not an ancestor of
   it — for a PR, update the branch onto the target head first so the run
   builds the merge result.
3. Everything checkable locally *was* checked — config files parsed, pure
   modules compiled and tested in isolation, linters run.

> ✅ **BUILD GATE PASSED — CI-only** — Android SDK unavailable and
> `dl.google.com` blocked in this container; config and lint checked locally;
> CI build required before merge.

This is weaker than the local gate and is recorded as such. It does not
license "CI will catch it" on a project where a local build merely takes a
while — that is still a straightforward BUILD GATE BLOCKED, not this state.

**Prove a never-run release step before a tag depends on it.** A release
workflow's own steps aren't proven by ordinary CI — a Docker registry
login, a signing step, a computed-version extractor, an ancestor-fallback
path only exercised on tag push — until a tag actually goes through them for
real once. Discovering a bug in one of those steps *during* a live release
means cancelling a run, deleting a wrongly-published release, and re-tagging
(the recovery runbook under Gate 6). Cheaper: before a tag push is about to
exercise a step that has never actually run in this repo, copy it out of
`release.yml` and dry-run it here if the tooling allows — against the local
build, with real (or scoped test) credentials where that's safe, or by hand
inspection where it isn't. Keep a short "unproven" note for anything that
still can't be exercised this way (e.g. it genuinely needs the tag-push
trigger's context) and carry it forward release to release until it's
actually run once for real — don't let it quietly stop being tracked just
because the release it was flagged on shipped anyway.

**Local artifact handoff — mandatory offer for compiled outputs, local Linux
and Windows sessions only.** For any build that produces something a person
installs or runs outside a terminal — a Docker image, a Windows `.exe`, an
Android `.apk` — the smoke test above proves the code runs; it does not prove
the artifact is something the user can actually pick up and try. This offer
depends on the execution environment detected at session start (step 0) and
the host shell (step 2):

| Session | Offer |
|---|---|
| **Local, Linux host** (shell = Linux Terminal, or WSL) | Full offer — Docker images, Windows `.exe`, Android `.apk` |
| **Local, Windows host** (shell = Windows PowerShell or Git Bash) | Narrowed — Windows `.exe` and Android `.apk` only; no Docker load/run instructions |
| **Remote container (cloud) or Termux (mobile)** | Not offered — these environments already ship through the regular CI-driven path (Gate 6), which is the correct handoff there |

"Not offered" here is about this specific step — letting a human try an
already-built artifact by hand. A web container that can't build Docker at
all is a separate, earlier problem (session start, Step 0, item 8) and is
not resolved by this row.

Where the offer applies, after the smoke test passes and before this gate is
marked passed, give the user a way to test the real build themselves:

- **Windows `.exe` and Android `.apk`:** copy the built artifact into a local
  folder (e.g. `dist/`, `build/output/`) and tell the user the exact path, so
  they can download or copy it to a device and run it.
- **Docker images (Linux host only):** give the exact commands to load and
  run the image locally — `docker load -i <file>` (if built to a tarball) or
  `docker build -t <tag> .`, then `docker run ...` with the ports/volumes the
  project needs.

  **Tear it down once its purpose is served.** A container started here —
  or for the "prove a never-run release step" check above, or for any other
  Gate 2 testing — is a running resource, not a fire-and-forget check.
  Stop and remove it after the commit it verified is submitted, or
  immediately if the user declines to try it: `docker stop <name>` (or
  `docker compose down` for a compose stack), then `docker rm <name>` if it
  wasn't started with `--rm`. Before the session ends (Section 8) or this
  gate closes, `docker ps` to confirm nothing test-related is still
  running — an orphaned container left behind by a smoke test is a silent
  resource leak, not a passed gate.

This offer is mandatory **every time the build changes**, not only the first
time in a session — a rebuild after a code change gets the same offer as the
first build did. It is not mandatory to *accept*: if the user says they don't
need to try this particular build by hand, skip it and move on. What can
never be skipped silently is the offer itself.

**Proceeding without acting on the offer counts as declining it — it is not
an unanswered question that blocks the gate.** If the user responds to a
commit/ship prompt with "commit" or "go ahead" without having run the image
or exe, that is the decline; don't hold BUILD open waiting for an explicit
"no thanks." Record it with the user's own words:
`handoff offered, user said "Commit" without running the image — recorded
as declined`. This is different from silently marking the annotation
"declined" on Claude's own initiative — the record should make clear the
user moved on, not that Claude assumed on their behalf.

This step comes after the automated smoke test, not instead of it — the
smoke test confirms the code runs; this confirms a human can actually get
their hands on it.

**Record the outcome on the tracker, not just in chat.** Where
`hooks/gate-preflight.sh` is installed, it enforces this deterministically:
for any repo with a Docker/.exe/.apk build signal (`Dockerfile`, `.csproj`/
`.sln`, or an Android Gradle project), it denies a BUILD gate marked ✅ unless
the tracker's BUILD line also says what happened to the offer. Write the
BUILD line as one of:

- `🔨 BUILD      ✅ <build description>; handoff offered, user tried it`
- `🔨 BUILD      ✅ <build description>; handoff offered, user declined to try it`
- `🔨 BUILD      ✅ <build description>; handoff n/a (remote container / Termux session)`

Note the offer is always made where it applies — "declined" above describes
the user's choice not to try the build by hand, never Claude skipping the
offer itself. There is no valid annotation for "didn't offer."

The hook can see whether the tracker says the offer happened; it cannot see
the conversation, so a passed gate with no annotation reads as "skipped," not
"forgot to write it down."

**Projects with CI release workflows.** If the project has a GitHub Actions
workflow that builds release artifacts on tag push (check
`.github/workflows/` for `on: push: tags:`), the local build gate covers
only the **debug/test build**. The release artifact is built by CI during
Gate 6 — do not build it locally. Gate 2 passes when the debug build
compiles and the app is verified working.

> ✅ **BUILD GATE PASSED** — debug build verified working (release build deferred
> to CI); handoff offered — Android `.apk` copied to `dist/`, user declined to
> try it by hand this round

**Projects with no build step** (config repos, skill repos, documentation-only
repos, pure script collections): mark this gate ➖ N/A with an explanation:

> ➖ **BUILD GATE N/A** — this is a [skill/config/docs] repo with no build system.

Do not silently skip — always show the N/A status on the tracker.

> ✅ **BUILD GATE PASSED** — test build verified working
> Output: [artifact path]

### Gate 3 — Security & Quality 🔒

**Mandatory after every build.** Two steps, both must pass: security scan and
quality review.

**Before scanning, load reference files from this skill's base directory**
(shown when the skill loaded, e.g. "Base directory for this skill: ..."):
1. Read `SECURITY_REFERENCE.md` — bad/good code examples for cross-platform
   and language-general security patterns.
2. Read `QUALITY_REFERENCE.md` — bad/good code examples for cross-platform
   structure and performance anti-patterns.
3. Detect the project's platform(s) using the same signal table as
   `WORKFLOW_REFERENCE.md` Step 1 (Docker/Windows/Linux/Android/etc). For each
   match, also read that platform's file: `SECURITY_WINDOWS.md` for Windows,
   `SECURITY_LINUX.md` for Linux or Docker/container projects,
   `SECURITY_ANDROID.md` **and** `QUALITY_ANDROID.md` for Android. A project
   can match more than one (e.g. a Dockerfile targeting a Windows base image)
   — load every file that applies. If nothing matches confidently, skip the
   platform files but say so in the scan output rather than silently omitting
   the check.
Use these examples to pattern-match against the code being reviewed.

#### Step 1 — Security scan

Run a full scan of all source files. Check for every pattern category in
Sections 4.1–4.3 and the full rule checklists in `SECURITY_REFERENCE.md` plus
whichever platform file(s) matched (loaded above).

**Then audit the dependencies — this part is not optional and not limited to
packages the session touched.** Run the ecosystem's audit tool against the
current lockfile:

| Ecosystem | Command |
|---|---|
| Node | `npm audit` / `pnpm audit` / `yarn npm audit` (Berry; classic is `yarn audit`) |
| Python | `pip-audit` (note the hyphen — there is no `pip audit` subcommand) |
| Rust | `cargo audit` |
| Go | `govulncheck ./...` |
| .NET | `dotnet list package --vulnerable --include-transitive` |
| Java | `mvn org.owasp:dependency-check-maven:check` / `gradle dependencyCheckAnalyse` |
| Any | `osv-scanner scan source .` |

If no audit tool is available for the ecosystem, say so explicitly rather than
passing the step in silence — an unaudited dependency tree is an unknown, and
unknown is never "passed" (Section 2).

Report dependency findings with the advisory ID, the package, the installed
version, and the fixed version:

> 🚨 `lodash@4.17.15` — GHSA-35jh-r3h4-6jhm (Critical, prototype pollution)
>    Fixed in 4.17.21 — bump the pin
> ⚠️ `urllib3@1.26.5` — transitive via `requests` — CVE-2023-43804 (High)
>    Fixed in 1.26.17 — bump `requests` to pull the fixed range

**Hard stops (must fix before proceeding):**
- 🚨 Critical: hardcoded secrets, SQL injection, `shell=True` with user input,
  disabled TLS, `pickle` on untrusted data, RCE vectors
- ⚠️ High: path traversal, missing auth, `debug=True` in prod, weak crypto for
  passwords, `random` for tokens, no input validation on endpoints
- 🚨⚠️ **Any dependency — direct or transitive — carrying a Critical or High
  advisory** (Section 4.1). A pinned version is not a safe version; pinning
  fixes *which* CVEs the project has, not *whether* it has any. Bump to the
  fixed release and re-run the audit. Where no fixed release exists upstream,
  the gate does not pass silently: surface the advisory and the options
  (patch, vendor, replace, or accept with a documented reason) and let the
  user decide on the record

**Fixing a Critical or High — three checks, every time, not just "patch and
move on":**
1. **Reproduce before writing the fix.** A fix written from reading the code
   is a guess about the bug shape; a fix written after triggering the actual
   failure is a fix for the actual bug. Once it's fixed, look for sibling
   paths into the same bad state — the same class of bug rarely has exactly
   one entry point, and a fix that closes only the one you found leaves the
   others live.
2. **Flag any existing test whose assertions encode the insecure behavior as
   correct.** A test isn't proof of correctness just because it's green — a
   test that asserts "a locked resource returns 'no key found'" instead of
   "access denied" is a bug wearing a passing test as camouflage. Read what
   the test actually asserts, not just whether it passes.
3. **Confirm every new regression test fails without the fix.** Revert the
   fix (or comment it out) and re-run the new test — if it still passes, the
   test isn't testing the vulnerability, and shipping it as "covered" is
   false confidence. Put the fix back before committing.

**Show and let user decide:**
- 📝 Medium: bare `except`, no type hints, mutable defaults, `assert` for validation,
  logging sensitive data, unpinned deps, dependencies with a Medium/Low advisory,
  dependencies several majors behind current with no advisory yet
- 💡 Low: missing `encoding=` on `open()`, string paths, missing static analysis in CI

Security step passes at zero Critical and zero High — **in the code and in the
dependency tree**. Both halves are reported, so a clean scan of hand-written
code can never stand in for an unaudited manifest:

> ✅ **Security scan passed** — 0 Critical, 0 High
> Code: 0 Critical, 0 High | Medium: N (shown above, user accepted) | Low: N
> Dependencies: `npm audit` clean — 0 Critical, 0 High | Medium: N | Low: N

If the project has no dependency-update automation, add the recommendation once
here rather than waiting for a Dependabot backlog to appear:

> 💡 No `.github/dependabot.yml` — nothing watches these packages between
> security gates. Want me to add one? (`WORKFLOW_REFERENCE.md`)

#### Step 2 — Quality review

Scan the changed code for every quality pattern in `QUALITY_REFERENCE.md`, plus
`QUALITY_ANDROID.md` if Android matched (loaded above), and the checklist
below:

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
   Claude to execute directly. **In semi-autonomous mode, Claude runs all three itself**
   ("Semi-autonomous mode — execution", above); no block is presented unless one fails.
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

7. Wait for explicit approval of the PR content and release notes. **In
   semi-autonomous mode this approval already happened** — the release notes were part
   of the single commit checkpoint. Post the PR and the notes for the record and
   continue to Gate 6. Re-ask only if the notes changed since that checkpoint.

**Never commit directly to main/master.** All work happens on feature/fix/release
branches and merges via PR. If the session is on the default branch when Gate 5
is reached, create a branch first.

> ✅ **RELEASE GATE PASSED** — PR [url] ready, release notes approved
> Pending: merge, tag, and publish (Gate 6)

### Gate 6 — Ship 🚀

Merge, tag, and publish. All three happen here, not in Gate 5.

**Pre-ship summary — explicit confirmation required.** "Yeah" or "ok" is not
enough — the user must say "ship", "yes push", or "go ahead." **In
semi-autonomous mode this confirmation becomes checkpoint 2: the full pre-tag
report, handed over with the tag block** ("Semi-autonomous mode — execution",
above). It is a longer stop than this one, not a shorter one — the user is
reading an account of work they did not watch happen, and then running the tag
themselves.

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

   **When Claude is the one executing this — a remote container, or a
   semi-autonomous session — drop `--delete-branch` and hand the branch
   deletion to the user with the tag block.** Deleting a ref is its own
   permission, denied (`403`) independently of the merge itself (Section 5.8),
   so a merge that carries the flag can succeed at merging and still fail at
   deleting, or fail as a whole. The flag is fine in a block the user runs.

   **Confirm the merge actually landed before doing anything else.** A
   request to merge is not a merged commit — don't treat "I ran the command"
   or "the user said it's done" as equivalent to verifying it:
   ```
   gh pr view <number> --json state -q '.state'    # must read "MERGED"
   sha=$(gh pr view <number> --json mergeCommit -q '.mergeCommit.oid')
   gh run list --commit "$sha" --json status,conclusion
   ```
   The second check matters as much as the first. Being on the default
   branch proves the commit was merged; it says nothing about whether CI
   ran against *that* commit or passed. **Do not proceed to step 3 until
   both hold.** This is not optional caution — a tag pushed before the merge
   lands on the *previous* commit, which is already on the default branch
   with CI already green from an earlier point in time. It passes both of
   these exact checks and publishes the old code under the new tag. The
   release workflow's own gate job (`WORKFLOW_REFERENCE.md`, "Verify tag is
   on default branch" / "Require a passing CI run") re-checks this on the
   tagged commit, but that job runs *after* the tag is already pushed — the
   check here is what stops the wrong tag from being pushed in the first
   place.

3. **Tag and push — in manual mode the user runs this block, and not before
   step 2 is confirmed.** Tag pushes are denied (`403`) to Claude's credentials far
   more often than they succeed, and this is the push that starts the
   release build (Section 5.8, "Tag pushes and ref deletions are the
   exceptions").

   **Semi-autonomous mode does not change who runs this step** — the `403` this
   carve-out exists for comes from the remote, not from the skill. What it
   changes is what goes above the block: the full pre-tag report of everything
   Claude did since the commit approval ("Semi-autonomous mode — execution",
   checkpoint 2), rather than a bare command block. Run step 2's merge
   confirmation and the version guard first either way. The rest of this step —
   the verification, the `src refspec` case, the UI fallback — is identical in
   both modes. Present it, in one block, with the sync in front so the tag
   lands on the merged commit, **and the version declared in that commit
   checked before the tag is created** — chained with `&&` so a mismatch
   stops the block before `git tag` runs. Use `exit` only inside the sourced
   extractor logic, never bare in the chain itself — a bare `exit` closes the
   user's interactive shell, not just the command:

   **Describe the step in words until both checks in step 2 have passed.**
   Handing over runnable commands before the merge is confirmed is exactly
   how a tag gets pushed against the wrong commit — say what will happen
   ("once the merge and CI are confirmed, I'll give you the tag block"), not
   the commands themselves.

   **If the clone path is not known yet — every remote session, by design
   (step 0, item 4) — ask for it before writing this block.** A `cd` the user
   has to edit is a broken first line.

   ```
   cd "<clone-path>"
   git checkout main && git pull origin main \
     && grep -q '^VERSION_STRING = "1.2.3"$' <version-file> \
     && git tag v1.2.3 && git push origin v1.2.3
   ```
   The literal string to grep for is whatever this project's version lives
   as — the same value and the same file the release workflow's own version
   check reads (`WORKFLOW_REFERENCE.md`'s per-ecosystem extractors: a
   `package.json` field, a `pyproject.toml` table, a `VERSION` file). Write
   this line from that same source, not a second hand-rolled check — two
   independently written version checks drift apart exactly the way CI and
   local dev drift apart (`GATE_REFERENCE.md` session start, step 6). If the
   project's versioning is tag-derived or computed (`setuptools-scm`, a
   `git describe`-based Android `versionName`), there is nothing to grep for
   — drop this clause and say so.

   > 📌 **Pushing that tag is what starts the release build.** Run the block
   > above and tell me when it's done — I'll watch the workflow from here.

   No local clone (web or mobile session)? Offer the UI instead: **Releases →
   Draft a new release → Choose a tag → create it on the default branch.** Same
   ref, same trigger.

   **Treat an unqualified "pushed" or "done" as unverified — confirm it
   yourself before touching 🚀 SHIP.** Reading refs is not a write and is not
   restricted. Existence alone is not enough: a tag can exist and still point
   at the wrong commit if it was created before this session's merge, or by
   a stale local branch. Check both the tag and what it points at, and
   compare that SHA against the merge commit from step 2:
   ```
   git ls-remote --tags origin v1.2.3
   git rev-parse v1.2.3^{}          # what the tag actually points at, locally after fetch
   ```
   🚀 SHIP stays ⏳ until the tag is confirmed on the remote *and* its target
   commit matches the one confirmed merged in step 2 — not just that some
   tag named `v1.2.3` exists.

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

7. **Commit and push the gate-state file's SHIP ✅ record — the last action
   of this gate, not an afterthought.** This only applies when
   `.claude/dev-skills-gates.md` is tracked in this repo (the remote-container
   convention, Section 2 — or a local repo that force-adds it despite
   gitignoring it, the way this one does). A tracker that says SHIP ✅ only
   in the local working tree does not close the sequence: the next session's
   re-derivation (Section 2) reads the remote and the committed history, sees
   RELEASE/SHIP still ⬜ there, and has no way to know the release actually
   finished. Commit it on its own (a tracker-only commit, same as any other
   work commit) and push before telling the user the sequence is done.

> ✅ **SHIP GATE PASSED** — PR merged, tag pushed, CI release published
> Verified: tag ✅ | release ✅ | PR merged ✅ | CI assets ✅

#### Recovery: a tag landed on the wrong commit

A tag can slip past both the merge-confirmation checks above and the
workflow's own gate job — pushed too early, or by hand outside this
session — and still get built and published under the wrong content before
anyone notices. If that happens:

1. **Cancel the release run immediately.** `gh run cancel <run-id>`. Don't
   wait to assess first — an image build with a warm cache can reach its
   push step in well under a minute, faster than the assessment in step 2
   below takes to do properly.
2. **Record what already went out before touching anything.** Read the
   cancelled (or completed) run's log for what it actually pushed —
   registry tags, uploaded assets — and `gh release view <tag>` for what
   GitHub shows as published. Cleanup decisions in the steps below depend on
   knowing this first; guessing what shipped and skipping something is how
   a bad artifact keeps circulating after the "fix."
3. **Delete the GitHub release, with approval.** `gh release delete <tag>`
   is a destructive action on a shared, visible artifact — get explicit
   approval the same as any other destructive step, don't fold it into
   "cleaning up."
4. **The tag deletion goes to the user.** `git push origin :refs/tags/v1.2.3`
   is a ref write, same as any other tag operation (Section 5.8) — present
   it, never execute it, regardless of how the wrong tag got there.
5. **Land the real release, then re-tag** — merge (or finish merging) the
   correct commit, re-run the merge-confirmation checks in step 2 above, and
   only then push the tag again. Two things this step does *not* cover:
   - **Floating tags** (`:latest`, `:dev`) get overwritten automatically by
     the correct build once it publishes — no separate action needed for
     those.
   - **Registry versions already pushed** under the wrong tag (a container
     image, a package version) usually cannot be deleted with the
     credentials this session has — deleting a package version needs
     `delete:packages`, a scope session tokens typically lack. Don't plan
     cleanup around removing it; plan around making sure nothing resolves
     to it anymore (the corrected tag/version takes over, floating tags move
     forward, the GitHub release pointing at it is gone per step 3).
6. **Add the tag/version match check if the workflow doesn't have one yet**
   (`WORKFLOW_REFERENCE.md`, "Verify tag matches the version in the tagged
   commit") — the recovery above fixes this incident; the check is what
   stops it from happening a second time.

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
deletions are the exceptions"), in both modes, so this splits into two blocks:

Claude runs (or presents, on a local session):
```
gh pr merge <number> --merge --delete-branch
git checkout main && git pull origin main
```

Same caveat as the CI-driven path's step 2: when Claude is executing this
rather than presenting it, drop `--delete-branch` and hand the branch deletion
over with the tag block. The flag belongs in a block the user runs.

**Confirm the merge landed before handing over the tag block below** — same
check as the CI-driven path (`gh pr view <number> --json state -q '.state'`
must read `MERGED`). There is no gate job here to catch a premature tag the
way a CI release workflow's own version check would (this path has no such
workflow by definition), so this manual confirmation is the only thing
standing between a tag and the wrong commit.

The user runs — stop here until they confirm the tag is on the remote. **This
is the same in semi-autonomous mode**; what changes there is that the full
pre-tag report goes above this block ("Semi-autonomous mode — execution",
checkpoint 2):
```
cd "<clone-path>"
git checkout main && git pull origin main \
  && grep -q '^VERSION_STRING = "1.2.3"$' <version-file> \
  && git tag v1.2.3 && git push origin v1.2.3
```
As in the CI-driven path, the `grep` clause is the version guard — same
literal value and file this project's version actually lives in, chained
with `&&` so a mismatch stops the block before `git tag` runs. Drop it only
if versioning is tag-derived/computed.

Once pushed, don't take "done" at face value — confirm the tag exists *and*
points at the merge commit, not just that some tag by that name exists:
```
git ls-remote --tags origin v1.2.3
git rev-parse v1.2.3^{}
```

If the push instead reports `error: src refspec v1.2.3 does not match any`
instead of a `403`, the tag was never created locally — see the
troubleshooting note under the CI-driven path's tag step above. Re-run
`git tag v1.2.3` from inside `<clone-path>` and push again.

Then, once `git ls-remote --tags origin v1.2.3` shows the tag:
```
gh release create v1.2.3 <artifacts> --title "v1.2.3" --notes "..."
```

**Post-ship verification (mandatory):** The gate does not pass without all four:
1. **Tag on remote:** `git ls-remote --tags origin v1.2.3` returns the tag
2. **Release exists:** visible via `gh release view v1.2.3`
3. **PR merged:** state is "merged", not just "closed"
4. **Assets match:** expected artifacts are attached per detection above

**Then commit and push the gate-state file's SHIP ✅ record — the last
action of this gate, not an afterthought.** Same rule as the CI-driven path
above: applies whenever `.claude/dev-skills-gates.md` is tracked in this
repo. A SHIP ✅ that only exists in the local working tree hasn't actually
closed the sequence.

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

