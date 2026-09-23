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

**Probe first: one read-only call answers every check below.** It is the
first action of the session; the version check below is the first thing
*reported*, and step 0 is the first *decision*. The self-check,
the version check, step 0's environment signals and steps 1, 1a, 4, 6 and 7
used to be separate calls, and each one resent the whole conversation. Run this
block once from anywhere in the project (it moves to the repo root itself), as a single Bash call, with `B` set to this skill's base directory,
then read every step's answer from its `key=value` output:

```bash
export B="<this skill's base directory>"
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || true
p() { k=$1; shift; if o=$("$@" 2>&1); then echo "$k=$(printf '%s' "$o" | tr '\n' ' ')"; else echo "$k=ERROR $(printf '%s' "$o" | tr '\n' ' ' | cut -c1-200)"; fi; }
p skill_installed bash -o pipefail -c "grep -m1 '^version:' \"\$B/SKILL.md\" | sed 's/version:[[:space:]]*//'"
p skill_latest bash -o pipefail -c "git ls-remote --tags https://github.com/darthrater78/claude-vibe-skills.git | sed 's#.*refs/tags/##' | grep -v '\^{}' | sort -V | tail -1"
p skill_missing bash -o pipefail -c "for f in GATE_REFERENCE SECURITY_GATE SHIP_REFERENCE AUTO_MODE SECURITY_REFERENCE QUALITY_REFERENCE SHELL_REFERENCE WORKFLOW_REFERENCE SECURITY_WINDOWS SECURITY_LINUX SECURITY_ANDROID QUALITY_ANDROID UPDATE_REFERENCE; do [ -f \"\$B/\$f.md\" ] || printf '%s ' \$f.md; done"
p env_termux bash -o pipefail -c 'case "${PREFIX:-}" in *com.termux*) echo yes;; *) echo no;; esac'
p env_wsl bash -o pipefail -c 'grep -qi microsoft /proc/version 2>/dev/null && echo yes || echo no'
p repo_root git rev-parse --show-toplevel
p origin bash -o pipefail -c "git remote get-url origin | sed -E 's#://[^/@]+@#://#'"
p branch git branch --show-current
p status git status -sb
p gh_installed bash -o pipefail -c 'command -v gh || echo no'
p gh_repo bash -o pipefail -c 'gh repo view "$(git remote get-url origin)" --json nameWithOwner,isFork,parent,viewerPermission,defaultBranchRef'
p gh_login gh api user -q .login
p default_branch bash -o pipefail -c "git remote show origin | sed -n 's/.*HEAD branch: //p'"
p latest_tag bash -o pipefail -c "git ls-remote --tags origin | sed 's#.*refs/tags/##' | grep -v '\^{}' | sort -V | tail -1"
p untagged bash -o pipefail -c "[ -f CHANGELOG.md ] || { echo no-changelog; exit 0; }; t=\$(git ls-remote --tags origin | sed 's#.*refs/tags/v\{0,1\}##' | grep -v '\^{}'); grep -oE '^## \[?[0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md | grep -oE '[0-9.]+\$' | while read v; do printf '%s\n' \"\$t\" | grep -qxF \"\$v\" || printf '%s ' \"\$v\"; done"
p workflows bash -o pipefail -c 'ls .github/workflows 2>/dev/null || echo none'
p release_workflow bash -o pipefail -c "grep -lE '^[[:space:]]*tags:' .github/workflows/* 2>/dev/null || echo none"
p local_dev bash -o pipefail -c 'for f in scripts Makefile justfile Taskfile.yml package.json tox.ini noxfile.py gradlew Cargo.toml *.sln *.csproj Dockerfile compose.yaml docker-compose.yml; do [ -e "$f" ] && printf "%s " "$f"; done; echo'
```

Reading it:

- **`key=ERROR …` is a finding, not a blank.** Every key prints every time, and
  a failed command prints `ERROR` with its message. It is never skipped. Handle
  it the way the step it answers says to, for example
  `skill_latest=ERROR` → "version check skipped — no network access".
- **Git keys with `ERROR` when `repo_root=ERROR`** mean no git repo. The git
  steps do not apply.
- **`gh_installed=no` or `gh_repo=ERROR`** → use the GitHub MCP equivalents
  (step 0) for step 1a, and for anything the probe could not answer.
- **`untagged` lists changelog versions with no remote tag.** The version being
  built right now shows there too, and that is expected. Step 7 is about the
  versions before it.
- **`origin` has any credentials in the URL stripped** (`https://user:token@…`
  becomes `https://…`) so a token never lands in the transcript.
