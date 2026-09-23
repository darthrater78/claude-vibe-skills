# Gate Reference — Gates 1–5

Loaded on demand by the dev-skills skill, when **a gate is about to run, pass,
or be marked ➖ N/A**, and when you are checking gate status and need a gate's
pass criteria. This file holds the **execution detail** for gates 1 through 5 —
the recipes, not the triggers.

The triggers stay in `SKILL.md` and are in effect at all times: commit
discipline, the mandatory pre-flight, the two tracks, the gate state file, the
tracker, and shortcut detection. This file tells you *how to run* a gate once
the pre-flight says one is owed.

**The rest of the reference set, loaded only at the moment each is owed:**

| File | Load when |
|---|---|
| `SESSION_START.md` | the session starts — once, before anything else |
| `SECURITY_GATE.md` | Gate 3 runs, passes, or is marked ➖ N/A, or a finding needs resolving |
| `SHIP_REFERENCE.md` | Gate 6 runs, passes, or is marked ➖ N/A |
| `AUTO_MODE.md` | the user has opted into semi-autonomous mode |
| `SECURITY_REFERENCE.md`, `QUALITY_REFERENCE.md` | Gate 3 (via `SECURITY_GATE.md`), and audit mode |
| `SHELL_REFERENCE.md` | before composing any command block |
| `WORKFLOW_REFERENCE.md` | a CI workflow is missing, or the user asks for workflow help |

Do not load a file this session has no use for. Each of these is read in full;
loading the ship path during Gate 1, or semi-autonomous execution in a manual
session, costs the tokens without the content ever being used.

Section numbers referenced here (Section 1, 2, 5.7, …) point at `SKILL.md`.

---

## Gate state file — re-derivation and resuming

The rules for `.claude/dev-skills-gates.md` are in `SKILL.md` Section 2 ("Gate
state"). This is the detail: load it when the file is missing, stale or
compacted away, or when a user-driven action has to be credited.

The file's format and row rules are in `SESSION_START.md`, where it is first
written ("Write the gate state file").

**Remote refs, never local ones.** Reading refs is not a write:

```
git ls-remote --tags origin              # all tags
git ls-remote --tags origin v1.2.3       # one tag
git ls-remote --heads origin             # all branches
git ls-remote --heads origin main        # one branch
```

**Re-derivation — when the state file is missing, stale, or the session was
compacted.** Do not guess, and do not treat a gate as passed because it feels
like it did. Rebuild from evidence:

| Gate | Evidence that it passed |
|---|---|
| 🔢 VERSION | every version-carrying file reads the same bumped semver, and `git ls-remote --tags origin` shows the previous version tagged |
| 🔨 BUILD | a build artifact exists newer than the last source edit — or the project has no build system (➖ N/A). **A check list with zero runs is ⬜, never ✅** (`SKILL.md` Section 2, "Absence of a verdict") |
| 🔒 SECURITY | a scan was run against the **current** diff; a scan of earlier code does not cover edits made after it |
| 📄 DOCS | the changelog has an entry for this version, and the README matches current behavior |
| 📦 RELEASE | a PR exists for this branch (`gh pr list`, or MCP `list_pull_requests`) |
| 🚀 SHIP | tag on remote, release exists, PR merged, expected assets attached |

Any gate you cannot prove from evidence is ⬜ pending and must be run.
"It probably ran" is ⬜.

**Resuming, or crediting user-driven work:**
1. Run `git log`, `git ls-remote --heads origin`, `git ls-remote --tags
   origin`, and `gh pr list` / `gh pr view` (or the GitHub MCP equivalents when
   `gh` is unavailable, `SESSION_START.md` step 0). Chain them into one call
   (`SKILL.md` §5.1).
2. Credit completed mechanical steps on the tracker (✅ "user-driven" or
   "already done").
3. Re-derive Gates 1–4 from evidence (table above), never from the presence of
   a commit.
4. Continue from the first gate that is not ✅ or ➖ N/A.

---

## Gates 1–5 — execution detail

The pre-flight, the two tracks and the gate state rules live in `SKILL.md`
Section 2; the re-derivation table is above. What follows is how each of gates 1 through
5 is actually run and what makes it pass. **Gate 3 is in `SECURITY_GATE.md`**
and **Gate 6 is in `SHIP_REFERENCE.md`**
— read that file when the ship gate is the one that is owed, not before.

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
   **Docker projects: the image tag in the README's compose quickstart and in
   any shipped `compose.yaml` is a version reference** (`SKILL.md` §10). It is
   bumped with the rest, and `latest` there is a gate failure.
3. Every version reference must show the same version and it must be bumped from
   the previous release.
4. Version must follow semver (MAJOR.MINOR.PATCH).
5. **Repository link is mandatory.** Every project that has an app manifest
   (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.) must include the
   `repository` / `homepage` / `[project.urls]` field pointing to the GitHub repo
   it belongs to. If missing, add it before passing this gate.
6. **Main-page links are mandatory, without exception** (`SKILL.md` §10).
   The project's main page (the README's top section, and the app's main page
   or screen when it has a UI) links to **both** the GitHub repo and the
   current version's release notes. Every other place that shows a repo link
   (an "About" dialog, settings screen, footer, help menu) also carries the
   release notes link. Use the pattern
   `https://github.com/<owner>/<repo>/releases/tag/v<VERSION>`; the version in
   the URL must match the version being built. A missing link on the main
   page blocks this gate. Add it before passing.

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
> - [e.g. "README top section has no link to the v1.2.3 release notes"]
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
(`SESSION_START.md`, step 6) — the project's own build and test commands, not CI.
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

