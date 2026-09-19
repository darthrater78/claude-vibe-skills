# Linux application Workflow Template

Loaded on demand by the dev-skills skill, **only when project environment
detection matches Linux application** (`WORKFLOW_REFERENCE.md`, "Workflow selection
procedure", Step 1). A project that is not Linux application never needs this file.

The selection procedure, the audit checklist, workflow linting, template best
practices, dev releases, and the Dependabot configuration stay in
`WORKFLOW_REFERENCE.md`. This file is the template itself.

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
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

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

      # No shellcheck step here: ci.yml's lint job already ran it, and the
      # gate job above requires that exact run to have passed for this
      # commit before this job starts. Re-running it would only re-prove
      # what the gate already checked (see "Require a passing CI run", above).

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
