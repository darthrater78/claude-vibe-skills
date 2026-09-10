# GitHub Workflow Reference

This is a reference file — not a standalone skill. It is loaded on demand by
the dev-skills skill (`SKILL.md`) in the same way as `SECURITY_REFERENCE.md`,
`QUALITY_REFERENCE.md`, and `SHELL_REFERENCE.md`. It provides template
workflows, audit procedures, and best practices for GitHub Actions. The
primary skill decides when to load it; this file provides the content.

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
     tag-on-default-branch check in release workflows
   - ⚠️ **High** — `persist-credentials: true` (or missing, which defaults to
     true), no concurrency groups (race conditions), no timeouts (stuck builds
     waste runner minutes), release workflow with `cancel-in-progress: true`
     (can cancel a release mid-flight)
   - 📝 **Medium** — CI reimplements build inline instead of calling project
     scripts, no `set -euo pipefail` in multi-line run blocks, no artifact
     verification after upload
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

Before generating any workflow file or presenting commands, check how the
user is working:

- **Remote container sessions** — Claude's working directory is already the
  repo root. No `cd` is needed in any code block. Do not ask for a path.
- **Local sessions** — the user's terminal may or may not be in the repo
  directory. Ask for the clone path as part of the Step 3 questions (below),
  but only if not already known from the shell reference or session start.
  If the user says they don't need a `cd` (they're already in the repo
  directory, or they'll handle it themselves), record that and **omit `cd`
  from all future code blocks in this session.** Do not ask again.

This decision applies to every code block produced by this reference file —
presented git commands, workflow file creation commands, and any other
terminal instructions. `SHELL_REFERENCE.md` already handles `cd` formatting
per shell; this step determines whether to include it at all.

When `cd` is needed, use the format from `SHELL_REFERENCE.md` for the user's
detected shell (PowerShell, Git Bash, Termux, macOS, Linux, WSL). When `cd`
is not needed, start the block directly with the command.

### Step 1 — Detect the project environment

Scan the repo for environment signals. Check these in order and pick the
**first match** (a project can match multiple — pick the primary one, note
the others):