- **The probe only reads.** It fetches nothing, so `status`'s ahead/behind
  counts are as of the last fetch, and step 3's sync offer still stands.

Steps 2 and 3 are questions for the user, not reads. Every step below still
applies: the probe changes how many calls it takes, never what gets checked.

**Self-check:** Verify that `GATE_REFERENCE.md`, `SECURITY_GATE.md`,
`SHIP_REFERENCE.md`,
`AUTO_MODE.md`, `SECURITY_REFERENCE.md`, `QUALITY_REFERENCE.md`,
`SHELL_REFERENCE.md`, `WORKFLOW_REFERENCE.md`, `SECURITY_WINDOWS.md`,
`SECURITY_LINUX.md`, `SECURITY_ANDROID.md`, `QUALITY_ANDROID.md`, and
`UPDATE_REFERENCE.md` exist in this skill's base directory (shown when the
skill loaded, e.g. "Base directory for this skill: ..."). If any is missing,
warn immediately:

> ⚠️ **Skill self-check failed:** [filename] not found in [base directory].
> The security/quality gate cannot run properly without it.

**Version check — run every time the skill loads, and report it before anything else.**
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
   - **Behind:** treat it like a failed security gate, not an FYI. It is **the
     first thing in the first message**, above any greeting and the banner,
     bracketed so it can't pass as routine output, with the versions at both
     ends:

       > 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨
       > **STOP — dev-skills is out of date: running v2.17.0, latest is v2.19.0.**
       >
       > Gates run in this session may be missing fixes released since
       > v2.17.0. Release notes:
       > https://github.com/darthrater78/claude-vibe-skills/releases
       >
       > **How do you want to update?**
       > 1. **I install it:** I download v2.19.0 from the release and replace
       >    this copy.
       > 2. **You install it:** I give you one command to run.
       > 3. **Continue on v2.17.0** (outdated).
       > 🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨

     Offer only the options the install location allows
     (`UPDATE_REFERENCE.md`), and ask it in the first `AskUserQuestion` call.
     Wait for an explicit answer before "What are we building?". If the user continues
     anyway, carry `⚠️ outdated (v2.17.0, latest v2.19.0)` on every later
     tracker display, status check, banner and handoff for the rest of the
     session: loud once, then visibly present, never silently dropped.

   **Before offering the update choice, read `UPDATE_REFERENCE.md`** from this
   skill's base directory: which options the install location allows, and the
   exact install commands. Never build an install command from memory.

4. This check is unconditional — it runs even in sessions with no git repo
   detected for the *host* project (step 0 below is about that project's own
   repo; this check targets the skill's own upstream repo, which is unrelated
   and always checked the same way).

**Step 0 — Execution environment detection. Decide this before any other step;
it changes how git works for the rest of the session.**

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
mode.** Only when step 0 resolves to **local** on native Linux: not Termux (no
`com.termux` in `$PREFIX`), not WSL (no `microsoft` in `/proc/version`), not a
container. Offer the **interactive** form:

> 💡 **This is a local Linux session.** Starting Claude Code with
> `claude --rc` (or running `/rc` in this one) keeps your terminal session
> exactly as it is *and* publishes it to claude.ai/code and the Claude desktop
> and mobile apps, so you can pick the same session up from either surface.
> Everything still executes here on your machine.

Never offer `claude remote-control`: that is server mode, which takes the
local prompt away. It is one line, once. If the user declines or ignores it,
drop it. It changes nothing about gates, tracks or mode. It needs an eligible
login (`/login`), and on Team/Enterprise plans an Owner must enable it in
Claude Code admin settings.

**Remote container specifics:**

1. **Nothing needs cloning — the repo is already there.** The container is
   provisioned with a fresh clone at session start. Never present `git clone`,
   and never treat a missing local repo as the user's problem to fix.
2. **The work exists only in the container until it is pushed.** Say this once,
   early:

   > ⚠️ **Remote session:** these edits live in this container. It is reclaimed
   > when the session ends, so anything uncommitted is lost. I'll commit and
   > push from here once you approve.

