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
*reported*, and step 0 is the first *decision*. Run this
block once, as a single Bash call, with `B` set to this skill's base
directory, then read every step's answer from its `key=value` output:

```bash
export B="<this skill's base directory>"
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || true
p() { k=$1; shift; if o=$("$@" 2>&1); then echo "$k=$(printf '%s' "$o" | tr '\n' ' ')"; else echo "$k=ERROR $(printf '%s' "$o" | tr '\n' ' ' | cut -c1-200)"; fi; }
p skill_installed bash -o pipefail -c "grep -m1 '^version:' \"\$B/SKILL.md\" | sed 's/version:[[:space:]]*//'"
p skill_latest bash -o pipefail -c "git ls-remote --tags https://github.com/darthrater78/claude-vibe-skills.git | sed 's#.*refs/tags/##' | grep -v '\^{}' | sort -V | tail -1"
p skill_missing bash -o pipefail -c "for f in GATE_REFERENCE SECURITY_GATE SHIP_REFERENCE AUTO_MODE SECURITY_REFERENCE QUALITY_REFERENCE SHELL_REFERENCE WORKFLOW_REFERENCE SECURITY_WINDOWS SECURITY_LINUX SECURITY_ANDROID QUALITY_ANDROID UPDATE_REFERENCE REMOTE_SESSION STANDARDS_REFERENCE ENFORCEMENT DOCKER_TEST LESSONS_REFERENCE WORKFLOW_DOCKER WORKFLOW_WINDOWS WORKFLOW_LINUX WORKFLOW_HOMEASSISTANT WORKFLOW_SCRIPTS WORKFLOW_ANDROID WORKFLOW_PYTHON WORKFLOW_NODEJS; do [ -f \"\$B/\$f.md\" ] || printf '%s ' \$f.md; done"
p env_termux bash -o pipefail -c 'case "${PREFIX:-}" in *com.termux*) echo yes;; *) echo no;; esac'
p env_wsl bash -o pipefail -c 'grep -qi microsoft /proc/version 2>/dev/null && echo yes || echo no'
p repo_root git rev-parse --show-toplevel
p origin bash -o pipefail -c "git remote get-url origin | sed -E 's#://[^/@]+@#://#'"
p branch git branch --show-current
p fetch git fetch --quiet origin
p status git status -sb
p gh_installed bash -o pipefail -c 'command -v gh || echo no'
p gh_repo bash -o pipefail -c 'gh repo view "$(git remote get-url origin)" --json nameWithOwner,isFork,parent,viewerPermission,defaultBranchRef'
p gh_login gh api user -q .login
p default_branch bash -o pipefail -c "git remote show origin | sed -n 's/.*HEAD branch: //p'"
p latest_tag bash -o pipefail -c "git ls-remote --tags origin | sed 's#.*refs/tags/##' | grep -v '\^{}' | sort -V | tail -1"
p untagged bash -o pipefail -c "[ -f CHANGELOG.md ] || { echo no-changelog; exit 0; }; t=\$(git ls-remote --tags origin | sed 's#.*refs/tags/v\{0,1\}##' | grep -v '\^{}'); grep -oE '^## \[?[0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md | grep -oE '[0-9.]+\$' | while read v; do printf '%s\n' \"\$t\" | grep -qxF \"\$v\" || printf '%s ' \"\$v\"; done"
p workflows bash -o pipefail -c 'ls .github/workflows 2>/dev/null || echo none'
p release_workflow bash -o pipefail -c "grep -lE '^[[:space:]]*tags:' .github/workflows/* 2>/dev/null || echo none"
p enforcement bash -o pipefail -c '[ -f "$B/checks/enforce.py" ] || echo checks-file-missing; for py in python3 python "py -3"; do $py -c "import getpass,os,re,sys,tempfile; u=re.sub(r\"[^A-Za-z0-9_.-]\",\"\",getpass.getuser())[:64]; f=os.path.join(tempfile.gettempdir(),\"dev-skills-enforcement-\"+u,os.environ.get(\"CLAUDE_CODE_SESSION_ID\",\"none\")); print(\"active\" if os.path.isfile(f) else \"NOT-ACTIVE\")" 2>/dev/null && exit 0; done; echo NOT-ACTIVE-no-python3'
p leftover_tests bash -c 'command -v docker >/dev/null 2>&1 || { echo no-docker; exit 0; }; docker ps -a --filter label=dev-skills.test --format "{{.Names}} ({{.Status}})"; docker ps -a --filter label=com.docker.compose.project --format "{{.Names}} {{.Label \"com.docker.compose.project\"}} ({{.Status}})" | grep " dev-skills-test" || true'
p local_tracked bash -c 'git ls-files -- .dev-skills-gates.md .claude/dev-skills-gates.md .dev-skills-handoff.md .claude/handoffs HANDOFF.md | tr "\n" " "; echo'
p handoff bash -c 'git log -1 --format="%cs %h" refs/dev-skills/handoff 2>/dev/null || echo none'
p lessons bash -c 'git log -1 --format="%cs" refs/dev-skills/lessons 2>/dev/null || echo none'
p local_dev bash -o pipefail -c 'for f in scripts Makefile justfile Taskfile.yml package.json tox.ini noxfile.py gradlew Cargo.toml *.sln *.csproj Dockerfile compose.yaml docker-compose.yml; do [ -e "$f" ] && printf "%s " "$f"; done; echo'
```

