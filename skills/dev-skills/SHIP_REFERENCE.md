# Ship Gate Reference — Gate 6 🚀

Loaded on demand by the dev-skills skill, when **Gate 6 is about to run, pass,
or be marked ➖ N/A**. It is a separate file from the other five gates because
it is the largest of them and fires once, at the end of a release sequence —
gates 1–5 have no use for it.

It holds the CI-driven ship path, the manual path for repos with no release
workflow, the wrong-commit tag recovery, and the post-ship verification.

Gates 1–5 are in `GATE_REFERENCE.md`. The pre-flight, the two tracks and the gate
state rules are in `SKILL.md` Section 2; the re-derivation table is in
`GATE_REFERENCE.md`, "Gate state file".

Section numbers referenced here (Section 1, 2, 5.7, …) point at `SKILL.md`.

---

### Gate 6 — Ship 🚀

Merge, tag, and publish. All three happen here, not in Gate 5.

**Pre-ship summary — explicit confirmation required.** "Yeah" or "ok" is not
enough — the user must say "ship", "yes push", or "go ahead." **In
semi-autonomous mode this confirmation becomes checkpoint 2: the full pre-tag
report, handed over with the tag block** (`AUTO_MODE.md`,
checkpoint 2). It is a longer stop than this one, not a shorter one — the user is
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
   A handed-over deletion is confirmed like a tag: `git ls-remote --heads
   origin <branch>` returning nothing.

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
   Claude did since the commit approval (`AUTO_MODE.md`,
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

   **Manual mode: merge through tag can be one block, when the shell makes
   step 2's checks.** Every stop in manual mode costs a model request
   (`SKILL.md`, Operating modes), and step 2's checks are mechanical. So the
   merge, both checks, the version guard and the tag can go in one `&&` chain
   that fails closed. It **replaces** the stop only when every link below is
   present: PR checks green before the merge, `HEAD` equal to the merge commit,
   and a CI run *on that commit* watched to success. A missing run makes
   `gh run watch` fail, which stops the chain, so an empty run list cannot
   read as a pass. Fill in the number, branch, workflow and version from this
   project:

   ````
   ### ▶️ RUN THIS — merge PR #<n> → tag v1.2.3 · in ~/<repo> · block 2 of 2
   ```bash
   # ════════ ▶️ START: merge → tag v1.2.3 ════════
   n=<pr-number> && gh pr checks "$n" --watch --fail-fast \
     && gh pr merge "$n" --merge --delete-branch \
     && git checkout main && git pull --ff-only origin main \
     && sha=$(gh pr view "$n" --json mergeCommit -q .mergeCommit.oid) \
     && [ "$(git rev-parse HEAD)" = "$sha" ] && sleep 20 \
     && gh run watch "$(gh run list --commit "$sha" --workflow <ci-workflow>.yml --json databaseId -q '.[0].databaseId')" --exit-status \
     && grep -qx '1.2.3' VERSION \
     && git tag v1.2.3 && git push origin v1.2.3 \
     && echo "✅ DONE: v1.2.3 tagged" || echo "❌ STOPPED: scroll up for the error"
   # ════════ ⏹️ END ════════
   ```
   ### ⏹️ END — nothing else to run
   No need to reply. Your next message starts with me checking the tag and
   the release run.
   ````

   Block 1 of 2 (commit → push → open PR) comes first, and the user looks at
   the PR between the two. Only a user can run this block, since it holds a
   tag push and a ref deletion (Section 5.8). The enforcement checks hold it
   back until every gate through RELEASE is ✅ (`ENFORCEMENT.md`, C2). The two-step form above stays in place when CI
   doesn't run on pushes to the default branch, or when the shell can't run
   `gh`. After the block, verify the tag's target as below, in the chained read
   that opens the user's next message.

   **No `cd`, and no clone-path question.** Say "run this from your local clone
   of the repo" in the prose above the block and leave the block copyable as
   given — a `cd` the user has to edit is a broken first line, and someone
   pushing a release tag knows where their checkout is
   (`SHELL_REFERENCE.md`, "Tag and ref-deletion blocks carry no `cd`").

   ```
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
   local dev drift apart (`SESSION_START.md`, step 6). If the
   project's versioning is tag-derived or computed (`setuptools-scm`, a
   `git describe`-based Android `versionName`), there is nothing to grep for
   — drop this clause and say so.

   > 📌 **Pushing that tag is what starts the release build.** Run the block
   > above. No need to reply just to say it's done: I'll check the tag and the
   > release run at the start of your next message.

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
   gone looking for a permissions fix; the fix here is simpler: from inside the
   clone, re-run `git tag v1.2.3`, then push again. This is the failure the
   prose reminder above the block is there to prevent.

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
   > original push. From their local clone:**
   > ```
   > git tag -d v1.2.3
   > git push origin :refs/tags/v1.2.3
   > # after the fix is merged to the default branch:
   > git checkout main && git pull origin main
   > git tag v1.2.3
   > git push origin v1.2.3
   > ```

7. **The SHIP ✅ record does not get its own PR.** On a local session the
   gate state file is untracked, so SHIP ✅ is written to it and nothing more.
   On a remote container it rode in with the release PR (Gate 5) and is already on the default branch carrying
   gates 1–5 ✅ and SHIP ⏳ with the plan. What is left after the tag is the
   one line that could not have existed before it — and that line is folded
   into **the next release's PR**, by the same close-as-you-go rule that
   governs every other section of this file (Section 2: close a section as
   part of the step that absorbs it). The next sequence's VERSION step is the
   step that absorbs it.

   **Never open a pull request whose only content is tracker bookkeeping.**
   Four consecutive releases of this repo each trailed one, which means the
   tagged commit's own state file was wrong every time — it said SHIP ⬜ for a
   version that had shipped, and the correction arrived in a PR merged after
   the fact.

   **Between the tag and the next release, the durable record is the tag, the
   GitHub release and the `CHANGELOG.md` entry.** Those are on the default
   branch, they are what the next session's re-derivation (`GATE_REFERENCE.md`) actually
   reads, and they prove the ship far better than a tracker line does. A
   tracker committed at ⏳ is not stale — it is accurate as of the commit it
   is in, which is the last commit that existed before the tag.

   Report the SHIP ✅ state to the user in the message, and hold it in the
   working tree for the rest of the session. It reaches git when the next
   release does.

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
pre-tag report goes above this block (`AUTO_MODE.md`,
checkpoint 2). From the user's local clone of the repo — no `cd`, same reason
as the CI-driven path:
```
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
`git tag v1.2.3` from inside the clone and push again.

Then, once `git ls-remote --tags origin v1.2.3` shows the tag:
```
gh release create v1.2.3 <artifacts> --title "v1.2.3" --notes "..."
```

**Post-ship verification (mandatory):** The gate does not pass without all four:
1. **Tag on remote:** `git ls-remote --tags origin v1.2.3` returns the tag
2. **Release exists:** visible via `gh release view v1.2.3`
3. **PR merged:** state is "merged", not just "closed"
4. **Assets match:** expected artifacts are attached per detection above

**Do not open a tracker-only PR to record SHIP ✅.** Same rule as the
CI-driven path above (step 7): locally the state file is untracked; on a
remote container it shipped inside the release PR at ⏳, and the post-tag line
folds into the next release's PR. The tag, the
release and the changelog entry are the durable record in the meantime.

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

