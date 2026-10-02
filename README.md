# claude-vibe-skills

One skill for disciplined vibe coding. Claude doesn't commit without your
say-so, doesn't ship without walking the gates, and can't quietly skip either.

```
🔢 VERSION  →  🔨 BUILD  →  🔒 SECURITY  →  📄 DOCS  →  📦 RELEASE  →  🚀 SHIP
```

**[⬇ Download `dev-skills.skill`](../../releases/latest/download/dev-skills.skill)** — current version `v2.46.0`

[GitHub repo](https://github.com/darthrater78/claude-vibe-skills) · [Release notes for v2.46.0](https://github.com/darthrater78/claude-vibe-skills/releases/tag/v2.46.0)

---

## Contents

- [What it does](#what-it-does) — the four rules
- [Enforcement checks](#enforcement-checks) — what's actually checked, full disclosure, and how to decline
- [What's new](#whats-new) — the last few releases
- [What it looks like](#what-it-looks-like) — a session, abridged
- [Install](#install) — claude.ai, Desktop, CLI, web
- [The six gates](#the-six-gates) — what each one checks
- [Two tracks](#two-tracks) — why a work commit isn't a release
- [Manual and semi-autonomous mode](#manual-and-semi-autonomous-mode) — who runs the commands
- [How gates are enforced](#how-gates-are-enforced) — the state file, and why memory isn't trusted
- [Execution environments](#execution-environments) — local vs. container vs. Termux
- [Workflow detection](#workflow-detection-local-dev-vs-ci) — local dev vs. CI
- [Cost discipline](#cost-discipline) — what's automatic, what you have to ask for
- [Project standards](#project-standards) — encryption at rest, login protections, main-page links, Apprise, compose quickstart
- [Audit mode](#audit-mode) · [Shortcut detection](#shortcut-detection) · [What's inside](#whats-inside) · [For maintainers](#for-maintainers)

---

## What it does

**1. Commits require approval.** Claude never runs `git commit`, `git push`, or
`gh pr create` without your explicit say-so. No surprise commits after a single
edit. A vague "ok" doesn't count, and neither does a hook telling Claude the
tree is dirty. This is the one rule [semi-autonomous
mode](#manual-and-semi-autonomous-mode) doesn't relax.

**2. All work happens on branches.** Never directly on `main`/`master`. At
session start the skill finds the repo, offers to sync with origin, and flags
you if you're sitting on the default branch.

**3. Gates run before anything ships.** A work commit needs the security gate
and your approval. Anything that bumps a version, builds an artifact, tags, or
publishes runs all six, in order. **Presenting a git command for you
to paste counts as running it** — the same pre-flight fires either way.

**4. Security and quality get scanned.** After every build, a full scan checks
for hardcoded secrets, injection vectors, spaghetti code, N+1 queries, and
more. Critical and High findings block the release.

---

## Enforcement checks

**Most of this skill is instructions, which Claude follows and nothing
checks.** Until 2.37.0 that was true of everything on most machines: the old
optional hook (`hooks/gate-preflight.sh`) had to be installed by hand, nothing
installed it, and nothing said it was missing. A review found it had also
weakened: prefixed commands, pushes to the default branch and decoy ✅ lines
all got through.

Since 2.37.0 the **enforcement checks ship inside the skill**
(`checks/enforce.py`), and Claude Code turns them on by itself when the skill
loads, through the `hooks:` block at the top of `SKILL.md`. There's nothing
to install.

**What they are, in full disclosure:**
- **A small Python 3 program that Claude Code runs on its own**: before
  Claude runs a command or edits a file, before Claude ends a reply, and after
  you answer Claude's questions.
- **They only read** the command, the file edit, the reply, your answers, the
  project's gate file, and a compose file about to be started. They answer
  allow, deny, ask you, or "fix the reply". **They never run a command.** The
  only thing they write is a status marker in the temp folder, so the banner
  can say whether they're on.
- **Every session starts by telling you**, then asking: keep them on, or
  decline for this session. It's all or nothing. You confirm a decline in
  Claude Code's own permission dialog, so Claude can't switch them off by
  itself.
- **The banner always shows the status:** `Hook enforcement: ✅ active`,
  `⚠️ declined`, or `⚠️ not active` with the reason
  (Python 3 missing, an incomplete install, or a Claude Code version that
  doesn't register skill checks).
- **When they can't run, they block** git, gh and docker commands rather than
  letting them through unchecked.
- **One caveat, verified and disclosed:** the checks find their own folder
  through `CLAUDE_PLUGIN_ROOT`, which Claude Code sets for skill checks
  (verified on 2.1.281) but documents only for plugins. If a future version
  changes that, the checks fail closed and the banner says hook enforcement
  is not active.
- **Without the hooks, the guardrails are still there.** Every gate,
  approval and rule in the skill still applies: Claude follows them as
  instructions. What's missing is the automatic check that it did.

| Group | What's checked |
|---|---|
| **Commands Claude runs** | Git writes need their gates (strict: only the gate's own row counts), including behind `env`/`sudo`/`bash -c`, any write that lands on the default branch, a dev version (`-dev`, `-rc`, …) reaching the default branch, auto-merge, release edits, PR branch updates, commits made by `merge`/`cherry-pick`/`revert` or by pulling another branch, and git aliases that expand to any of these · no git write before the mode is chosen · tags and ref deletions are always yours · test containers publish on your LAN IP only (no `127.0.0.1`, bare ports or Docker-bridge IPs) · host networking only with your recorded permission · no test container with a restart policy mounting from `/tmp` (a reboot turns it into a root-owned folder that breaks Claude Code) · temp-folder mounts are never root-owned (created first, container runs as you) · test containers are labeled, and the next session start finds any left behind |
| **Files Claude edits** | Gate-file lines that decline enforcement, approve host networking or waive a finding go to you as a permission prompt (gate rows and the mode line don't), as do edits to settings files and the installed checks. Staging the gate file on a local session is blocked · workflow edits that add an unpinned action, a `${{ }}` inside a `run:` script or a checkout that keeps its credential are blocked, and ones that drop the `permissions:` block or a job's timeout, or run `./gradlew` in a job that doesn't validate the wrapper, ask you |
| **Claude's replies** | No loopback or bridge test URLs · command blocks you're handed obey the same gates as executed ones · every run block is labeled `▶️ RUN THIS`, with START/END markers, no `cd`, the tracker above and "No need to reply" below |
| **Your answers** | A skipped question gets flagged to Claude: re-ask it, and don't pick a default |

Every check, with exactly what it blocks and lets through, is in
[`ENFORCEMENT.md`](skills/dev-skills/ENFORCEMENT.md). Each one has test cases
in `scripts/test-checks.py`, run by `validate.sh` and CI, so a check can't
quietly weaken again. `scripts/audit-workflows.py` applies the workflow
rules to this repo's own workflows and every template on each run too, and
`scripts/check-pins.py` checks weekly that every action pin still matches its tag. `scripts/audit-repos.py` applies the same workflow rules weekly to every public repo you own (private ones too with an `AUDIT_TOKEN` secret), so a repo no session opens is still audited. **What they can't catch:** judgment (the track, N/A
reasons, severity, docs accuracy), whether your "yes" meant commit approval,
and what you actually paste. Those stay instructions. To run the checks in
every session, including ones that don't load the skill, see
[`hooks/README.md`](hooks/README.md).

---

## What's new

The last few releases. Full detail in [CHANGELOG.md](CHANGELOG.md).

- **No more Sonnet ceiling.** The model is your choice; the skill no longer
  asks about it. Savings come from how sessions are worked and from loading
  less: Gates 1 and 5 now load only on the release track. *(2.46.0)*
- **Ten recorded lessons applied.** A TLS 1.2 floor, a UI visual pass,
  README screenshots checked before the release PR, CI that skips heavy jobs
  on docs-only changes, one Docker test login per session, and more. *(2.46.0)*
- **Far fewer gate-file prompts.** A shell command that names the gate file
  no longer asks just for naming it, which prompted on nearly every session.
  It asks only when it deletes the file or writes a waiver, an enforcement
  decline or a host-network approval, the same rule as an edit. *(2.45.2)*
- **Open Medium and Low findings don't block work commits.** A SECURITY row
  of `⏳ open — 0 Critical, 0 High, …` lets you commit and push a feature
  branch; PRs, merges and releases still need every finding closed. *(2.45.2)*
- **Docs-only merges skip the test artifact, with your OK.** On a work-commit
  merge, `test artifact: n/a — no app code changed` replaces the artifact
  and handoff; you confirm it once when it's added. *(2.45.2)*
- **Install instructions for every surface, and synced installs checked.** The
  install section covers the hand install on Windows, Python 3 for the checks,
  installing one way only, and a tested answer on whether a copy synced from
  claude.ai enforces like a hand-installed one (it does). *(2.45.2)*
- **Idle repos get audited, and dev versions stay off the default branch.**
  A weekly job checks every repo's workflows and keeps one issue up to date.
  Pushing or merging a pre-release version (`-dev`, `-rc`, …) onto the default
  branch is blocked. Every job that runs `./gradlew` must validate the wrapper
  first. Gate-file edits stop re-asking for approved waivers. *(2.45.0)*
- **Aliases and pulls can't slip past the gates.** A git alias (inline or in
  your git config) is expanded before it's checked, and pulling another branch
  into yours, which writes a merge commit, needs the same gate as `git merge`.
  `gh pr update-branch` is gated like its API form. *(2.44.1)*
- **No more ungated merges, and less reloading.** The checks now catch
  auto-merge, PR branch updates, release edits, `gh api` merges and contents
  writes, and `git merge`/`cherry-pick`/`revert`. Reference files load once
  per session instead of before every gate and command block, and the cost
  guidance matches current pricing and prompt caching. *(2.44.0)*
- **Templates are linted and their pins checked.** CI runs actionlint on every
  template workflow, and a weekly job confirms each action pin still matches
  its tag and flags newer releases, since Dependabot can't see pins inside
  Markdown. Dependabot and dev-release guidance moved to their own files, so a
  workflow audit loads 10KB less. *(2.43.0)*
- **Existing workflows get re-audited, not just new ones.** Every Gate 3 now
  runs the workflow checklist against every file in `.github/workflows/`
  and records which skill version it audited against, so a checklist that
  grows re-checks everything. A fork's inherited workflows start unaudited.
  The checklist adds secrets decoded before a dependency install, a missing
  `permissions:` block, branch-pinned actions and Gradle wrapper
  validation, and the audit offers dependency review, CodeQL, secret
  scanning and build provenance. Docker images are scanned with Trivy
  before a version tag points at them. New template for Capacitor/Ionic apps.
  A missing or incomplete `dependabot.yml` is an audit finding. *(2.42.0,
  2.42.1)*

Earlier releases, back to 2.1.0, are in [CHANGELOG.md](CHANGELOG.md).

---

## What it looks like

Trying to skip ahead surfaces the tracker instead of complying:

```
you ▸ just push it

     🔢 VERSION    ✅ v2.46.0 — all refs agree
     🔨 BUILD      ✅ scripts/validate.sh green
     🔒 SECURITY   ⬜ not run against the current diff
     📄 DOCS       ⬜
     📦 RELEASE    ⬜
     🚀 SHIP       ⬜

     Security hasn't run on these changes. Doing that first.
```

Gate state lives in a file, not in Claude's memory:

```
# .dev-skills-gates.md
Track: release sequence
Mode: manual
Origin: you/your-repo (not a fork)
Version: 2.46.0

🔢 VERSION    ✅ all refs at 2.46.0; prev v2.45.2 tagged on remote
🔨 BUILD      ➖ N/A — skill repo, no build system
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜
```

Marks mean: ✅ passed · 🚫 blocked · ⏳ in progress · ⬜ pending · ➖ N/A.

---

## Install

Download `dev-skills.skill` from the [latest release](../../releases/latest),
then install it **one** of these ways. Don't install both: in the CLI the
hand-installed copy takes the `/dev-skills` name, the synced copy becomes
`anthropic-skills:dev-skills`, and both can end up loaded in one session.

| Where | How |
|---|---|
| **[claude.ai](https://claude.ai)** (recommended) | **Customize** → **Skills** → upload the `.skill` file. It syncs to Claude Desktop, Claude Code on the web, and the Claude Code CLI in sessions signed in with that account (CLI 2.1.273 or later). |
| **Claude Code CLI, by hand** | Unzip into your personal skills folder (below). Use this when your CLI sessions don't sync: signed in with an API key, on Bedrock or Vertex, or with sync turned off. |
| **One repo only** | Commit the unzipped folder to the repo's `.claude/skills/dev-skills/`. Cloud sessions load it from there too. |

**Enforcement needs Python 3**, and on Windows, Git for Windows (the checks
run in Git Bash). Without them the skill still works as instructions, the
banner says `⚠️ not active`, and git, gh and docker commands are blocked
rather than let through unchecked. See [Enforcement checks](#enforcement-checks).

Hand install. The `.skill` file is a zip with no top-level folder, so unzip it
into a folder named `dev-skills`:

```bash
mkdir -p ~/.claude/skills/dev-skills
unzip -o dev-skills.skill -d ~/.claude/skills/dev-skills/
```

```powershell
Copy-Item dev-skills.skill dev-skills.zip
Expand-Archive dev-skills.zip "$HOME\.claude\skills\dev-skills" -Force
```

If you set `CLAUDE_CONFIG_DIR`, use that folder in place of `~/.claude`.

**Synced and hand-installed copies enforce the same way.** Claude Code
registers a synced skill's frontmatter hooks just as it does a local skill's
(tested on Claude Code 2.1.284). The limits on synced skills (no `!` commands,
no `@` attachments and no placeholder substitution in the skill's text) don't
touch anything this skill uses. Start a fresh session after you install or
update, and check the banner reads `Hook enforcement: ✅ active`.

**Updating:** when a session finds your copy out of date, it offers to
install the new release for you or to give you a one-line command (bash or
PowerShell). Either way the whole skill is replaced from the release file,
and nothing changes if the download doesn't match the expected version.
Copies synced from claude.ai have to be re-uploaded there.

The skill activates on its trigger phrases ("ship it", "commit", "audit",
"just push it", …) or when you invoke `/dev-skills` directly.

---

## The six gates

### Gate 1 — Version 🔢

No build starts until every version file (`package.json`, `pyproject.toml`,
`VERSION`, …) is bumped, consistent, and includes the repository URL. Greps the
whole project for hardcoded version strings — source, UI templates (XAML,
HTML), window titles, "About" dialogs, config files. Every match must be
updated. **Every project's main page (the README's top section, and the app's
main page when it has a UI) links to the GitHub repo and the current release
notes, without exception.** Anything else that shows a repo link must link the
release notes too.

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
be found. A third state, **CI-only**, covers a build system that exists and is
correct but structurally can't run in this environment (no SDK, a blocked
registry) — permitted only with the obstacle stated concretely and everything
checkable locally actually checked. *(2.23.0)*

For compiled outputs — Docker images, Windows `.exe`, Android `.apk` — a
passing smoke test isn't the end of the gate: Claude must also offer a way to
try the real build by hand (a local download folder, or `docker load`/`docker
run` instructions), every time the build changes. The offer can be declined,
never skipped silently. Scope is environment-gated: full offer on a local
Linux session, `.exe`/`.apk` only (no Docker) on a local Windows session.
*(2.22.0)* **Nothing merges to the default branch without a test artifact**
built from the exact commit being merged, in every environment: remote
container and Termux sessions get theirs from CI (a PR build artifact or a
dev pre-release) instead of skipping it. Every Docker test run gets a freshly
generated throwaway username and password, shown to you with the run
command. *(2.33.0)* The container is published on the network, and its URL
uses the host's LAN IP (checked to answer), never `127.0.0.1`. It binds to
that private IP only, never a public interface. *(2.36.1)* That IP is read
from the default route (a Docker bridge such as `172.17.0.1` is rejected), the
app inside listens on `0.0.0.0`, and `docker port` must show the LAN IP before
the URL is handed over. *(2.37.0)* The login
is repeated at the bottom of every message after the test container is
started, rebuilt or restarted, never just "see above". *(2.34.0)* The
[enforcement checks](#enforcement-checks) hold the offer to this: a BUILD gate
marked ✅ with no `handoff` annotation on its tracker line, in a repo with a
Docker/.exe/.apk build signal, is denied — reading the tracker row's full
text, not just its first line, so a wrapped annotation isn't misread as
missing. *(2.23.0, 2.25.0, 2.37.0)*

A web/remote container with the Docker CLI but no reachable daemon is a
separate, earlier problem than the handoff offer: session start measures
`docker info`, not just `which docker`, and offers a real choice for a
Docker-build project — commit as work-in-progress to finish on a machine
with a working daemon, or the CI-only path above. Any container started for
testing must be torn down once it's served its purpose. A build/test run
only counts as this gate's evidence if the working tree was unchanged for
its full duration. *(2.25.0)*

### Gate 3 — Security & Quality 🔒

Mandatory after every build. Loads the cross-platform reference files, plus
whichever platform-specific files match the detected project environment.

**Security:** hardcoded secrets · SQL injection · command injection · disabled
TLS · path traversal · missing auth · weak crypto · unsafe deserialization ·
dependency auditing (typosquatting, unpinned versions, known CVEs, a runtime
or LTS line past end of support, an LTS project moved off LTS).

Plus platform-specific rules, loaded only when that platform is detected:

- **Windows** — UAC elevation, PowerShell injection, UNC path attacks, DLL
  hijacking, registry ACLs, unquoted service paths, code signing
- **Linux** — SUID misuse, container security (host networking only with your permission), symlink races, systemd hardening
- **Android** — exported components, WebView RCE, Intent spoofing, insecure storage

**Code quality:** deep nesting · god functions · circular dependencies · hidden
side effects · N+1 queries · wrong data structures · string concat in loops ·
blocking I/O · unbounded caches · missing indexes · premature abstraction ·
container dependency drift (Dockerfiles hardcoding packages instead of
installing from dependency files; imports missing from declared dependencies).

**Project standards:** every scan also checks the [project standards](#project-standards)
you decided on: encryption at rest, the login protections, and Apprise.

Critical and High must be fixed before anything else happens. Medium and Low
don't stop a work commit, but every finding has to be fixed, waived by you, or
withdrawn before the release track runs. **Passes at 0 open findings (0
Critical, 0 High).**

### Gate 4 — Docs 📄

Checks that README/CHANGELOG has an entry for this version, new features are
documented, removed features leave no stale references, architecture docs
match the code, and README screenshots and walkthroughs still match the app.

### Gate 5 — Release 📦

Checks prerequisites first (GitHub remote exists, default branch pushed, `gh`
authenticated), then creates a feature branch, gets commit approval, pushes,
and opens a PR with release notes. Never falls back to direct commits on main —
if the infrastructure isn't set up, it blocks and helps you fix it.

### Gate 6 — Ship 🚀

Merges the PR, confirms the merge and its CI landed before ever presenting the
tag block, tags the merge commit, creates a GitHub release with artifacts,
then verifies all four post-ship conditions (tag on remote — pointing at the
merge commit, not just present by name — release exists, PR merged, assets
attached). Shows the full ship summary and waits for explicit confirmation —
"yeah" is not enough; type "ship" or "confirm ship". In semi-autonomous mode
that confirmation is the full pre-tag report.

The tag push itself always comes back to you — see
[Execution environments](#execution-environments).

Before a tag exercises a release-workflow step that's never actually run in
this repo (a first registry login, a first signing step), it's worth
dry-running that step locally against the built artifact first — cheaper
than discovering it fails during a live release. On a local session the gate-state
file is gitignored and never committed, so switching branches never trips over
it. In a remote container it ships inside the release PR with SHIP ⏳, and the
SHIP ✅ line rides in the *next* release's PR. There is never a PR whose only
content is tracker bookkeeping. *(2.25.0, 2.28.0, 2.39.1)*

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
| **Release sequence** | anything with publishing intent: a version bump, an artifact, a tag, or a publish | all six, in order |

A work commit never becomes a release by accident. If the operation bumps a
version, tags, or publishes, it's a release sequence — regardless of it being
called "just a quick push".

The test is *publishing intent*, not the branch a commit lands on. A merge
to the default branch that bumps nothing, tags nothing, and publishes
nothing — a tracker-bookkeeping commit, a docs typo fix — is still a work
commit, with RELEASE/SHIP marked ➖ N/A and the reason stated. Treating every
default-branch merge as release-track by default is what turns a five-line
housekeeping commit into a six-gate ceremony. (The [enforcement
checks](#enforcement-checks) are stricter here: see their table.) When a
repo's own convention
here is genuinely unclear, the skill asks once at session start rather than
discovering it mid-PR.

Gates apply by default to any session that modified a tracked file. There is no
"too small to bother" exemption. A gate leaves the workflow exactly one way: by
being marked ➖ N/A for a *structural* reason (no build system, for example),
stated out loud on the tracker.

---

## Manual and semi-autonomous mode

**You pick the mode at the start of every session.** It is one of the
session-start questions, manual listed first and neither recommended, and
nothing proceeds until you answer. No edits and no git writes happen before
then, and the [enforcement checks](#enforcement-checks) deny git writes while
the gate file reads `Mode: unchosen`.

**Manual mode** is the behavior this skill has always had. Claude hands you the
git commands, you run them, and the tag push comes back to you no matter where
the session is running. Each stop costs a model request, so Claude keeps them
few: one chained block per decision, with the CI checks inside the chain. A
release is two blocks: commit → push → PR, then (after you've looked at the
PR) merge → tag. Every block is labeled `▶️ RUN THIS`, starts and ends with
marker lines, prints ✅ or ❌ at the end, and has no `cd`. You never need to
reply just to say "done": your next message starts with a check of the
result, and a failed block is raised before anything else. A timer wouldn't
save anything, because its wakeup costs the same request. *(2.37.0)*

**Semi-autonomous mode** is chosen per session, either at that question or
later by asking for it: "auto mode", "semi-autonomous mode", "take it from
here". It changes *who runs
most of the commands* — not what has to be true before they run, and not the two
ref operations GitHub denies Claude.

| | Manual | Semi-autonomous |
|---|---|---|
| **Commit approval** | required, every commit | **required, every commit** |
| Commit, branch push, PR | presented for you to run | Claude runs them |
| PR merge | presented | Claude runs it once the PR's checks pass, without `--delete-branch`; CI on the merge commit is confirmed before the tag |
| **Tag push** | always yours | **always yours — with a full report above the block** |
| **Branch / tag deletion** | always yours | **always yours** |
| Release publish, notes, verification | presented / Claude | Claude runs them |
| Command blocks | the normal way commands arrive | the tag and ref deletions, plus anything that fails |
| The six gates and the pre-flight | enforced | enforced, identically |
| Questions and judgment calls | yours | still yours |

**Two checkpoints, not none.** A release in semi-autonomous mode stops twice:
once at the commit, once before the tag.

**Checkpoint 1 — the commit.** The version-bump confirmation and the
release-notes review fold in here, presented together:

```
Ready to commit — this is the one approval for the release.

Version:  2.25.0 → 2.26.0 (MINOR — one feat, no breaking change)
Commit:   feat(skill): add semi-autonomous mode
Changes:  SKILL.md +118, GATE_REFERENCE.md +96, README.md +54 …
Gates:    🔢 ✅ · 🔨 ✅ · 🔒 ✅ 0 Critical / 0 High · 📄 ✅ · 📦 ⬜ · 🚀 ⬜
Release notes (v2.26.0):
  - …

On your yes: commit, push, open the PR, and merge it once CI is green. Then
I'll come back with a full report and the tag block for you to run.
```

That yes covers the sequence it describes and nothing else — if more commits
land or the notes change, you get asked again.

**Checkpoint 2 — the tag.** The tag is the action that publishes, and **you run
it** — in this mode exactly as in manual, because Claude's credentials get
`403`'d on tag refs and no mode can grant what the remote withholds. What this
mode adds is what arrives *with* the block: Claude reports **everything** it did
since your approval — commits with SHAs, every push, the PR and what happened on
it, every CI run and its conclusion, the merge commit, each gate with the
evidence behind it, the version guard, and anything that failed, was retried, or
went differently than described at the commit. Then it asks:

```
Ready to tag v2.26.0 — full report of everything since your commit approval.

Commits (3)
  257b224 feat(skill): add semi-autonomous mode — 6 files, +412/−38
  …
Pushes:  feature/x → origin, 3 times (no force, no rewrite)
PR:      #48 — opened, 2 review comments addressed, merged as c3a49f7
CI:      validate ✅ 257b224 · ✅ 9ab0e12 · ✅ merge commit c3a49f7
         (one earlier ❌ on 4c1a88e — shellcheck SC2086, fixed in 9ab0e12)
Gates:   🔢 ✅ · 🔨 ✅ · 🔒 ✅ 0 Critical / 0 High · 📄 ✅ · 📦 ✅ PR #48 merged
Version guard: VERSION in c3a49f7 reads 2.26.0, matches the tag ✅
Deviations from what you approved: the CI failure above added one commit.

Pushing v2.26.0 fires release.yml, which builds and publishes the release.
This one is yours to run — my credentials get 403'd on tag refs. From your
local clone of the repo:

  git checkout main && git pull origin main \
    && grep -q '^2.26.0$' VERSION \
    && git tag v2.26.0 && git push origin v2.26.0

Tell me when it's done and I'll take it from there.
```

Failures, retries and deviations are the part of that report that matters most —
a report listing only successes is the one nobody needed. Afterwards Claude
confirms the tag on the remote itself rather than taking "done" at face value,
then finishes the release: watch the run, add the notes, verify, and record SHIP
✅, which ships in the next release's PR.

**It is semi-autonomous, not hands-off.** Beyond those two checkpoints, a
blocked gate, a Critical or High security finding, an ambiguous requirement, a
`403` on a branch push, a failed CI run, or anything that needs a tag, branch,
or release *deleted* stops the sequence and comes back to you. Claude deletes no
refs in either mode — the merged PR's own branch included.

**The mode is written to the gate state file**, not remembered — a compacted
session can't lose track of it. A file with no `Mode:` row, or one that reads
`unchosen`, means no mode has been chosen, not manual, and git writes wait
until you answer. The mode never carries into a new session: every session
asks again, even when it resumes from a handoff or finds a committed gate file.
Switch any time with "manual mode" or "auto mode".

Two notes worth knowing:

- **Don't confuse it with Claude Code's own "auto mode"** — that's a permission
  setting in the harness. Being in that one is not asking for this one.
- **It costs more tokens on a local session.** A pasted block is free; a chain
  of executed git commands resends the conversation each round trip. You're
  buying autonomy with tokens, which is usually the right trade when you asked
  for it. It's also where the [enforcement checks](#enforcement-checks) do
  the most work, since every command arrives as a tool call they can inspect.

---

## How gates are enforced

**Gate state is a file, not a memory.** `.dev-skills-gates.md` is written
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

## Execution environments

The skill detects where the session is running, because in
[manual mode](#manual-and-semi-autonomous-mode) that determines whether Claude's
working tree and your terminal are the same clone. (In semi-autonomous mode Claude
runs every command itself except the tag push and ref deletions, which are
always yours, and this table describes only the fallback when one fails.)

| Environment | Git behavior |
|---|---|
| **Local** (Claude Code CLI) | Same clone — commands are **presented** for you to run, at no tool-call token cost |
| **Remote container** (web/mobile) | A clone your terminal never sees — Claude **executes** git directly. A pasted block would commit nothing, and container work is destroyed when the session ends |
| **Termux** (Android) | Presented, plus a clone flow — the repo may not be on the device |

### Forks

If the repo is a fork, **`origin` must be the fork.** Session start checks this
with `gh repo view` against `origin`. If `origin` turns out to be the upstream
parent of a fork you own, Claude stops and repoints it with
`git remote set-url origin <fork-url>` before any work begins. No `upstream`
remote is added for you. If one exists already, it is never pushed to.

From then on every push, PR, merge and release targets the fork, and every
`gh` write carries `--repo <you>/<repo>`. The reason is concrete: in a fork,
a bare `gh pr create` defaults to opening the PR against the **parent** repo.
Anything you want to do upstream, like opening a PR there or syncing the fork,
you do on GitHub directly. The gate file records this as
`Origin: <you>/<repo> (fork of <parent>)`, and the [enforcement
hook](#enforcement-checks) blocks a `gh` write in a fork that has no
`--repo` or names another repo.

### Native Linux sessions get offered Remote Control

On a **local session on native Linux** (not Termux, not WSL, not a container),
the skill mentions once — in either mode — that starting with `claude --rc`, or
running `/rc` in the open session, keeps the terminal session exactly as it is
while also publishing it to claude.ai/code and the Claude desktop and mobile
apps. Same session, reachable from either surface, still executing on your
machine.

It offers the **interactive** form deliberately. `claude remote-control` is
server mode: it serves sessions to the apps and gives you no local prompt, which
is the opposite of the point here. One line, once; decline it and it drops.
(Remote Control needs an eligible login, and on Team and Enterprise plans an
Owner has to enable it first.)

Every environment capability the skill records — Docker daemon reachable,
push allowed, tag push allowed — is measured, not inferred, and re-measured
every session rather than carried forward from a prior one or a handoff
summary. `which docker` only proves the CLI is on `PATH`; a container can
have the binary with no daemon behind it, which looks identical to "Docker
available" until a build actually tries it. The skill checks `docker info`
instead, and treats a capability noted in an earlier context as a claim
about *that* context, not a fact about this one.

### Tag pushes and ref deletions come back to you

In **every** environment, remote containers included, `git tag` /
`git push origin v<X.Y.Z>` and any ref deletion (branch or tag) are presented as
a block for you to run. Claude never executes them, and never creates or deletes
a ref through a GitHub MCP tool.

[Semi-autonomous mode](#manual-and-semi-autonomous-mode) does not change this.
The denial comes from the remote, not from the skill, so no mode can hand Claude
a credential it doesn't have — what that mode adds is a full report of
everything it did, above the block, instead of a bare set of commands. Ref *deletions* stay yours in both modes, including
the source branch of a PR Claude just merged, so Claude never merges with
`--delete-branch`. Everything below still applies:
the permission risk doesn't go away, it just becomes a failure to report rather
than a rule to obey, and a `403` is exactly where semi-autonomous mode hands the block
back to you.

The reason is permissions. Creating a `refs/tags/*` ref — especially one that
*triggers a workflow* — is commonly withheld even where ordinary branch pushes
succeed, and deleting a ref is a separate permission again. A token that pushes
commits all session can still return `403` on a branch delete.

The tag side carries the worse blast radius: the tag push is what fires the
release workflow, so a `403` there strands a merged, version-bumped default
branch with no release behind it. **Gate 6 stays ⏳ until the tag is confirmed on
the remote and pointing at the merge commit** with `git ls-remote` — never ✅
on the assumption that you ran the block; existence alone isn't enough, since
a tag pushed too early still exists. Deleting and re-pushing a tag follows the same rule, and there's a GitHub
UI fallback (**Releases → Draft a new release → Choose a tag**) if you have no
local clone.

<details>
<summary><b>Remote container specifics</b></summary>

Containers arrive pre-cloned (no `git clone` step), commit the gate state file
with the work instead of gitignoring it, and fall back to GitHub MCP tools when
`gh` is unavailable.

They skip the shell question entirely — Claude runs every git command in the
container's own bash — and the tag/ref-deletion block needs nothing asked at
all: it carries no `cd`, and everything in it is a plain single-line `git`
command with no shell-specific syntax. "Run this from your local clone" goes in
the prose above it; the block itself is copyable as given.

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

- **Model is your choice** — no model question or gate; savings come from
  how the session is worked (bounded output, minimal context, fewer turns)
- **Effort fit** — recommends `/effort` changes when the task doesn't match the
  level
- **Subagent model delegation** — when spawning subagents, uses the cheapest
  model tier that fits the task (Haiku for lookups, Sonnet for code, Opus/Fable
  only for the hardest reasoning)
- **MCP awareness** — identifies unused MCP servers adding token overhead and
  gives the `/mcp disable <server>` command for each one
- **Git command presentation** — on local sessions, presents git as a single
  copy-once block per operation rather than several, formatted for your shell
  (PowerShell, Git Bash, Termux, macOS, Linux, WSL) and with no `cd`, since
  your terminal is already in the repo. Remote container sessions execute
  directly instead, since a presented block would operate on the wrong clone
- **Fewer round trips** — session start is one read-only probe call instead of
  about ten, the session-end checkpoint reads its evidence in one call, and any
  step made of several commands is chained into one invocation in every mode
  (never across an approval or a failed gate)
- **Short routine output** — the full gate tracker shows at session start, on a
  gate change, on "status" and in handoffs; otherwise it is one line. The banner
  folds all-clear checks into one row
- **Token impact estimate** — part of the session-end checkpoint whenever the
  session modified a tracked file: what was saved, what was wasted, the biggest
  win next time, in at most three lines
- **Handoff offers** — proposed at three observable points: a release sequence
  finished, you opened unrelated work with no release in flight, or the
  conversation was compacted. Also when a usage limit is actually signalled

**On request — ask by name:**

| Ask for it | What you get |
|---|---|
| "handoff summary" | A ~30-line summary — goal, current state, gate status, key files, decisions, next step — to paste into a fresh, cheap session and drop a long history |
| "how did we do?" | A rough token impact estimate: what was saved, what was wasted, biggest win next time |

---

## Project standards

Five requirements that apply to every project. Claude raises each one when the
project or feature it applies to is being designed, not first at a gate. Your
answer goes on the tracker's `Standards:` row, so a "no" is a decision on the
record, not a gap. Gate 3 checks the code against that row.

| Standard | Applies to | What happens |
|---|---|---|
| **Encryption at rest** | every project | The security section states what is stored, whether each store is encrypted at rest, how, and where the key lives. "Not needed, because …" is an answer. Silence is a finding |
| **TOTP 2FA, "trust this device for 30 days", and unlock/rescue** | anything with a login | All three offered: RFC 6238 TOTP, a signed 30-day trusted-device token revoked on credential change, and recovery codes plus a logged admin unlock. You decide |
| **GitHub + release-notes links on the main page** | every project, no exceptions | Gate 1 blocks until the README top section, and the app's main page if it has a UI, link to both |
| **Apprise notifications** | Docker projects | Offered: an `APPRISE_URLS` setting (a secret, never logged), useful events, and a test-notification action. You decide |
| **Compose quickstart** | Docker projects | The README gives a one-line `mkdir -p /opt/docker/<name>/…` setup, then the compose block with its explanations as `#` comments at the bottom of the YAML (not inline), then the filename (`compose.yaml`). Every volume is a bind mount under `/opt/docker/<name>/`, never a named volume. The image tag is pinned to the current version, so Gate 1 bumps it with every release. Gate 4 checks it |

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
| "just tag it for me" | Tag pushes are yours to run in **both** modes — the block is presented, not executed (semi-autonomous mode adds a full report above it) |
| "just delete that branch for me" | Ref deletions are yours in both modes — the block is presented, not executed |
| "auto mode" / "take it from here" | Semi-autonomous mode on — Claude runs the commands. Commit approval stays, and the tag push and ref deletions stay yours |
| "stop asking me to approve commits" | Not what semi-autonomous mode relaxes — you get offered the mode, you keep the approval |
| "that finding is pre-existing" | Provenance, not a verdict — it stays open and blocks the release until fixed, waived or withdrawn |
| "ignore the Mediums" | Category suppression isn't a waiver — you're asked which specific finding, and the waiver is recorded with your reason |
| "we'll fix it next release" | You're offered the waiver explicitly, so the decision is on the record rather than carried silently |

---

## What's inside

The skill uses tiered loading to keep token costs down:

| File | Size | Loaded when |
|---|---|---|
| `SKILL.md` | ~38KB | **Every turn** (the `hooks:` header isn't loaded) — commit discipline, the operating modes (manual/semi-autonomous), gate pre-flight, the enforcement-check rules, the two tracks, gate state, shortcut detection, cost discipline, and the security layer that must fire unprompted: which patterns to flag on sight, the dependency-audit and attack-surface checklists |
| `SESSION_START.md` | ~30KB | Once, at session start — the one-call probe, the gate state file's format, self-check, version check, execution-environment detection, repo/shell questions, workflow detection, the unfinished-release check, the banner |
| `ENFORCEMENT.md` | ~22KB | Its "At session start" section (~2KB) every session; the whole file whenever a check blocks — the full disclosure, the keep-or-decline question, every check as a plain rule, and what they can't catch |
| `GATE_REFERENCE.md` | ~18KB | When gate 2 or 4 runs, passes, or is marked ➖ N/A — build, test artifact and docs checks; also when the state file must be re-derived or user-driven work credited |
| `RELEASE_GATES.md` | ~9KB | Release track only, when gate 1 or 5 runs, passes, or is marked ➖ N/A — version checks, branch sync, release commit, PR and release notes |
| `DOCKER_TEST.md` | ~9KB | Gate 2, only before a Docker test container is started or a run command handed over — per-session test login, LAN-only publishing, temp-mount and restart rules, the login echo, teardown |
| `LESSONS_REFERENCE.md` | ~4KB | Only when a session found a lesson for the skill itself, and at session start in this repo when lessons are waiting — what counts, asking once, recording to a local-only ref here or a blurb, picking them up |
| `SESSION_END.md` | ~6KB | When the session winds down, a handoff is written or the token impact estimate is due — the session-end checkpoint, where the handoff is stored, the one-call command, the handoff format, the estimate's format, the usage-limit prompt |
| `SECURITY_GATE.md` | ~19KB | Gate 3 only — the security scan, the quality review, the finding lifecycle (fixed / waived by you / withdrawn), and the combined gate output |
| `SHIP_REFERENCE.md` | ~26KB | Gate 6 only — the CI-driven ship path, the manual path, wrong-commit tag recovery, post-ship verification |
| `AUTO_MODE.md` | ~13KB | Only in semi-autonomous mode — the two checkpoint formats, the per-step table, the round-trip cost note, stop conditions |
| `UPDATE_REFERENCE.md` | ~6KB | Only when the version check finds this copy behind the latest release — the out-of-date callout, which update options the install location allows, and the tested install commands (Claude installs it, or you run one command) |
| `REMOTE_SESSION.md` | ~4KB | Only in a remote container (web or mobile session) — no clone, uncommitted work is lost, `gh` → GitHub MCP, no shell question, the state file on the branch, the tag carve-out, Docker without a daemon |
| `STANDARDS_REFERENCE.md` | ~2KB | When a project or feature a project standard applies to is being designed, and when Gates 1, 3 or 4 check one — how the login protections are built, and the compose quickstart example |
| `SECURITY_REFERENCE.md` | ~16KB | Gate 3 + audit mode, and when adding a package — cross-platform and language-general security rules, each with a bad/good code example, and the LTS-line rule with its lookup commands |
| `QUALITY_REFERENCE.md` | ~18KB | Gate 3 + audit mode — cross-platform quality rules, each with a bad/good code example |
| `SECURITY_WINDOWS.md` | ~7KB | Gate 3 + audit mode, only when project environment detection matches Windows — Windows-only security rules and examples |
| `SECURITY_LINUX.md` | ~3KB | Gate 3 + audit mode, only when project environment detection matches Linux/Docker — Linux-only security rules and examples |
| `SECURITY_ANDROID.md` | ~9KB | Gate 3 + audit mode, only when project environment detection matches Android — Android-only security rules and examples |
| `QUALITY_ANDROID.md` | ~3KB | Gate 3 + audit mode, only when project environment detection matches Android — Android-only quality rules and examples |
| `SHELL_REFERENCE.md` | ~16KB | Before writing any command block, and at session start when the repo is a fork or someone else's — fork targeting and the four fork cases, the labeled run-block format, manual mode's few-stops rules, tag/ref-deletion rationale, the semi-autonomous-mode fallback, Git Bash split invocations, Termux clone flow |
| `WORKFLOW_REFERENCE.md` | ~34KB | When a CI workflow is missing or the user asks for workflow help — the selection and audit procedures, workflow linting, template best practices, CI-status release gates, and the review checklist |
| `WORKFLOW_DEPENDABOT.md` | ~6KB | When a repo needs a `dependabot.yml` or one is missing an ecosystem, or a SHA pin is refreshed by hand — the config for every ecosystem, and the `ls-remote` pin lookup |
| `WORKFLOW_DEVRELEASE.md` | ~6KB | Only when the user wants a dev (pre-)release from a branch or Cosign image signing |
| `WORKFLOW_DOCKER.md` | ~17KB | Workflow help, only when environment detection matches Docker — the Docker/container-image template, with the Trivy image scan |
| `WORKFLOW_WINDOWS.md` | ~8KB | Workflow help, only when environment detection matches a Windows app — the .NET/packaged-.exe template |
| `WORKFLOW_LINUX.md` | ~7KB | Workflow help, only when environment detection matches a Linux application — the binary/.deb/.rpm/AppImage template |
| `WORKFLOW_HOMEASSISTANT.md` | ~6KB | Workflow help, only when environment detection matches Home Assistant/HACS — the integration template |
| `WORKFLOW_SCRIPTS.md` | ~7KB | Workflow help, only when environment detection matches a script collection — the shell/PowerShell/Python-scripts template |
| `WORKFLOW_ANDROID.md` | ~9KB | Workflow help, only when environment detection matches Android — the Gradle/APK/AAB template |
| `WORKFLOW_HYBRID.md` | ~13KB | Workflow help, only when environment detection matches a Capacitor/Ionic hybrid app — npm build, `cap sync`, then the signed APK |
| `WORKFLOW_PYTHON.md` | ~8KB | Workflow help, only when environment detection matches a Python package — the PyPI template |
| `WORKFLOW_NODEJS.md` | ~8KB | Workflow help, only when environment detection matches Node.js — the npm template |
| `checks/enforce.py` | ~85KB | Never loaded into Claude's context. Claude Code runs it as the [enforcement checks](#enforcement-checks) |

The split follows one rule: **triggers load every turn, recipes load on demand.**
`SKILL.md` holds what has to fire without being asked. How to actually *run* a
gate lives in `GATE_REFERENCE.md`, loaded when the pre-flight says one is owed.
Security, quality, and shell formatting work the same way.

The second rule is **one file, one moment.** A reference file is read in full,
so a file that covers several unrelated moments charges every one of them for
all of it. Session start happens once and never again; Gate 6 is the largest of
the six and fires last; semi-autonomous execution is dead weight in a manual
session; eight of the nine workflow templates are wrong for any given project.
Each of those is its own file, so loading one does not drag the others along.
`scripts/validate.sh` enforces a per-file size ceiling to keep it that way.

Security is the clearest case. *Knowing* that a `pickle.loads` on untrusted
input is worth flagging has to be resident — nobody asks for it, and Gate 3 runs
too late if the pattern was written an hour ago. The worked example of how to
fix it does not: that loads with the gate. So the flag-on-sight categories stay
in `SKILL.md` and the rules and examples live in `SECURITY_REFERENCE.md` —
split further into `SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`, and
`SECURITY_ANDROID.md` so a project only pays for the platform it's actually
on.

Sizes in this table are verified by `scripts/validate.sh`. `SKILL.md` is paid for
on every request, so an understated figure hides a real per-turn cost.

---

## For maintainers

Contributing guide: [CONTRIBUTING.md](CONTRIBUTING.md). Build and check with:

```bash
bash scripts/build-skill.sh   # rebuild dev-skills.skill from source
bash scripts/validate.sh      # versions, changelog, size table and ceilings,
                              # rule phrases, bundle-vs-source
```

**Rules are guarded, not just written.** `scripts/rule-phrases.txt` lists the
phrases that carry the skill's rules. Each is either required in `SKILL.md`
(`SKILL|`: triggers and hard rules that must fire without anything being
loaded) or required somewhere in the skill (`ANY|`: procedures that load on
demand). `validate.sh` fails if one goes missing, so trimming or rewording
can't silently drop a rule. Removing a line from that file is removing a rule;
say so in the CHANGELOG.

Releases are published by CI: pushing a `v*` tag runs
`.github/workflows/release.yml`, which verifies the tagged commit is on the
default branch, rebuilds `dev-skills.skill` from the tagged source, publishes the
release with notes from `CHANGELOG.md`, and fails if the artifact doesn't end up
attached.

The default-branch check matters because a tag trigger fires for a tag on *any*
commit — without it, tagging an unreviewed branch would publish a real release
from unreviewed code. Every workflow pins `actions/checkout` to a commit SHA
rather than a mutable version tag, checks out with `persist-credentials: false`,
declares least-privilege `permissions:`, and carries a concurrency group and
timeouts. `validate.yml` runs `validate.sh`, which includes the check test
cases in `scripts/test-checks.py`, on every push and pull request.
`lint-workflows.yml` runs actionlint (checksum-verified) on any change
to the workflow files or the templates. `check-pins.yml` resolves every action
pin, templates included, against the tag its comment names, weekly and on any
pull request that touches one. `audit-repos.yml` runs `scripts/audit-repos.py`
weekly against the workflows of every repo you own and keeps one "Weekly
workflow audit" issue here up to date.

---

## Migrating from the old skills (pre-2.0)

From 2.0.0 this single skill replaces all four previous ones:

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

`v2.46.0` — see [CHANGELOG.md](CHANGELOG.md) for the full history.