3. **`gh` is typically not installed.** The probe's `gh_installed` and
   `gh_repo` keys say whether it is there and whether it works. If absent, every
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
8. **Docker in a web container: only for projects with a Docker build
   signal** (`Dockerfile`, `docker-compose.yml`/`compose.yaml`). Measure the
   daemon, not the binary: `docker info`. A web container often ships the
   CLI with no daemon behind it. If `docker info` fails, say so and offer a
   choice. This is a real limitation, not something to route around:

   > ⚠️ **Docker isn't usable in this container** — the `docker` CLI is
   > present but `docker info` can't reach a daemon, so I can't build or
   > verify the image here. Two ways forward:
   > 1. **Work commit now** — save progress on the branch so you can finish
   >    Gate 2 on a machine with a working Docker daemon.
   > 2. **CI-only BUILD** — if a release workflow builds and tests the image
   >    in CI, Gate 2 can pass on that basis (Gate 2, "CI-only").
   >
   > Which do you want?

   This is separate from the test artifact. Either way, nothing merges to the
   default branch until CI has produced a test image from the PR head
   (`GATE_REFERENCE.md`, Gate 2, "Test artifact before merge").

Report the detected environment in the session banner.

**Measure, don't infer, for every environment capability recorded anywhere**
(gate file, banner, handoff). `which <tool>` proves a binary is on `PATH`, not
that it works. Record what was checked and what it returned ("`docker info`:
daemon unreachable", "push to `fix/x` succeeded"), and re-measure every session
and whenever the execution context changes. A capability noted in a prior
session or handoff describes *that* context, not this one.

**Git repo detection — run at session start.** Check if the current working
directory is inside a git repository (`git rev-parse --is-inside-work-tree`).
If yes:

**Every read in steps 1, 1a, 4, 6 and 7 comes from the probe** (top of this
section). Run a command below separately only when the probe printed `ERROR`
for it or it needs something the probe does not read.

1. **Detect and store the repo URL.** Run `git remote -v` to capture the origin
   URL. Store it for the session — this URL is used in clone commands (Termux),
   `git remote add` recovery, release URLs, and PR links. Never assume or
   hardcode a repo URL — always derive from `git remote -v`.

   If no remote is configured:

   > ⚠️ **No remote configured.** This repo has no `origin` remote set.
   > What is the GitHub URL for this project? (e.g. `https://github.com/owner/repo`)

   Store the answer, and include `git remote add origin <url>` in the first
   command block presented to the user.

1a. **Fork check: `origin` must be the fork, never upstream.** Resolve what
   `origin` points at and whether a fork is involved. The probe already ran both
   of these (`gh_repo`, `gh_login`):

   ```
   gh repo view "$(git remote get-url origin)" --json nameWithOwner,isFork,parent,viewerPermission
   gh api user -q .login
   ```

   (Without `gh`, use the GitHub MCP `get_repository` equivalent.) Then there
   are four cases:

   | What you find | What it means | Do |
   |---|---|---|
   | `isFork: true` | `origin` is the fork | Correct. Record `Origin: <owner>/<repo> (fork of <parent>)` and run `gh repo set-default <owner>/<repo>` |
   | `isFork: false`, and `<login>/<repo>` exists with this repo as its `parent` | `origin` is **upstream**, and the user's fork exists | Stop. Fix the remote before any work: `git remote set-url origin <fork-url>`, then `git fetch origin`. Record the fork as above |
   | `isFork: false`, the user is not the owner, `viewerPermission` is below `WRITE`, and no fork exists | They cloned someone else's repo and have nowhere to push | Stop and ask. The user creates the fork on GitHub (or approves `gh repo fork --remote=false`), and then the remote is fixed as above. Never plan a push or PR to the upstream repo |
   | `isFork: false`, and the user owns it or has `WRITE` | An ordinary repo | Nothing to do. Record `Origin: <owner>/<repo> (not a fork)` |

   The user's rule: **the user can go to GitHub directly if they want to go
   upstream.** So the fix is always to repoint `origin` to the fork. Adding an
   `upstream` remote beside it is not a fix. If an `upstream` remote already
   exists, leave it alone and never push to it. Changing `set-url` is a local
   config change, not a ref write: it follows the session's mode (presented in
   manual, run by Claude in semi-autonomous), after the user has seen the
   before and after URLs. Full rule: `SHELL_REFERENCE.md`, "Forks".

   **Re-check after a fix, don't assume it worked.** `git remote -v` and the
   `gh repo view` call must now both name the fork. Record what they returned.

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

