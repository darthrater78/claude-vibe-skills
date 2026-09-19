# Python package Workflow Template

Loaded on demand by the dev-skills skill, **only when project environment
detection matches Python package** (`WORKFLOW_REFERENCE.md`, "Workflow selection
procedure", Step 1). A project that is not Python package never needs this file.

The selection procedure, the audit checklist, workflow linting, template best
practices, dev releases, and the Dependabot configuration stay in
`WORKFLOW_REFERENCE.md`. This file is the template itself.

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
    environment:
      name: pypi
      url: https://pypi.org/p/${{ github.event.repository.name }}
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.x'

      # ADAPT: if the project uses setuptools-scm (or any tool that
      # computes __version__ from the git tag itself), the version matches
      # by construction -- delete this step and say so in a comment instead
      # of generating a check that can't fail.
      - name: Verify tag matches the version in the tagged commit
        env:
          TAG: ${{ github.ref_name }}
        run: |
          set -euo pipefail
          version="$(python3 -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
          if [ -z "$version" ]; then
            echo "::error::No [project.version] found in pyproject.toml. Refusing to publish."
            exit 1
          fi
          if [ "v${version}" != "$TAG" ]; then
            echo "::error::Tag $TAG is on a commit that declares ${version}. Merge the release first, then tag the merged commit."
            exit 1
          fi

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