This is weaker than the local gate and is recorded as such. The test artifact
before merge (below) still applies, and comes from that CI build. It does not
license "CI will catch it" on a project where a local build merely takes a
while — that is still a straightforward BUILD GATE BLOCKED, not this state.

**Prove a never-run release step before a tag depends on it.** A release
workflow's own steps aren't proven by ordinary CI — a Docker registry
login, a signing step, a computed-version extractor, an ancestor-fallback
path only exercised on tag push — until a tag actually goes through them for
real once. Discovering a bug in one of those steps *during* a live release
means cancelling a run, deleting a wrongly-published release, and re-tagging
(the recovery runbook in `SHIP_REFERENCE.md`). Cheaper: before a tag push is about to
exercise a step that has never actually run in this repo, copy it out of
`release.yml` and dry-run it here if the tooling allows — against the local
build, with real (or scoped test) credentials where that's safe, or by hand
inspection where it isn't. Keep a short "unproven" note for anything that
still can't be exercised this way (e.g. it genuinely needs the tag-push
trigger's context) and carry it forward release to release until it's
actually run once for real — don't let it quietly stop being tracked just
because the release it was flagged on shipped anyway.

**Test artifact before merge — required in every environment and both
modes.** For any build that produces something a person installs or runs
outside a terminal — a Docker image, a Windows `.exe`, an Android `.apk`, a
packaged binary — the smoke test proves the code runs; it does not prove the
artifact works. **Nothing merges to the default branch until a test artifact
built from the exact commit being merged exists, and the user has been told
where it is and how to run it.** Trying it is the user's choice. The artifact
existing is not. The release build CI makes after the tag never counts: it
comes after the merge this rule protects. A push after the artifact was built
means a new artifact.

| Session | Where the test artifact comes from |
|---|---|
| **Local, Linux host** (Linux Terminal, WSL) | Built here: Docker image, `.exe`, `.apk`, binary |
| **Local, Windows host** (PowerShell, Git Bash) | Built here: `.exe`, `.apk`. Docker only if `docker info` answers; otherwise from CI, as in the next row |
| **Remote container or Termux** | Built by CI from the PR head commit: a PR build workflow that uploads it (`actions/upload-artifact`; a Docker image as a `docker save` tarball artifact or pushed with a `pr-<number>` tag), or a pre-release tag the user pushes (`WORKFLOW_REFERENCE.md`, "Dev releases"). Give the user the link to that run's artifact or the pre-release |

**No way to produce one is a blocked merge, not a skipped step.** If CI has no
job that publishes a test artifact for a PR, offer to create one (`SKILL.md`
§9.2) or a dev pre-release, and hold the merge until one exists. A container
that cannot build Docker at all is the earlier problem in `SESSION_START.md`,
step 0, item 8.

Hand it over after the smoke test passes, before this gate is marked passed:

- **`.exe`, `.apk`, binaries:** copy the artifact into a local folder (e.g.
  `dist/`, `build/output/`) and give the exact path, or give the CI artifact
  link.
- **Docker images:** give the exact commands to get and run it: `docker load
  -i <file>` (tarball), `docker pull <image>:pr-<n>`, or `docker build -t
  <tag> .`, then `docker run ...` with the ports and volumes the project needs,
  and the credentials below.

**Docker test runs get fresh credentials, every run.** Each time a container
is started for testing — by Claude, or in a run command handed to the user —
generate a new username and password for that run and show them to the user
in the same message as the run command:

```bash
TEST_USER="test-$(LC_ALL=C tr -dc 'a-km-z2-9' </dev/urandom | head -c4)"
TEST_PASS="$(LC_ALL=C tr -dc 'A-HJ-NP-Za-km-z2-9' </dev/urandom | head -c12)"
docker run -d --rm --name <app>-test -p 127.0.0.1:8080:8080 \
  -e <APP_USER_VAR>="$TEST_USER" -e <APP_PASS_VAR>="$TEST_PASS" <image>
```

> 🔑 **Test login for this run** — throwaway, reachable only from this
> machine, gone when the container is removed.
> URL: http://127.0.0.1:8080 · User: `test-k3xm` · Password: `Hq7vT2mWz9Ka`

- **Simple on purpose:** letters and digits only, with look-alikes (`0 O 1 l
  I`) left out, so they can be read off the screen and typed.
- **Passed to the variables the app actually reads for its login.** Find them
  in the Dockerfile `ENV`, the compose file, `.env.example`, or the docs; never
  guess a name. For compose, set them on the command line
  (`TEST_USER=… TEST_PASS=… docker compose up -d`) for a compose file that
  interpolates them. A compose file with credentials written into it is a
  Gate 3 finding (hardcoded secret), not something to work around.
- **Ports bound to `127.0.0.1` only**, so throwaway credentials never face a
  network.
- **Never** written to a file in the repo, baked into the image (`ENV`/`ARG`),
  reused across runs or sessions, or the project's real credentials.
  Displaying them is the point: they die with the container.
- **An app with no login** needs none: say so, and record `test creds n/a (no
  login)`.

**Echo the login every time the test container changes, as the last thing in
the message.** Testing is iterative: fix, rebuild, restart, re-check. A login
shown once scrolls out of sight after the first round. So the 🔑 block above is
repeated, in full (URL, user and password), at the **bottom** of every message
in which the test container was started, rebuilt, restarted or recreated, or
in which the user is asked to try it again. That includes a rebuild after a
one-line fix. The bottom of the message is where the user's eye lands, so
nothing goes below it. A pointer such as "same login as before" or "see
above" does not count. When the credentials changed with the new container,
say so on the block's first line (`🔑 **New test login, the previous one no
longer works**`). If the current credentials are no longer in context, for
example after compaction, never reconstruct them from memory. Recreate the
container with fresh ones and show those.

**Tear it down once its purpose is served.** A container started here — or for
the "prove a never-run release step" check above, or for any other Gate 2
testing — is a running resource, not a fire-and-forget check. Stop and remove
it after the commit it verified is submitted, or immediately if the user
declines to try it: `docker stop <name>` (or `docker compose down` for a
compose stack), then `docker rm <name>` if it wasn't started with `--rm`.
Before the session ends (Section 8) or this gate closes, `docker ps` to
confirm nothing test-related is still running. Its credentials go with it.

The handover is repeated **every time the build changes**, not only the first
time in a session. **Proceeding without trying it counts as declining to try
it**, not as an unanswered question that blocks the gate: if the user answers
a commit or ship prompt with "commit" or "go ahead", record their words
(`handoff offered, user said "Commit" without running the image — recorded as
declined`). Declining to try it never waives the artifact.

**Record it on the tracker, not just in chat.** Where `hooks/gate-preflight.sh`
is installed, in any repo with a Docker/.exe/.apk build signal, it denies a
BUILD ✅ with no `handoff` annotation, and **denies every merge to the default
branch** whose BUILD row has no `test artifact:` annotation, or, with a
Dockerfile or compose file, no `test creds` annotation. Write the BUILD row as:

```
🔨 BUILD      ✅ <build>; handoff offered, user tried it
  test artifact: <path, CI artifact link, or pre-release> @ <short SHA>
  test creds: generated per run, shown to user   (or: n/a (no login))