6. **Workflow detection: two workflows, both needed, both in the banner.**
   - **Local dev workflow**, which **Gate 2 (BUILD) runs**: `scripts/`,
     `Makefile`/`justfile`/`Taskfile.yml`, `package.json` `"scripts"`,
     `tox.ini`, `noxfile.py`, `gradlew`, `Cargo.toml`, `.csproj`/`.sln`, a
     `docker compose` dev stack, or build steps in `CONTRIBUTING.md`/`README.md`.
   - **CI build check** (on push/PR), which validates **Gate 5's PR**.
   - **CI release workflow** (`on: push: tags:`), which **Gate 6 fires**.

   Name the gate each missing one breaks:

   | Missing | Surface |
   |---|---|
   | Local dev workflow | 💡 **No local build/test workflow found.** Gate 2 can only confirm this builds if there's something to run. How do you build and test this locally? |
   | CI build check | 💡 **No CI build check detected.** PRs are not compiled before merge. Want me to create one? |
   | CI release workflow (Gate 2 not ➖ N/A) | 💡 **No CI release workflow detected.** CI could build and publish artifacts when you push a version tag. Want me to create `.github/workflows/release.yml`? |

   **When both exist, check that they agree.** CI should call the project's
   own scripts (`bash scripts/validate.sh`, `npm test`), not reimplement them
   inline. Otherwise flag it: "⚠️ **CI and local dev have drifted.**
   `validate.yml` runs its checks inline, but `scripts/validate.sh` is what a
   developer runs." To create a workflow, **load `WORKFLOW_REFERENCE.md`** and
   follow its selection procedure, asking every question in one turn. Adapt
   the workflow from the project's real build tooling. A workflow that doesn't
   run the real build goes green without proving anything.

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

**Mode choice — ask every session, and block until it is answered.** This is
the question the skill used to leave to the user to volunteer. In practice
that meant it was never asked, and every session ran manual whether or not
the user wanted that. Now it is asked every time:

- **Ask it in the first message that asks the user anything**, in the same
  `AskUserQuestion` call as the shell, sync and branch questions (steps 2–4)
  and the model-ceiling question (`SKILL.md` §5.2). It is one more question in
  a call that is already being made, so it adds no extra round trip. If there
  is nothing else to ask (a remote container with a clean, current branch),
  ask it on its own. Never skip it.
- **Word it neutrally, with manual first and no recommendation:**

  > **Operating mode for this session?**
  > 1. **Manual:** I present git commands and you run them. I stop between
  >    steps. *Cost:* running the commands costs no tokens, since they run
  >    outside me. Each stop is one more turn when you reply.
  > 2. **Semi-autonomous:** I run git myself after your approval of each
  >    commit. The tag push and any ref deletion are still yours to run.
  >    *Cost:* every command I run is a tool call that resends the whole
  >    conversation. I chain steps to keep that down, and the output lands
  >    in context.

  **The cost line is part of each option and is shown every time.** A picker
  that shows only what a mode does, without its cost, is the wrong question.
  With `AskUserQuestion`, use these option descriptions word for word. Both
  options carry a `Cost:` sentence, and neither is labeled "(Recommended)":

  | Option label | Description, local and Termux sessions | Description, remote container |
  |---|---|---|
  | `Manual` | I present git commands and you run them; I stop between steps. Cost: the commands run outside me, so they cost no tokens; each stop is one more turn. | I run git here only after you confirm each step. Cost: each stop between steps is one more turn, and each turn resends the conversation. |
  | `Semi-autonomous` | I run git after you approve each commit; the tag push and ref deletions stay yours. Cost: every command I run resends the whole conversation; I chain steps to keep that down. | I run git after you approve each commit; the tag push and ref deletions stay yours. Cost: fewer stops, so fewer turns; I chain steps into single calls. |

  In a remote container Claude runs git in both modes (`SKILL.md` §5.8), so the
  difference there is only the number of stops.

- **Nothing selects it for the user.** Not the harness's permission mode, not
  a handoff summary, not a `Mode:` line committed by an earlier session, and
  not silence. If the user answers the other questions and skips this one, ask
  again. The mode stays `unchosen`.
- **Until it is answered:** no edits, no git write executed or presented, and
  no "What are we building?". Read-only session-start checks continue. Once it
  is answered, write it to the state file in the same turn. If the answer is
  semi-autonomous, give the one-message confirmation from `AUTO_MODE.md`
  ("Entering the mode").

**Write the gate state file.** Create `.claude/dev-skills-gates.md` with all
six gates ⬜ pending, the `Origin:` row from step 1a, and `Mode: unchosen`
(format below), and a `Standards:` row for the project standards that apply
(`SKILL.md` §10; `n/a` when none do). Replace `unchosen` with the user's answer as soon as it
arrives. Where the pre-flight hook is installed, it denies every git write
while the row reads `unchosen`. A file committed by an earlier session is
overwritten, not inherited: its `Mode:` line describes that session. On local
sessions add the file to `.gitignore`; on remote containers it is committed
with the work. This file, not the conversation, is the source of truth for gate
state and mode for the rest of the session.