| Environment | Signals | Template |
|---|---|---|
| **Docker** | `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `compose.yaml` | [Docker workflow](#docker-workflow) |
| **Windows app** | `.csproj`, `.sln`, `.vbproj`, `.fsproj`, `*.xaml`, `Setup.iss`, `*.wixproj`, `*.nsis`, MSBuild files | [Windows workflow](#windows-app-workflow) |
| **Android app** | `build.gradle`, `build.gradle.kts`, `settings.gradle`, `AndroidManifest.xml`, `app/` directory with Gradle wrapper | [Android workflow](#android-app-workflow) |
| **Linux app** | `Makefile`, `CMakeLists.txt`, `meson.build`, `configure.ac`, `.deb`/`.rpm` packaging, `setup.py`/`pyproject.toml` with entry points | [Linux workflow](#linux-application-workflow) |
| **Home Assistant** | `manifest.json` with `"domain"` key, `hacs.json`, `custom_components/` directory | [Home Assistant workflow](#home-assistant-integration-workflow) |
| **Python package** | `pyproject.toml`, `setup.py`, `setup.cfg` with package metadata | [Python package workflow](#python-package-workflow) |
| **Node.js** | `package.json` with build scripts | [Node.js workflow](#nodejs-workflow) |
| **Shell scripts** | `*.sh`, `*.bash` files as primary content, no compiled output | [Script workflow](#script-collection-workflow) |

If no signal matches, ask what the project is.

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

1. **Clone path** (local sessions only, if not already known): What is the
   path to your local clone? (Or "not needed" if you're already there / will
   handle `cd` yourself.) If answered "not needed," omit `cd` from all code
   blocks for the rest of the session.
2. **Docker registry** (Docker only): Which registry? (Docker Hub / GitHub
   Container Registry / AWS ECR / other)
3. **Artifact attachment** (when ambiguous): Should compiled artifacts be
   attached to the GitHub release for download?
4. **Signing** (Windows / Android): What signing secrets are needed?
   (certificate name, keystore, etc.)
5. **Release notes source**: Extract from CHANGELOG.md, or generate from PR
   description?
6. **Branch protection**: Which branch is the default? (main / master / other)
7. **Dev releases**: Do you want to be able to push pre-release tags from
   feature branches for testing? (e.g., `v1.0.0-dev.1` builds from your
   working branch, marked as pre-release on GitHub)

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

1. **Generate the workflow files** from the matching template, adapted with
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
   suggest it alongside the new workflows

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
  Third-party and community actions (`docker/*`, `hacs/*`, etc.) must always
  be pinned.
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

## Docker workflow

Two files: a build check and a release workflow.

### CI build check — `.github/workflows/ci.yml`

Triggers on every push to a branch and on pull requests. Builds the image to
verify it compiles. Does NOT push to any registry.

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0

      - name: Build image (no push)
        uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          push: false
          tags: ${{ github.repository }}:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Release workflow — `.github/workflows/release.yml`

Triggers on tag push only. Builds, pushes to registry, and creates a GitHub
release with notes.

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write
  packages: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            exit 1
          fi

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@37fe631027851001ddb9b187196cc803df7f5f0e # v4.3.0

      # ADAPT: change login action and registry URL for your registry
      # Docker Hub: docker/login-action with DOCKERHUB_USERNAME / DOCKERHUB_TOKEN
      # AWS ECR: aws-actions/amazon-ecr-login
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@dbcb813823bdd20940b903addbd779551569679f # v4.6.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@dc802804100637a589fabce1cb79ff13a1411302 # v6.2.0
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}

      - name: Build and push
        uses: docker/build-push-action@53b7df96c91f9c12dcc8a07bcb9ccacbed38856a # v7.3.0
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # ADAPT: add platforms for multi-arch
          # platforms: linux/amd64,linux/arm64
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Extract release notes
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      - name: Create GitHub release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md
```

**Adaptation notes:**
- For Docker Hub: swap login action, set `images:` to `docker.io/<user>/<repo>`
- For multi-arch: uncomment `platforms:` line, increase timeout to 30 min
- For private registries: add registry URL to login and metadata actions

---

## Windows app workflow

### CI build check — `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: windows-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      # ADAPT: choose the right setup action for your framework
      - name: Setup .NET
        uses: actions/setup-dotnet@a98b56852c35b8e3190ac28c8c2271da59106c68 # v6.0.0
        with:
          dotnet-version: '8.0.x'

      - name: Restore dependencies
        run: dotnet restore

      - name: Build
        run: dotnet build --configuration Release --no-restore

      - name: Test
        run: dotnet test --configuration Release --no-build --verbosity normal
```

### Release workflow — `.github/workflows/release.yml`

A compiled artifact MUST be attached to every release for Windows apps.

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: windows-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        shell: bash
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            exit 1
          fi

      - name: Setup .NET
        uses: actions/setup-dotnet@a98b56852c35b8e3190ac28c8c2271da59106c68 # v6.0.0
        with:
          dotnet-version: '8.0.x'

      - name: Build release
        run: dotnet publish --configuration Release --output ./publish

      # ADAPT: adjust the artifact path and name for your project
      - name: Package artifact
        shell: bash
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          cd publish
          7z a -tzip "../${{ github.event.repository.name }}-v${version}-win-x64.zip" .

      - name: Extract release notes
        shell: bash
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      - name: Create GitHub release with artifact
        shell: bash
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          artifact="${{ github.event.repository.name }}-v${version}-win-x64.zip"
          gh release create "$GITHUB_REF_NAME" \
            "$artifact" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md

      - name: Verify release has artifact
        shell: bash
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          assets="$(gh release view "$GITHUB_REF_NAME" --json assets --jq '.assets[].name')"
          echo "Assets: $assets"
          if [ -z "$assets" ]; then
            echo "Release published without any artifacts attached."
            echo "Windows releases MUST have a compiled artifact."
            exit 1
          fi
```

**Adaptation notes:**
- For MSBuild: replace `dotnet` steps with `msbuild` and `Add-MsbuildToPath`
- For InnoSetup: add `iscc` compilation step after build
- For code signing: add certificate import step using `secrets.SIGNING_CERT`
  and `signtool sign` — never check signing certificates into the repo

---

## Linux application workflow

### CI build check — `.github/workflows/ci.yml`

Includes script consistency checking (shellcheck) for any shell scripts in
the project.

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Check shell script consistency
        run: |
          set -euo pipefail
          scripts=$(find . -name '*.sh' -o -name '*.bash' | grep -v node_modules | grep -v .git || true)
          if [ -n "$scripts" ]; then
            echo "Checking scripts with shellcheck..."
            echo "$scripts" | xargs shellcheck --severity=warning
            echo "All scripts passed shellcheck."
          else
            echo "No shell scripts found to check."
          fi

      # ADAPT: add language-specific linters
      # Python: flake8, ruff, mypy
      # Go: golangci-lint
      # Rust: cargo clippy

  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      # ADAPT: replace with your build system
      - name: Build
        run: |
          set -euo pipefail
          make build

      - name: Test
        run: |
          set -euo pipefail
          make test
```

### Release workflow — `.github/workflows/release.yml`

Whether to attach artifacts depends on the project — ask the user once and
record the answer (see [workflow selection procedure](#step-3--ask-all-questions-in-one-turn)).

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            exit 1
          fi

      - name: Check shell scripts
        run: |
          set -euo pipefail
          scripts=$(find . -name '*.sh' -o -name '*.bash' | grep -v node_modules | grep -v .git || true)
          if [ -n "$scripts" ]; then
            echo "$scripts" | xargs shellcheck --severity=warning
          fi

      # ADAPT: uncomment and adjust if artifacts should be attached
      # - name: Build release artifact
      #   run: |
      #     set -euo pipefail
      #     make release
      #     # or: python -m build
      #     # or: cargo build --release

      - name: Extract release notes
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      - name: Create GitHub release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          # ADAPT: add artifact path after "$GITHUB_REF_NAME" if attaching:
          #   gh release create "$GITHUB_REF_NAME" \
          #     "dist/myapp-${GITHUB_REF_NAME#v}-linux-x64.tar.gz" \
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md
```

---

## Home Assistant integration workflow

Home Assistant integrations typically need HACS validation on PRs and a
tagged release with **no artifact** — HACS pulls directly from the tagged
source.

### CI build check — `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: HACS validation
        uses: hacs/action@main
        with:
          category: integration

      # ADAPT: add hassfest validation if needed
      # - name: Hassfest validation
      #   uses: home-assistant/actions/hassfest@master

      - name: Check shell scripts
        run: |
          set -euo pipefail
          scripts=$(find . -name '*.sh' -o -name '*.bash' | grep -v node_modules | grep -v .git || true)
          if [ -n "$scripts" ]; then
            echo "$scripts" | xargs shellcheck --severity=warning
          fi
```

### Release workflow — `.github/workflows/release.yml`

No artifact — HACS downloads the tagged source directly.

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            exit 1
          fi

      - name: Extract release notes
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      - name: Create GitHub release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md
```

---

## Script collection workflow

For repos that are primarily shell scripts, Python utilities, or other
interpreted code. The key difference from compiled projects: the CI check
focuses on **linting and consistency**, not compilation.

Whether to attach an artifact (e.g., a tarball for easy download) depends on
the project — ask the user once.

### CI build check — `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Check shell script consistency
        run: |
          set -euo pipefail
          scripts=$(find . -name '*.sh' -o -name '*.bash' | grep -v node_modules | grep -v .git || true)
          if [ -n "$scripts" ]; then
            echo "Checking scripts with shellcheck..."
            echo "$scripts" | xargs shellcheck --severity=warning
            echo "All scripts passed shellcheck."
          else
            echo "No shell scripts found to check."
          fi

      # ADAPT: add for Python scripts
      # - name: Lint Python
      #   run: |
      #     pip install ruff
      #     ruff check .

      # ADAPT: add for YAML-heavy repos
      # - name: Lint YAML
      #   run: |
      #     pip install yamllint
      #     yamllint .
```

### Release workflow — `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            exit 1
          fi

      - name: Validate scripts before release
        run: |
          set -euo pipefail
          scripts=$(find . -name '*.sh' -o -name '*.bash' | grep -v node_modules | grep -v .git || true)
          if [ -n "$scripts" ]; then
            echo "$scripts" | xargs shellcheck --severity=warning
          fi

      - name: Extract release notes
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      # ADAPT: uncomment to attach a download artifact
      # - name: Package scripts
      #   run: |
      #     version="${GITHUB_REF_NAME#v}"
      #     tar czf "${{ github.event.repository.name }}-v${version}.tar.gz" \
      #       --exclude='.git' --exclude='.github' .

      - name: Create GitHub release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          # ADAPT: add artifact path if attaching a tarball:
          #   gh release create "$GITHUB_REF_NAME" \
          #     "${{ github.event.repository.name }}-v${version}.tar.gz" \
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md
```

---

## Android app workflow

For Android apps built with Gradle. The APK is the artifact — users download
it from the GitHub release to install on their device.

### CI build check — `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up JDK
        uses: actions/setup-java@c5195efecf7bdfc987ee8bae7a71cb8b11521c00 # v4.7.1
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@ac638b010cf753c3731813f9302c85b32d0b30b0 # v4.4.1

      - name: Build debug APK
        run: ./gradlew assembleDebug

      - name: Run unit tests
        run: ./gradlew test

      # ADAPT: add lint check
      # - name: Lint
      #   run: ./gradlew lint
```

### Release workflow — `.github/workflows/release.yml`

The APK MUST be attached to every release — users download it directly to
install on their device. See also [dev releases](#dev-releases) for
pre-release builds from feature branches.

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          # Pre-release tags (v1.0.0-dev.1, v1.0.0-beta.1) skip this check
          # so dev builds can happen from feature branches.
          case "$GITHUB_REF_NAME" in
            *-dev.*|*-alpha.*|*-beta.*|*-rc.*) echo "Pre-release tag — skipping branch check."; exit 0 ;;
          esac
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            echo "Use a pre-release tag (e.g., v1.0.0-dev.1) for feature branch builds."
            exit 1
          fi

      - name: Set up JDK
        uses: actions/setup-java@c5195efecf7bdfc987ee8bae7a71cb8b11521c00 # v4.7.1
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@ac638b010cf753c3731813f9302c85b32d0b30b0 # v4.4.1

      # ADAPT: for signed release builds, decode the keystore from a secret:
      # - name: Decode keystore
      #   env:
      #     KEYSTORE_BASE64: ${{ secrets.KEYSTORE_BASE64 }}
      #   run: |
      #     echo "$KEYSTORE_BASE64" | base64 -d > app/release.keystore
      #
      # - name: Build signed release APK
      #   env:
      #     KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
      #     KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
      #     KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
      #   run: ./gradlew assembleRelease
      #
      # - name: Clean up keystore
      #   if: always()
      #   run: rm -f app/release.keystore

      - name: Build release APK
        run: ./gradlew assembleRelease

      - name: Find APK
        id: apk
        run: |
          set -euo pipefail
          apk=$(find app/build/outputs/apk/release -name '*.apk' -type f | head -1)
          if [ -z "$apk" ]; then
            echo "No APK found in app/build/outputs/apk/release/"
            exit 1
          fi
          echo "path=$apk" >> "$GITHUB_OUTPUT"
          echo "Found APK: $apk"

      - name: Extract release notes
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      - name: Create GitHub release with APK
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          prerelease_flag=""
          case "$GITHUB_REF_NAME" in
            *-dev.*|*-alpha.*|*-beta.*|*-rc.*) prerelease_flag="--prerelease" ;;
          esac
          gh release create "$GITHUB_REF_NAME" \
            "${{ steps.apk.outputs.path }}" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md \
            $prerelease_flag

      - name: Verify release has APK
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          assets="$(gh release view "$GITHUB_REF_NAME" --json assets --jq '.assets[].name')"
          echo "Assets: $assets"
          echo "$assets" | grep -q '\.apk$' || {
            echo "Release published without an APK attached."
            echo "Android releases MUST have an APK artifact."
            exit 1
          }
```

**Adaptation notes:**
- For signed builds: uncomment the keystore steps above — store the keystore
  as a base64-encoded secret and always delete it after use
- For AAB (App Bundle): change `assembleRelease` to `bundleRelease` and
  adjust the find path to look for `*.aab`
- For multiple build variants: use a matrix strategy or build both debug and
  release in the same job
- **Never commit a keystore or signing key to the repo** — always use GitHub
  Secrets

---

## Python package workflow

For Python packages published to PyPI. Uses OIDC trusted publishing — no API
keys or tokens stored as secrets. The user configures a "trusted publisher" on
PyPI once, and the workflow authenticates via GitHub's OIDC identity.

### CI build check — `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.x'

      - name: Lint
        run: |
          set -euo pipefail
          pip install ruff
          ruff check .

  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.x'

      - name: Install and test
        run: |
          set -euo pipefail
          pip install -e ".[test]"
          pytest

      # ADAPT: add matrix testing for multiple Python versions
      # strategy:
      #   matrix:
      #     python-version: ['3.10', '3.11', '3.12', '3.13']
```

### Release workflow — `.github/workflows/release.yml`

Uses OIDC trusted publishing — the PyPI project must have this repository
configured as a trusted publisher. No API token secret needed.

**Setting up trusted publishing (one-time):**
1. Go to your project on pypi.org → Settings → Publishing
2. Add a new publisher: GitHub, your owner/repo, workflow `release.yml`,
   environment `pypi`
3. That's it — no secrets to manage or rotate

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write
  id-token: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment:
      name: pypi
      url: https://pypi.org/p/${{ github.event.repository.name }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            exit 1
          fi

      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.x'

      - name: Build package
        run: |
          set -euo pipefail
          pip install build
          python -m build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@dc37677b2e1c63e2034f94d8a5b11f265b73ba33 # v1.14.2

      - name: Extract release notes
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      - name: Create GitHub release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md
```

**Adaptation notes:**
- For packages not on PyPI: remove the `pypa/gh-action-pypi-publish` step and
  attach the wheel/sdist as release artifacts instead
- For TestPyPI: add a separate job with `repository-url: https://test.pypi.org/legacy/`
  and a `testpypi` environment
- For private registries: replace the publish action with `twine upload` using
  a `TWINE_PASSWORD` secret

---

## Node.js workflow

### CI build check — `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Node.js
        uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
        with:
          node-version: 'lts/*'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint --if-present

      - name: Test
        run: npm test --if-present

      # ADAPT: add matrix testing for multiple Node versions
      # strategy:
      #   matrix:
      #     node-version: [18, 20, 22]
```

### Release workflow — `.github/workflows/release.yml`

Publishes to npm. Unlike PyPI, npm does not support OIDC trusted publishing
yet, so an `NPM_TOKEN` secret is required. Generate one at npmjs.com →
Access Tokens → Generate New Token (Automation type).

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Verify tag is on default branch
        env:
          DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
        run: |
          set -euo pipefail
          if ! git merge-base --is-ancestor "$GITHUB_SHA" "origin/$DEFAULT_BRANCH"; then
            echo "Tag $GITHUB_REF_NAME is not on $DEFAULT_BRANCH."
            echo "Releases come from the default branch only."
            exit 1
          fi

      - name: Set up Node.js
        uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
        with:
          node-version: 'lts/*'
          registry-url: 'https://registry.npmjs.org'

      - name: Install and build
        run: |
          set -euo pipefail
          npm ci
          npm run build --if-present

      - name: Publish to npm
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: npm publish

      - name: Extract release notes
        run: |
          set -euo pipefail
          version="${GITHUB_REF_NAME#v}"
          if [ -f CHANGELOG.md ]; then
            awk -v v="$version" '
              $0 ~ "^## \\[" v "\\]" { flag = 1; next }
              flag && /^## \[/ { exit }
              flag { print }
            ' CHANGELOG.md > release-notes.md
          fi
          if [ ! -s release-notes.md ]; then
            echo "Release $version" > release-notes.md
          fi

      - name: Create GitHub release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md
```

**Adaptation notes:**
- For scoped packages: add `--access public` to `npm publish` if the package
  is under an org scope and should be public
- For GitHub Packages: change `registry-url` to `https://npm.pkg.github.com`
  and use `GITHUB_TOKEN` instead of `NPM_TOKEN`
- For pnpm or yarn: replace `npm ci` with the equivalent install command and
  adjust the cache setting in `setup-node`

---

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

**What it does:** Dependabot watches the action versions in your workflow
files. When a new version is released, it opens a PR that updates the SHA
pin and version comment. You review the PR, confirm CI passes, and merge.

**Recommend adding this file to every project with GitHub Actions workflows.**

### `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    # Group all action updates into a single PR to reduce noise
    groups:
      actions:
        patterns:
          - "*"
```

**Adaptation notes:**
- Change `interval` to `"monthly"` for less-active projects
- Remove the `groups` section if you prefer one PR per action update (easier
  to review individually but more PRs)
- Add `reviewers:` to assign specific people to review these PRs
- For monorepos with workflows in subdirectories, add multiple entries with
  different `directory:` values

**What the PRs look like:**

Dependabot will open PRs like:
> Bump actions/checkout from v7.0.0 to v7.0.1
>
> Updates actions/checkout from 3d3c42e... (v7.0.0) to abc1234... (v7.0.1)
> - [Release notes](link)
> - [Changelog](link)
> - [Commits](link)

The PR updates both the SHA and the version comment automatically.

---

## Integration with GATE_REFERENCE.md

This reference file supports the workflow detection in session start (step 6)
and Gate 6 (Ship). When the skill detects a missing workflow:

1. **Load this file** (`WORKFLOW_REFERENCE.md`)
2. **Run the detection procedure** (Step 1 above)
3. **Ask all questions in one turn** (Step 3 above)
4. **Generate the workflow** from the matching template, adapted with the
   user's answers
5. **Validate the generated workflow** — check that:
   - All action references use pinned commit SHAs
   - `persist-credentials: false` is set on checkout
   - Concurrency groups are present
   - Timeouts are set on every job
   - The tag-on-default-branch check is present in release workflows
   - Release notes extraction is present
   - The generated workflow calls the project's own build scripts where they
     exist, rather than reimplementing the build inline

### Workflow review checklist

When reviewing an existing workflow (user request or drift detection), check
every item:

- [ ] Actions pinned to commit SHAs (not version tags)
- [ ] `persist-credentials: false` on all checkouts
- [ ] Least-privilege `permissions:` block
- [ ] Concurrency groups (cancel-in-progress for CI, never for release)
- [ ] Timeouts on all jobs
- [ ] Tag-on-default-branch verification in release workflows
- [ ] Release notes extracted from CHANGELOG.md or PR body
- [ ] CI calls project's own scripts, not inline reimplementations
- [ ] Secrets used only in `env:` blocks, never in `run:` strings
- [ ] Artifact verification after upload (release workflows)
- [ ] Shell scripts checked with shellcheck (Linux/script projects)
- [ ] `set -euo pipefail` in multi-line run blocks
- [ ] Dependabot configured for action updates (`.github/dependabot.yml`)
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
