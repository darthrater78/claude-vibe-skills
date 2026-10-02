# Release Gates — Gates 1 and 5

Loaded on demand by the dev-skills skill, **on the release track only**: when
Gate 1 (Version) or Gate 5 (Release) is about to run, pass, or be marked ➖
N/A. A work commit or work-commit merge never needs it. Section numbers point
at `SKILL.md`.

---

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
3. **Bring the gate state file up to date before the release commit**: gates
   1–5 ✅ with the evidence that passed each, SECURITY reading `0 open` (Gate 3
   — it cannot be ✅ otherwise), and 🚀 SHIP ⏳ carrying the plan rather than ⬜.
   **Local sessions: it stays untracked.** Never stage or `git add -f` it: a
   tracked copy is rewritten by every session and blocks `git checkout`. The
   release record is the commit, `CHANGELOG.md`, the tag and the handoff.
   **Remote containers: stage it with the release — it ships inside this PR**
   (`git add -f .dev-skills-gates.md` where gitignored), because the
   container's copy dies with the container.

   SHIP is ⏳ here and that is correct, not a gap: the tag does not exist yet,
   so no commit that precedes it can honestly claim it does. The post-tag line
   folds into the next release's PR (`SHIP_REFERENCE.md`, step 7). **There is
   never a separate bookkeeping PR**, and a release PR that does not carry the
   state file leaves the tagged commit describing a release that had not
   happened. (Remote containers; a local file is never in any commit.)
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
> Gate state file: gates 1–5 ✅, SHIP ⏳ (in the PR on remote containers; untracked locally)
> Pending: merge, tag, and publish (Gate 6)

---

Gate 6 — Ship 🚀 continues in `SHIP_REFERENCE.md`. Load it now if the ship gate
is what the pre-flight says is owed.