**Format:**

```
# Dev Skills gate state
Track: release sequence
Mode: manual
Origin: owner/repo (not a fork)
Standards: at-rest ✅ SQLite via SQLCipher · TOTP ✅ · 30-day trust ✅ · rescue ✅ · Apprise ➖ declined · compose ✅
Version: 2.12.0
Updated: 2026-09-07

🔢 VERSION    ✅ all refs at 2.12.0
🔨 BUILD      ➖ N/A — skill repo, no build system
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜
```

**Row format: the status symbol and every word the hook checks go on the row's
first line.** The hook and re-derivation both read the ✅/➖/⏳/🚫/⬜ symbol and
annotations like `handoff` or `0 open` line by line, so a check that wraps to
line two reads as absent. Keep line one to the symbol plus a short label, and
put the why and the evidence on indented lines below it.

**Keep the file small.** It is read in full on every gate check and every git
write. Long write-ups belong in the commit message or `CHANGELOG.md`. Close an
absorbed section (a VERSION or SHIP step folding earlier work-commit entries
into a release) in the step that absorbs it. A stale "IN PROGRESS" reads as
open work to the next session.

Then show the gate tracker:

```
Dev Skills v2.36.0 active.

Repo: <repo-name> | Branch: <current-branch> | Remote: <origin url or "NOT SET">
Origin: <✅ fork of <parent> / ✅ not a fork / 🚫 points at upstream — fixing first>
Mode: <manual / semi-autonomous / ⬜ unchosen — answer the mode question first>
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

**Fold the all-clear rows.** `Origin`, `CI`, `Local dev`, `Releases` and
`Skill version` get their own line only when they need attention (⚠️, ❌, 🚫,
🚨). The ones that read ✅ collapse into one line, for example
`Checks: ✅ origin, CI, local dev, releases, skill version`. `Repo`, `Mode`,
`Env` and `Shell` always print. They are this session's settings, not checks.

**Important:** The version shown must match the `version` field in `SKILL.md`'s
frontmatter. If they differ, the skill was not repackaged after a version bump —
surface this to the user.

**Release notes for this version:**
https://github.com/darthrater78/claude-vibe-skills/releases/tag/v2.36.0
**Updates:** checked automatically every session start (above) — this line is
only the fallback if that check was skipped for lack of network access:
https://github.com/darthrater78/claude-vibe-skills/releases

**MCP check — run at session start, every time.** Scan your context for active
MCP tool prefixes (`mcp__<server>__`). Report what's connected:

```
MCP servers active: [list names derived from tool prefixes]
To disable for this session, run the line for each one you don't need:
  /mcp disable <server-1>
  /mcp disable <server-2>
```

Rules for the MCP check:
- **Only name servers whose `mcp__<server>__` tool prefixes are literally in your
  context.** Never infer or guess.
- Distinguish **active** (full tool definitions loaded — expensive, thousands of
  tokens per request) from **deferred** (name-only, schemas loaded on demand —
  cheap). Report deferred as a count only: "N deferred (low overhead)".
- **Give one ready-to-paste `/mcp disable <server>` line per active server**,
  never a bare `/mcp`. `<server>` is the name from the tool prefix. If Claude
  Code does not recognize it, the name shown in the `/mcp` list is the one to
  use (the prefix can swap spaces or hyphens for `_`). `/mcp enable <server>`
  turns one back on, and `/mcp disable all` turns off every server. On a
  Claude Code version without these arguments, fall back to plain `/mcp` and
  toggle the server off in the list.
- If active servers look irrelevant to the work ahead, say so: "Consider
  disabling [name] — not needed for this task: `/mcp disable [name]`."
- `/mcp disable` works without leaving the session. This is the primary
  recommendation for disabling during a session.
- Permanent removal, by how the server was added: CLI-added → `claude mcp
  list` / `claude mcp remove <name>`; project `.mcp.json` → add it to
  `"disabledMcpjsonServers"` in `.claude/settings.json`; desktop app
  connectors → the app's Settings (Claude cannot change these); a clean start →
  `claude --strict-mcp-config --mcp-config '{"mcpServers":{}}'`, which is worth
  a shell alias for users who want a cheap default.
- **After `/mcp` changes, re-check from your own context** (tool prefixes), not
  `claude mcp list`, which returns the full catalog. Give a short before/after:
  `Connections now: X, Y (was: + Z)` and `Estimated overhead: ~12k/turn, down
  from ~40k/turn`.

Then: "What are we building?"

