# Docker Workflow Template

Loaded on demand by the dev-skills skill, **only when project environment
detection matches Docker** (`WORKFLOW_REFERENCE.md`, "Workflow selection
procedure", Step 1). A project that is not Docker never needs this file.

The selection procedure, the audit checklist, workflow linting, template best
practices, dev releases, and the Dependabot configuration stay in
`WORKFLOW_REFERENCE.md`. This file is the template itself.

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
  # A commit reaching the default branch proves nothing on its own about
  # whether CI passed on it -- only that it was merged. This job is the one
  # place that checks both before anything gets built or published.
  gate:
    runs-on: ubuntu-latest
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
          version="$(cat VERSION 2>/dev/null | tr -d '[:space:]')"
          if [ -z "$version" ]; then
            echo "::error::No VERSION file found. Refusing to publish."
            exit 1
          fi
          if [ "v${version}" != "$TAG" ]; then
            echo "::error::Tag $TAG is on a commit that declares ${version}. Merge the release first, then tag the merged commit."
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