**On Windows the probe runs in the Bash tool, which is Git Bash.** If Claude
Code has no Bash tool here (Git for Windows missing), the probe and the
enforcement checks can't run: say so first, with the fix (install Git for
Windows, or set `CLAUDE_CODE_GIT_BASH_PATH`), and run the session on
instructions only until it's fixed.

Reading it:

- **`key=ERROR …` is a finding, not a blank.** Every key prints every time, and
  a failed command prints `ERROR` with its message. It is never skipped. Handle
  it the way the step it answers says to, for example
  `skill_latest=ERROR` → "version check skipped — no network access".
- **Git keys with `ERROR` when `repo_root=ERROR`** mean no git repo. The git
  steps do not apply.
- **`gh_installed=no` or `gh_repo=ERROR`** → use the GitHub MCP equivalents
  (`REMOTE_SESSION.md`, item 3) for step 1a, and for anything the probe could
  not answer.
- **`untagged` lists changelog versions with no remote tag.** The version being
  built right now shows there too, and that is expected. Step 7 is about the
  versions before it.
- **`origin` has any credentials in the URL stripped** (`https://user:token@…`
  becomes `https://…`) so a token never lands in the transcript.
- **`enforcement=active`**: the checks ran on this very probe. Anything else
  (`NOT-ACTIVE`, `checks-file-missing`) is `⚠️ Hook enforcement: not active — instructions still apply` in
  the banner, with the reason.
- **`handoff` is the last session's handoff** (`SKILL.md` §5.6): a date, or
  `none`. When there is one, read it (`git show
  refs/dev-skills/handoff:HANDOFF.md`) before the questions, and say in one
  line what it picks up. It is replaced when this session writes its own.
- **`lessons` is a date only in the skill's own repo**, when other sessions
  recorded lessons for it: read `LESSONS_REFERENCE.md`, "In the skill's repo".
- **`leftover_tests` lists test containers an earlier session left behind**
  (`ENFORCEMENT.md`, A12). The banner shows `⚠️ Leftover test containers: N`,
  and before any new work, present a ▶️ RUN THIS block that removes them
  (`docker rm -f …`) and their temp mount folders
  (`docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}'` lists them).
- **The probe only reads, plus one `git fetch`**, which updates the
  remote-tracking refs and nothing in the working tree. So `status`'s
  ahead/behind counts are current, and step 3 asks only when they say behind.

Steps 2 and 3 are questions for the user, not reads. Every step below still
applies: the probe changes how many calls it takes, never what gets checked.

**Self-check:** `skill_missing` from the probe. If it names any file, warn
immediately:

> ⚠️ **Skill self-check failed:** [filename] not found in [base directory].
> The security/quality gate cannot run properly without it.