```

"Declined" describes the user's choice not to try it, never Claude skipping
the handover. There is no valid annotation for "no test artifact": in a
remote container or Termux the artifact comes from CI, so `handoff n/a` is no
longer an answer.

**Projects with CI release workflows.** If the project has a GitHub Actions
workflow that builds release artifacts on tag push (check
`.github/workflows/` for `on: push: tags:`), the local build gate covers
only the **debug/test build**, which is also the test artifact. The release
artifact is built by CI during Gate 6 — do not build it locally. Gate 2
passes when the debug build compiles and the app is verified working.

> ✅ **BUILD GATE PASSED** — debug build verified working (release build deferred
> to CI); test artifact: Android `.apk` in `dist/` @ a1b2c3d; handoff offered,
> user declined to try it by hand this round

**Projects with no build step** (config repos, skill repos, documentation-only
repos, pure script collections): mark this gate ➖ N/A with an explanation:

> ➖ **BUILD GATE N/A** — this is a [skill/config/docs] repo with no build system.

Do not silently skip — always show the N/A status on the tracker.

> ✅ **BUILD GATE PASSED** — test build verified working
> Output: [artifact path]

### Gate 3 — Security & Quality 🔒

**Gate 3 is in `SECURITY_GATE.md`** — read that file when the security gate is
the one that is owed. It holds the scan, the quality review, the finding
lifecycle, and the combined output, and it is where the rule lives that no
finding of any severity may be open when the release track runs.

It also loads `SECURITY_REFERENCE.md` and `QUALITY_REFERENCE.md`, so do not
open it for gates 1, 2, 4 or 5.

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
6. **Docker compose quickstart** (`SKILL.md` §10). This applies to Docker
   projects. The README has the one-line `mkdir -p /opt/docker/<name>/…`
   setup, then the compose block with only bind mounts under
   `/opt/docker/<name>/`, the image pinned to this version, and its
   explanations as `#` comments at the bottom of the YAML (not inline), then
   the `compose.yaml` filename. A missing quickstart, a named volume or a
   `latest` tag blocks this gate.

Show what was checked:

> ✅ **DOCS GATE PASSED**
> - Version history: v1.2.3 entry added with date and changes
> - New features: [list any docs updated]
> - Removed features: [list any stale refs cleaned up, or "none"]
> - Architecture/tables: [updated / no changes needed]
> - Internal consistency: [README descriptions match source of truth, or list fixes]
> - Compose quickstart: [matches the standard at v1.2.3 / N/A, not Docker]

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
3. **Stage the gate state file with the release — it ships inside this PR.**
   `.claude/dev-skills-gates.md` is part of the release commit, not a
   follow-up. Bring it up to date first: gates 1–5 ✅ with the evidence that
   passed each, SECURITY reading `0 open` (Gate 3 — it cannot be ✅ otherwise),
   and 🚀 SHIP ⏳ carrying the plan rather than ⬜. Where the file is
   gitignored, force-add it: `git add -f .claude/dev-skills-gates.md`.

   SHIP is ⏳ here and that is correct, not a gap: the tag does not exist yet,
   so no commit that precedes it can honestly claim it does. The post-tag line
   folds into the next release's PR (`SHIP_REFERENCE.md`, step 7). **There is
   never a separate bookkeeping PR**, and a release PR that does not carry the
   state file leaves the tagged commit describing a release that had not
   happened.
4. **Get commit approval** (per `SKILL.md` Section 1) — show what's staged, get explicit yes
5. **Verify remote is configured.** Run `git remote -v`. If no origin is set,
   include `git remote add origin <url>` (using the URL stored at session start)
   in the command block before any push commands. This prevents the "default repo
   has not been set" error. **If the gate state file's `Origin:` row says
   `fork of`, confirm that `origin` still points at the fork, and give
   `gh pr create` an explicit `--repo <fork-owner>/<repo>` (and `--base` a
   branch of the fork).** Without `--repo`, `gh` opens the PR against the parent
   repo (`SHELL_REFERENCE.md`, "Forks").
6. **Present commands per Section 5.8** — format the commit, push, and PR creation
   commands for the user's shell environment. The user runs them manually or asks
   Claude to execute directly. **In semi-autonomous mode, Claude runs all three itself**
   (`AUTO_MODE.md`); no block is presented unless one fails.
7. After the branch is pushed and PR created, draft release notes and show the
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

8. Wait for explicit approval of the PR content and release notes. **In
   semi-autonomous mode this approval already happened** — the release notes were part
   of the single commit checkpoint. Post the PR and the notes for the record and
   continue to Gate 6. Re-ask only if the notes changed since that checkpoint.

**Never commit directly to main/master.** All work happens on feature/fix/release
branches and merges via PR. If the session is on the default branch when Gate 5
is reached, create a branch first.

> ✅ **RELEASE GATE PASSED** — PR [url] ready, release notes approved
> Gate state file included in the PR: gates 1–5 ✅, SHIP ⏳
> Pending: merge, tag, and publish (Gate 6)

---

Gate 6 — Ship 🚀 continues in `SHIP_REFERENCE.md`. Load it now if the ship gate
is what the pre-flight says is owed.
