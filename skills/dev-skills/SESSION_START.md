# Session Start Reference

Loaded on demand by the dev-skills skill, **once per session**, when the skill
loads (`SKILL.md` Section 6). It holds the session-start procedure: the
self-check, the version check, execution-environment detection, the repo and
shell questions, workflow detection, the unfinished-release check, and the
session banner.

Nothing here is needed again after the session has started. The gate recipes
are in `GATE_REFERENCE.md` (gates 1–5) and `SHIP_REFERENCE.md` (gate 6);
semi-autonomous execution is in `AUTO_MODE.md`.

Section numbers referenced here (Section 1, 2, 5.7, …) point at `SKILL.md`.

---

## Session start

When the skill loads:

**Self-check:** Verify that `GATE_REFERENCE.md`, `SECURITY_GATE.md`,
`SHIP_REFERENCE.md`,
`AUTO_MODE.md`, `SECURITY_REFERENCE.md`, `QUALITY_REFERENCE.md`,
`SHELL_REFERENCE.md`, `WORKFLOW_REFERENCE.md`, `SECURITY_WINDOWS.md`,
`SECURITY_LINUX.md`, `SECURITY_ANDROID.md`, and `QUALITY_ANDROID.md` exist in this skill's base directory (shown when the
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
4. **Skip step 2 (shell detection) entirely — including for the tag and
   ref-deletion blocks.** Every git command Claude runs here uses the
   container's own bash. The tag-push and ref-deletion carve-out (Section 5.8)
   still hands the user a block to run on their own machine, but that block
   carries no `cd` and nothing else that varies by shell: it is plain
   single-line `git` commands (`git checkout`, `git pull`, `git tag`,
   `git push`) that run unmodified in every shell `SHELL_REFERENCE.md` lists.
   So there is no clone path to ask for and no shell to ask about — put "run
   this from your local clone" in the prose above the block and leave the block
   itself copyable as given (`SHELL_REFERENCE.md`, "Tag and ref-deletion blocks
   carry no `cd`").
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

**Batch the reads.** Steps 1, 4, 5 and 7 are independent read-only commands,
and every one of them run as its own call resends the whole conversation
again. Chain them into one invocation and read the combined output — for
example `git rev-parse --is-inside-work-tree && git remote -v && git status
-sb && git ls-remote --heads origin && git ls-remote --tags origin`. Steps 2
and 3 are questions for the user and are not part of that chain. This changes
nothing about what gets checked; a step that is skipped is still a step that
was skipped.

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
Dev Skills v2.28.0 active.

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
https://github.com/darthrater78/claude-vibe-skills/releases/tag/v2.28.0
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