**Version check — every session, reported before anything else**, even with no
git repo in the project (it checks the skill's own upstream).

1. **Installed version** — the `version:` field in this skill's own
   `SKILL.md` frontmatter (e.g. `2.19.0`).
2. **Latest published version** — `skill_latest` from the probe, read from the
   upstream remote (never a cached clone, never a number from memory). On
   `ERROR`, say once in the banner "⚠️ version check skipped — no network
   access" and continue.
3. **Compare** (strip the leading `v`, semver order).
   - **Current:** fold a single confirmed line into the banner — no separate
     callout needed.
   - **Behind:** treat it like a failed security gate, not an FYI. It is
     **the first thing in the first message**, above any greeting and the
     banner. **Read `UPDATE_REFERENCE.md` first**: it has the bracketed
     callout, the options the install location allows, and the
     `⚠️ outdated` marker every later tracker carries if the user continues.

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

**Remote container: read `REMOTE_SESSION.md`** from this skill's base
directory before step 1. It changes the clone, the shell and sync questions,
`gh` (GitHub MCP equivalents), where the state file lives, the tag carve-out
and Docker. Local and Termux sessions skip it.

Report the detected environment in the session banner.

**Measure, don't infer, for every environment capability recorded anywhere**
(gate file, banner, handoff). `which <tool>` proves a binary is on `PATH`, not
that it works. Record what was checked and what it returned ("`docker info`:
daemon unreachable", "push to `fix/x` succeeded"), and re-measure every session
and whenever the execution context changes. A capability noted in a prior
session or handoff describes *that* context, not this one.

**Git repo steps — when `repo_root` is not `ERROR`.** **Every read in steps 1, 1a, 4, 6 and 7 comes from the probe** (top of this
section). Run a command below separately only when the probe printed `ERROR`
for it or it needs something the probe does not read.

1. **Store the repo URL** from the probe's `origin` for the session: clone
   commands (Termux), `git remote add` recovery, release URLs and PR links.
   Never assume or hardcode one.

   If no remote is configured:

   > ⚠️ **No remote configured.** This repo has no `origin` remote set.
   > What is the GitHub URL for this project? (e.g. `https://github.com/owner/repo`)

   Store the answer, and include `git remote add origin <url>` in the first
   command block presented to the user.

1a. **Fork check: `origin` must be the fork, never upstream.** Resolve what
   `origin` points at and whether a fork is involved, from the probe's `gh_repo`
   and `gh_login` (without `gh`, use the GitHub MCP `get_repository` equivalent). **The
   common case:** `isFork: false`, and the owner in `nameWithOwner` is the
   `gh_login` user, so no fork of it can exist. Record `Origin: <owner>/<repo>
   (not a fork)` and move on. **Anything else** (a fork, someone else's repo,
   even one you can write to): read `SHELL_REFERENCE.md`,
   "Forks", for the four cases and the fix, before any work.

   **Re-check after a fix, don't assume it worked.** `git remote -v` and the
   `gh repo view` call must now both name the fork. Record what they returned.

2. **Shell environment detection.** *Local and Termux sessions only. Remote
   containers never ask it, not even for the tag block (`REMOTE_SESSION.md`,
   item 4).* Ask the user which shell they work in. It sets how every presented
   command is formatted for the rest of the session:

   > **Which shell will you be running these commands in?**
   > 1. Windows PowerShell
   > 2. Linux PowerShell (pwsh)
   > 3. Git Bash (Windows)
   > 4. Termux (Android)
   > 5. macOS Terminal (zsh/bash)
   > 6. Linux Terminal (bash/zsh)
   > 7. WSL (Windows Subsystem for Linux)

   Store the answer for the rest of the session — don't ask again.

3. **Offer to sync with origin, only when `status` says behind.** Up to date
   or only ahead: say "in sync with origin" in the banner and don't ask. When
   behind, present the option before any work begins, formatted for the user's
   detected shell (Section 5.8):

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

7. **Unfinished release check — did the last release actually ship?** A session
   can die between merge and tag (a reclaimed container, a usage limit, a
   `403` on the tag push), and nothing later goes looking for it. The probe's `untagged` key compares `CHANGELOG.md` versions against the
   remote's tags. Section 8's end-of-session check only runs if the session
   winds down, so this start-of-session check is the one that always runs.

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

**Enforcement disclosure — every session, before the mode question.** Read
only `ENFORCEMENT.md`'s "At session start" section (`sed -n '/^## At session
start/,/^## The checks/p'`, about 2KB of a 12KB file; the rest loads when a
check blocks) and follow it: the short
disclosure, then **"Keep the enforcement checks on for this session?"** in the
same `AskUserQuestion` call as the mode question. It is all or nothing, never
defaulted, and asked again if skipped.

**Mode choice — ask every session, and block until it is answered.**

- **Ask it in the first message that asks the user anything**, in the same
  `AskUserQuestion` call as the others. If there is nothing else to ask, ask
  it on its own. Never skip it.
- **One call when it fits, and it usually does.** A call holds at most four
  questions. In order: enforcement, mode, shell (local and Termux), then
  whichever of model ceiling (only above Sonnet, `SKILL.md` §5.2; the answer
  goes on the `Model:` row and covers the session), branch
  (only on the default branch) and sync (only when behind) apply. Only when
  more than four apply does the rest go in a second call. Nothing is edited
  until every question has an answer.
- **Word it neutrally, with manual first and no recommendation:**

  > **Operating mode for this session?**
  > 1. **Manual:** I present git commands and you run them, one block per
  >    decision. *Cost:* running the commands costs no tokens, since they run
  >    outside me, and you never need to reply just to say "done".
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
  | `Manual` | I present git commands and you run them, one block per decision. Cost: the commands run outside me, so they cost no tokens; you never need to reply just to say "done". | I run git here only after you confirm each step. Cost: each stop between steps is one more turn, and each turn resends the conversation. |
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

**Write the gate state file.** Create `.dev-skills-gates.md` in the repo root with all
six gates ⬜ pending, the `Origin:` row from step 1a, and `Mode: unchosen`
(format below), and a `Standards:` row for the project standards that apply
(`SKILL.md` §10; `n/a` when none do). Replace `unchosen` with the user's answer as soon as it
arrives. The checks deny git writes while it reads `unchosen`. **Edit this
file with the Write/Edit tools, never the shell**, so the checks can show the
user each line that declines enforcement, approves host networking or waives
a finding (`ENFORCEMENT.md`, B5). **It lives in the repo root, not in
`.claude/`:** Claude Code asks before every edit under `.claude/` whatever the
permission mode, so a gate file there cost the user a prompt per gate
(2.39.1 and earlier). A file committed by an earlier session is
overwritten, not inherited: its `Mode:` line describes that session. On local
sessions add `.dev-skills-gates.md` and `.dev-skills-handoff.md` to
`.gitignore` and keep them untracked, so neither can ever block a commit, PR,
checkout or pull (the handoff is committed to its own local ref instead). An
old `.claude/dev-skills-gates.md` is never read again; leave it alone (deleting
it is an edit under `.claude/`, so it would prompt) and tell the user once that
they can delete it. **`local_tracked` naming paths on a local session** means
an earlier session committed them. A tracked gate file blocks `git checkout`
whenever a session rewrites it (2.28.0–2.39.0 committed it): untrack it. For
older handoffs (`.claude/handoffs/`, `HANDOFF.md`), ask once whether to move
the newest into `refs/dev-skills/handoff` and untrack them all, since the
user may want them kept in the repo; their answer stands. Untrack with `git rm -r --cached <path>` plus the
`.gitignore` line, staged with the session's first commit and named in its
approval. **Once that
commit reaches the default branch, every other clone meets it once:** a pull
deletes that clone's copy, or refuses with "would be overwritten" if the
file has local edits. Say so in the approval. The fix is `git stash push
<path>` (or discard it) before pulling. Nothing durable is
lost, since each session rewrites the file. On remote
containers it is committed with the work. This file, not the conversation, is the source of truth for gate
state and mode for the rest of the session.

**Format:**

```
# Dev Skills gate state
Track: release sequence
Mode: manual
Model: Sonnet 5 (within ceiling)
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

**Row format: the status symbol and every word the checks read go on the row's
first line.** The checks and re-derivation both read the ✅/➖/⏳/🚫/⬜ symbol and
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
Dev Skills v2.40.0 active.

Repo: <repo-name> | Branch: <current-branch> | Remote: <origin url or "NOT SET">
Origin: <✅ fork of <parent> / ✅ not a fork / 🚫 points at upstream — fixing first>
Mode: <manual / semi-autonomous / ⬜ unchosen — answer the mode question first>
Hook enforcement: <✅ active (ENFORCEMENT.md) / ⚠️ declined — instructions still apply / ⚠️ not active — <reason>; instructions still apply>
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
`Env`, `Shell` and `Enforcement` always print. They are this session's settings, not checks.

**Important:** The version shown must match the `version` field in `SKILL.md`'s
frontmatter. If they differ, the skill was not repackaged after a version bump —
surface this to the user.

**Release notes for this version:**
https://github.com/darthrater78/claude-vibe-skills/releases/tag/v2.40.0
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

