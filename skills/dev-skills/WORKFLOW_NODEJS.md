# Node.js Workflow Template

Loaded on demand by the dev-skills skill, **only when project environment
detection matches Node.js** (`WORKFLOW_REFERENCE.md`, "Workflow selection
procedure", Step 1). A project that is not Node.js never needs this file.

The selection procedure, the audit checklist, workflow linting, template best
practices, dev releases, and the Dependabot configuration stay in
`WORKFLOW_REFERENCE.md`. This file is the template itself.

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

Uses OIDC trusted publishing (GA since July 2025) — the npm package must
have this repository configured as a trusted publisher. No `NPM_TOKEN`
secret to generate or rotate. Requires npm CLI 11.5.1+ and Node 22.14.0+;
the pinned `node-version` below clears both.

**Setting up trusted publishing (one-time):**
1. On npmjs.com, go to the package → Settings → Trusted Publisher
2. Add a GitHub Actions publisher: organization/user, repository, workflow
   filename `release.yml` (environment name is optional — only needed if
   you also want GitHub deployment protection rules on the `npm`
   environment below)
3. That's it — no secret to manage

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
      name: npm
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
          version="$(node -p "require('./package.json').version")"
          if [ -z "$version" ]; then
            echo "::error::No version found in package.json. Refusing to publish."
            exit 1
          fi
          if [ "v${version}" != "$TAG" ]; then
            echo "::error::Tag $TAG is on a commit that declares ${version}. Merge the release first, then tag the merged commit."
            exit 1
          fi

      - name: Set up Node.js
        uses: actions/setup-node@820762786026740c76f36085b0efc47a31fe5020 # v7.0.0
        with:
          node-version: '22.14.0'
          registry-url: 'https://registry.npmjs.org'

      - name: Install and build
        run: |
          set -euo pipefail
          npm ci
          npm run build --if-present

      # npm CLI auto-detects the OIDC environment (id-token: write, above)
      # and authenticates with it before falling back to a token — no
      # NODE_AUTH_TOKEN needed when trusted publishing is configured.
      - name: Publish to npm
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
  and use `GITHUB_TOKEN` instead — trusted publishing is npmjs.com-specific
- For pnpm or yarn: replace `npm ci` with the equivalent install command and
  adjust the cache setting in `setup-node`
- **No trusted-publisher access, or a registry without OIDC support:** fall
  back to an `NPM_TOKEN` secret (npmjs.com → Access Tokens → Generate New
  Token, Automation type), pass it as `NODE_AUTH_TOKEN` in the publish
  step's `env:`, and drop `id-token: write` from `permissions`.

---
