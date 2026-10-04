# Gate Reference — Gates 2 and 4

Loaded on demand by the dev-skills skill when **Gate 2 or Gate 4 is about to
run, pass, or be marked ➖ N/A**, and when the gate state file must be
re-derived or user-driven work credited. The triggers (pre-flight, tracks,
gate state) stay in `SKILL.md` Section 2; section numbers here point at it.

---

## Gate state file — re-derivation and resuming

The rules are in `SKILL.md` Section 2 ("Gate state"); the format and row
rules in `SESSION_START.md` ("Write the gate state file").

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
   `gh` is unavailable, `REMOTE_SESSION.md` item 3). Chain them into one call
   (`SKILL.md` §5.1).
2. Credit completed mechanical steps on the tracker (✅ "user-driven" or
   "already done").
3. Re-derive Gates 1–4 from evidence (table above), never from the presence of
   a commit.
4. Continue from the first gate that is not ✅ or ➖ N/A.

---

## Gates 2 and 4 — execution detail

How gates 2 and 4 are run and what makes them pass.

### Gate 2 — Build 🔨

**This gate runs the local development workflow** detected at session start
(`SESSION_START.md`, step 6) — the project's own build and test commands, not CI.
CI runs later and on a different machine; it cannot tell you now whether the
code you just wrote works. Run the project's build command only after Gate 1
is ✅ (or ➖ on a work-commit merge). If the build fails, fix and rebuild — do not advance.

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
§9) or a dev pre-release, and hold the merge until one exists. A container
that cannot build Docker at all is the earlier problem in `REMOTE_SESSION.md`,
item 8.

Hand it over after the smoke test passes, before this gate is marked passed:

- **`.exe`, `.apk`, binaries:** copy the artifact into a local folder (e.g.
  `dist/`, `build/output/`) and give the exact path, or give the CI artifact
  link. An artifact uploaded with `archive: false` can make `gh run download`
  refuse with "path traversal"; hand over `gh api
  repos/<owner>/<repo>/actions/artifacts/<id>/zip > <file>` instead, plus a
  hash to compare with the artifact's `digest`, in the user's recorded shell.
- **Docker images:** give the exact commands to get and run it: `docker load
  -i <file>` (tarball), `docker pull <image>:pr-<n>`, or `docker build -t
  <tag> .`, then `docker run ...` with the ports and volumes the project needs,
  and the credentials below.

**Docker test runs: read `DOCKER_TEST.md` first**, before starting any test
container or handing over a run command. It has the per-session
test login (shown in a 🔑 block at the bottom of every message where the
container changed), LAN-only publishing, the temp-mount and restart rules, and
teardown.

The handover is repeated **every time the build changes**, not only the first
time in a session. **Proceeding without trying it counts as declining to try
it**, not as an unanswered question that blocks the gate: if the user answers
a commit or ship prompt with "commit" or "go ahead", record their words
(`handoff offered, user said "Commit" without running the image — recorded as
declined`). Declining to try it never waives the artifact.

**Record it on the tracker, not just in chat.** In any repo with a
Docker/.exe/.apk build signal, the enforcement checks (`ENFORCEMENT.md`, A4)
deny a BUILD ✅ with no `handoff` annotation, and **deny every merge to the default
branch** whose BUILD row has no `test artifact:` annotation, or, with a
Dockerfile or compose file, no `test creds` annotation. Write the BUILD row as:

```
🔨 BUILD      ✅ <build>; handoff offered, user tried it
  test artifact: <path, CI artifact link, or pre-release> @ <short SHA>
  test creds: generated this session, shown to user   (or: n/a (no login))
```

"Declined" describes the user's choice not to try it, never Claude skipping
the handover. In a remote container or Termux the artifact comes from CI, so
`handoff n/a` is no answer.

**One exception: a work-commit merge that changes no app code** (docs,
screenshots, tooling the app build excludes, and the build-file lines that
exclude it). On `Track: work commit`, write `test artifact: n/a — no app code
changed` on its own line under BUILD. It stands in for the handoff and the
artifact, and adding it asks the user (B5), so they confirm the diff really
is app-free. A release never takes it: it needs a real artifact.

**Projects with CI release workflows.** If the project has a GitHub Actions
workflow that builds release artifacts on tag push (check
`.github/workflows/` for `on: push: tags:`), the local build gate covers
only the **debug/test build**, which is also the test artifact. The release
artifact is built by CI during Gate 6 — do not build it locally. Gate 2
passes when the debug build compiles and the app is verified working.

**Projects with a UI: a visual pass before commit approval.** Every screen
the diff touches, with realistic seeded data (long names, many rows): an
automated overflow check (`scrollWidth > clientWidth` on tables, dialogs and
popovers) at 1920, 1440, 1280 and ~390 px wide in light and dark theme, then
a look at each touched screen at one desktop and the phone width. With a
`DESIGN.md` (`DESIGN_REFERENCE.md`), also: that look compares each screen
against it, the changed UI files hold no raw colours and no generic tell it
didn't choose, and its pinned `lint` passes when it or the tokens changed.
Record it on the BUILD row (`visual pass: N screens × 4 widths × 2 themes,
0 overflow · DESIGN.md: lint clean, 0 tells`).

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

In `SECURITY_GATE.md`, which also loads the security and quality references:
open it only for Gate 3.

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
7. **README visuals and walkthroughs** — every release to the default
   branch, and before the release PR opens, never between merge and tag.
   Walk each step-by-step section (Quick Start, usage) against the test
   artifact, and retake any screenshot whose UI changed, from seeded sample
   data. **Before staging regenerated images, diff each against HEAD** with
   a pixel threshold and keep only real changes: anti-aliasing noise is
   churn, and an unexpected change may be a harness or app bug, so look at
   it. If the look changed, `DESIGN.md` describes the new one.

Show what was checked:

> ✅ **DOCS GATE PASSED**
> - Version history: v1.2.3 entry added with date and changes
> - New features: [list any docs updated]
> - Removed features: [list any stale refs cleaned up, or "none"]
> - Architecture/tables: [updated / no changes needed]
> - Internal consistency: [README descriptions match source of truth, or list fixes]
> - Compose quickstart: [matches the standard at v1.2.3 / N/A, not Docker]
> - README visuals: [retaken N, unchanged M · quick start re-walked · DESIGN.md current / N/A, no UI]

If documentation is missing or stale:

> 🚫 **DOCS GATE BLOCKED**
> The following documentation issues must be resolved:
> - [specific issue, e.g. "README still references feature X which was removed"]
> - [specific issue, e.g. "README calls Gate 6 'Push' but it was renamed to 'Ship'"]
> - [specific issue, e.g. "No version history entry for v1.2.3"]
>
> Fixing now...

Fix any issues found. Rebuild if doc fixes affected source files. A
docs-only fix never triggers a full CI run (`SKILL.md` §5.1).

---

Gate 5 — Release 📦 is in `RELEASE_GATES.md` (release track only).
