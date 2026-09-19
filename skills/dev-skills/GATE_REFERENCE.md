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
| `SHIP_REFERENCE.md` | Gate 6 runs, passes, or is marked ➖ N/A |
| `AUTO_MODE.md` | the user has opted into semi-autonomous mode |
| `SECURITY_REFERENCE.md`, `QUALITY_REFERENCE.md` | Gate 3, and audit mode |
| `SHELL_REFERENCE.md` | before composing any command block |
| `WORKFLOW_REFERENCE.md` | a CI workflow is missing, or the user asks for workflow help |

Do not load a file this session has no use for. Each of these is read in full;
loading the ship path during Gate 1, or semi-autonomous execution in a manual
session, costs the tokens without the content ever being used.

Section numbers referenced here (Section 1, 2, 5.7, …) point at `SKILL.md`.

---

## Gates 1–5 — execution detail

The pre-flight, the two tracks, the gate state file, and the re-derivation
table live in `SKILL.md` Section 2. What follows is how each of gates 1 through
5 is actually run and what makes it pass. **Gate 6 is in `SHIP_REFERENCE.md`**
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

This is weaker than the local gate and is recorded as such. It does not
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
   (`AUTO_MODE.md`); no block is presented unless one fails.
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

---

Gate 6 — Ship 🚀 continues in `SHIP_REFERENCE.md`. Load it now if the ship gate
is what the pre-flight says is owed.
