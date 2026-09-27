# Docker Workflow Template

Loaded on demand by the dev-skills skill, **only when project environment
detection matches Docker** (`WORKFLOW_REFERENCE.md`, "Workflow selection
procedure", Step 1). A project that is not Docker never needs this file.

The selection procedure, the audit checklist, workflow linting and template
best practices stay in `WORKFLOW_REFERENCE.md`; dev releases are in
`WORKFLOW_DEVRELEASE.md` and the Dependabot configuration in
`WORKFLOW_DEPENDABOT.md`. This file is the template itself.

---

## Docker workflow

Three workflows (a build check, a release and a weekly image scan) plus two
Trivy files, `trivy.yaml` and `.trivyignore.yaml` (below). The release scans
the exact pushed digest **before** any version tag points at it, so an image
that fails the scan is never published under a version. The weekly scan
catches CVEs published after release against an image that hasn't changed.
Trivy is for projects that **ship a container image**. Elsewhere, the
ecosystem audit, Dependabot and dependency review already cover what it
would find, and it only adds duplicate alerts.

**Pin `trivy-action` by SHA, never by tag.** Its tags were hijacked in a
supply-chain attack in early 2026, which is the exact case SHA pinning
protects against. Pin the Trivy binary too (`version:`), so the action's
default can't change what runs.

### CI build check — `.github/workflows/ci.yml`

Triggers on every push to a branch and on pull requests. Builds the image,
scans it, and does NOT push to any registry.

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
        uses: docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1

      - name: Build image (no push)
        uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
        with:
          context: .
          push: false
          load: true
          tags: ci-image:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # Reports only: a CVE in the base image isn't this PR's doing, so it
      # doesn't fail the check. The release gate is what blocks.
      - name: Scan image
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: ci-image:test
          version: v0.74.0
          trivy-config: trivy.yaml
          trivyignores: .trivyignore.yaml
          format: table
          exit-code: '0'
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
  security-events: write  # the SARIF upload; drop it with those steps

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

jobs:
  # A commit reaching the default branch proves nothing on its own about
  # whether CI passed on it -- only that it was merged. This job is the one
  # place that checks both before anything gets built or published.
  gate:
    runs-on: ubuntu-latest
    # The CI wait loop below gives up after 30 minutes; this is the backstop.
    timeout-minutes: 35
    permissions:
      actions: read
      contents: read
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

      - name: Require a passing CI run for this commit
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
          SHA: ${{ github.sha }}
        run: |
          set -euo pipefail
          # Tagging right after pushing the branch is normal, and CI takes
          # minutes -- so an in-progress run is waited on, not treated as a
          # failure. This job never runs CI itself: it only asks whether
          # ci.yml already ran and passed for this exact commit.
          deadline=$(( $(date +%s) + 1800 ))
          while true; do
            runs=$(gh api \
              "repos/${REPO}/actions/workflows/ci.yml/runs?head_sha=${SHA}&per_page=100" \
              --jq '.workflow_runs[] | "\(.status) \(.conclusion) \(.html_url)"')

            if [ -z "$runs" ]; then
              echo "::error::CI has never run for ${SHA}, so nothing has tested this commit."
              echo "Push the branch so CI runs on it, or dispatch it by hand" >&2
              echo "(Actions -> CI -> Run workflow), then re-tag." >&2
              exit 1
            fi

            if printf '%s\n' "$runs" | awk '$2 == "success" { hit = 1 } END { exit !hit }'; then
              echo "CI passed for ${SHA}."
              exit 0
            fi

            unfinished=$(printf '%s\n' "$runs" | awk '$1 != "completed"' | wc -l)
            if [ "$unfinished" -eq 0 ]; then
              echo "::error::CI ran for ${SHA} and did not pass. Refusing to release."
              printf '%s\n' "$runs" | sed 's/^/  /' >&2
              exit 1
            fi

            echo "CI is still running for ${SHA} (${unfinished} unfinished) -- waiting."
            if [ "$(date +%s)" -ge "$deadline" ]; then
              echo "::error::Timed out waiting for CI on ${SHA} to finish."
              exit 1
            fi
            sleep 20
          done

  release:
    needs: gate
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      # ADAPT: only needed if the app has its own version file/constant
      # separate from the git tag. If every version signal here (image
      # tags, release notes) is derived from $GITHUB_REF_NAME as it already
      # is above, there is nothing to compare against -- delete this step
      # and say so in a comment instead of leaving a check that can't fail.
      - name: Verify tag matches the version in the tagged commit
        env:
          TAG: ${{ github.ref_name }}
        run: |
          set -euo pipefail
          version="$(tr -d '[:space:]' 2>/dev/null < VERSION || true)"
          if [ -z "$version" ]; then
            echo "::error::No VERSION file found. Refusing to publish."
            exit 1
          fi
          if [ "v${version}" != "$TAG" ]; then
            echo "::error::Tag $TAG is on a commit that declares ${version}. Merge the release first, then tag the merged commit."
            exit 1
          fi

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1

      # ADAPT: change login action and registry URL for your registry
      # Docker Hub: docker/login-action with DOCKERHUB_USERNAME / DOCKERHUB_TOKEN
      # AWS ECR: aws-actions/amazon-ecr-login
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@dbcb813823bdd20940b903addbd779551569679f # v4.6.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # Registries need a lowercase name; the owner may not be.
      - name: Image name
        id: image
        run: echo "name=ghcr.io/${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@dc802804100637a589fabce1cb79ff13a1411302 # v6.2.0
        with:
          images: ${{ steps.image.outputs.name }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}

      # Pushed by digest only: no version tag points at it until it passes
      # the scan below.
      - name: Build and push by digest
        id: build
        uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
        with:
          context: .
          outputs: type=image,name=${{ steps.image.outputs.name }},push-by-digest=true,name-canonical=true,push=true
          labels: ${{ steps.meta.outputs.labels }}
          # ADAPT: add platforms for multi-arch
          # platforms: linux/amd64,linux/arm64
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # Two runs over the same digest. This one never fails: it writes SARIF
      # for the repo's Security tab. ADAPT: a private repo without GitHub
      # Advanced Security can't take SARIF; drop this step and the upload.
      - name: Scan image (SARIF report)
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: ${{ steps.image.outputs.name }}@${{ steps.build.outputs.digest }}
          version: v0.74.0
          trivy-config: trivy.yaml
          trivyignores: .trivyignore.yaml
          format: sarif
          output: trivy-results.sarif
          exit-code: '0'

      - name: Upload scan to the Security tab
        if: always()
        uses: github/codeql-action/upload-sarif@2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2 # v4.38.2
        with:
          sarif_file: trivy-results.sarif
          category: trivy-image

      # This run is the gate: a fixable HIGH or CRITICAL stops the release
      # here, before any version tag exists.
      - name: Scan image (gate)
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: ${{ steps.image.outputs.name }}@${{ steps.build.outputs.digest }}
          version: v0.74.0
          skip-setup-trivy: true
          trivy-config: trivy.yaml
          trivyignores: .trivyignore.yaml
          format: table
          exit-code: '1'

      - name: Tag the scanned image
        env:
          IMAGE: ${{ steps.image.outputs.name }}
          DIGEST: ${{ steps.build.outputs.digest }}
          TAGS: ${{ steps.meta.outputs.tags }}
        run: |
          set -euo pipefail
          args=()
          while IFS= read -r tag; do
            [ -n "$tag" ] && args+=(-t "$tag")
          done <<< "$TAGS"
          docker buildx imagetools create "${args[@]}" "${IMAGE}@${DIGEST}"

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

### Weekly image scan — `.github/workflows/image-scan.yml`

Rescans the newest published release every week and uploads the result to the
Security tab. It never fails: its job is to surface new CVEs, and fixing one
is a new release with a bumped base image.

```yaml
name: Image scan

on:
  schedule:
    - cron: '17 6 * * 1'  # Mondays; ADAPT the time
  workflow_dispatch:

permissions:
  contents: read
  packages: read
  security-events: write

concurrency:
  group: image-scan
  cancel-in-progress: true

jobs:
  scan:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      # The newest stable version tag, never a floating :latest.
      - name: Find the newest release
        id: image
        run: |
          set -euo pipefail
          tag="$(git tag --list 'v*' --sort=-v:refname | grep -v -- '-' | head -n1 || true)"
          if [ -z "$tag" ]; then
            echo "::error::No release tag yet, so there is no published image to scan."
            exit 1
          fi
          echo "ref=ghcr.io/${GITHUB_REPOSITORY,,}:${tag#v}" >> "$GITHUB_OUTPUT"

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@dbcb813823bdd20940b903addbd779551569679f # v4.6.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Scan the published image
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: ${{ steps.image.outputs.ref }}
          version: v0.74.0
          trivy-config: trivy.yaml
          trivyignores: .trivyignore.yaml
          format: sarif
          output: trivy-results.sarif
          exit-code: '0'

      - name: Upload scan to the Security tab
        if: always()
        uses: github/codeql-action/upload-sarif@2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2 # v4.38.2
        with:
          sarif_file: trivy-results.sarif
          category: trivy-weekly
```

### Trivy configuration — `trivy.yaml` and `.trivyignore.yaml`

Both files sit in the repo root. `trivy.yaml` decides what fails:

```
severity:
  - HIGH
  - CRITICAL
scan:
  scanners:
    - vuln
pkg:
  types:
    - os          # the base image's packages; app dependencies are Gate 3's audit
vulnerability:
  ignore-unfixed: true   # nothing to bump to yet; Gate 3 still reports it
```

`.trivyignore.yaml` accepts one finding at a time, and every entry carries a
reason and an expiry, so an accepted risk comes back for review instead of
staying hidden:

```
vulnerabilities:
  - id: CVE-2026-12345
    statement: "libfoo is in the base image but never loaded; waived by <user> 2026-09-27"
    expired_at: 2026-12-31
```

An entry is a Gate 3 waiver (`SECURITY_GATE.md`, "Finding lifecycle"): the
user decides it, and it re-opens when `expired_at` passes. Start with an
empty `vulnerabilities: []`.

**Adaptation notes:**
- **A scan failure is the base image's**, nearly always: bump the `FROM` tag
  (or its digest) to the newest patch, rebuild, and re-tag
- **Optional, off by default to keep the noise down:** `scanners: [vuln,
  misconfig]` in `trivy.yaml` also checks the Dockerfile and compose files
  (running as root, no `HEALTHCHECK`), and a
  `format: cyclonedx` run on the gated digest writes an SBOM to attach to
  the release (the provenance offer, `WORKFLOW_REFERENCE.md`, step 4)
- **A failed gate leaves an untagged digest** in the registry. It can't be
  pulled by version, and the registry's untagged-image cleanup removes it
- For Docker Hub: swap login action, set `images:` to `docker.io/<user>/<repo>`
- For multi-arch: uncomment `platforms:` line, increase timeout to 30 min.
  Trivy scans the runner's platform from the manifest list; add
  `TRIVY_PLATFORM: linux/arm64` in a second gate step's `env:` to scan another
- For private registries: add registry URL to login and metadata actions
- **For a floating `:dev`/`:latest`-style tag** (this template's
  `docker/metadata-action` block already handles the standard `:latest`
  case): if the project instead hand-rolls a moving tag — e.g. a separate
  `:dev` channel tracking prerelease builds — guard it against ever moving
  backward. Nothing about a tag push says it's the newest version: backfilling
  a version that was skipped, or re-tagging an old commit, republishes an
  older build through this same workflow, and without a check that build
  claims the floating tag and silently downgrades whoever pulls it. Compare
  the version being built against every existing tag of its own kind (dev
  against dev, stable against stable — don't compare across kinds; a plain
  `sort -V` places `1.0.0` before `1.0.0-dev.2`, which is correct for neither):
  ```bash
  versions="$(git ls-remote --tags origin 'refs/tags/v*' \
    | sed 's#.*refs/tags/v##' | grep -v '\^{}$')"
  newest_dev="$(printf '%s\n' "$versions" | { grep -- '-dev' || true; } | sort -V | tail -n1)"
  if [ "$version" = "$newest_dev" ]; then
    tags="${tags}"$'\n'"${image}:dev"     # only move :dev when this IS the newest dev build
  fi
  ```

---
