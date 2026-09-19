# Home Assistant integration Workflow Template

Loaded on demand by the dev-skills skill, **only when project environment
detection matches Home Assistant integration** (`WORKFLOW_REFERENCE.md`, "Workflow selection
procedure", Step 1). A project that is not Home Assistant integration never needs this file.

The selection procedure, the audit checklist, workflow linting, template best
practices, dev releases, and the Dependabot configuration stay in
`WORKFLOW_REFERENCE.md`. This file is the template itself.

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
        uses: hacs/action@main # intentionally unpinned — see Template best practices, Security
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
    timeout-minutes: 10
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
          version="$(jq -r .version custom_components/*/manifest.json)"
          if [ -z "$version" ] || [ "$version" = "null" ]; then
            echo "::error::No version found in custom_components/*/manifest.json. Refusing to publish."
            exit 1
          fi
          if [ "v${version}" != "$TAG" ]; then
            echo "::error::Tag $TAG is on a commit that declares ${version}. Merge the release first, then tag the merged commit."
            exit 1
          fi
          # ADAPT: a repo with more than one integration has more than one
          # manifest.json -- name the specific one instead of globbing.

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
