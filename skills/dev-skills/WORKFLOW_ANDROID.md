# Android app Workflow Template

Loaded on demand by the dev-skills skill, **only when project environment
detection matches Android app** (`WORKFLOW_REFERENCE.md`, "Workflow selection
procedure", Step 1). A project that is not Android app never needs this file.

The selection procedure, the audit checklist, workflow linting and template
best practices stay in `WORKFLOW_REFERENCE.md`; dev releases are in
`WORKFLOW_DEVRELEASE.md` and the Dependabot configuration in
`WORKFLOW_DEPENDABOT.md`. This file is the template itself.

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
  # changes: the job from WORKFLOW_REFERENCE.md, "Job-level change detection"
  build:
    needs: changes
    if: ${{ !cancelled() && needs.changes.outputs.code != 'false' }}
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up JDK
        uses: actions/setup-java@de7274f081f381c8f8158605e0321c36c376e2e6 # v6.0.1
        with:
          distribution: 'temurin'
          java-version: '17'

      # Also validates every Gradle wrapper jar in the repo against Gradle's
      # published checksums (validate-wrappers defaults to true), so a
      # tampered gradle-wrapper.jar fails here instead of running.
      # cache-provider: basic is the MIT-licensed actions/cache provider; the
      # default "enhanced" one is proprietary and free only on public repos.
      # ADAPT: a job that caches with setup-java (`cache: gradle`) instead of
      # setup-gradle still validates the wrapper, with the validation-only
      # action, before its first ./gradlew. Every job that runs ./gradlew needs
      # one or the other:
      # - name: Validate Gradle wrapper
      #   uses: gradle/actions/wrapper-validation@9c971963bec38e04b3d30dcc455b5382be2fdbfb # v6.3.0
      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@9c971963bec38e04b3d30dcc455b5382be2fdbfb # v6.3.0
        with:
          cache-provider: basic

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
install on their device. See also dev releases (`WORKFLOW_DEVRELEASE.md`) for
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
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      # ADAPT: if versionName is computed (e.g. from `git describe`, a
      # Flutter `flutter.versionName`, or a CI-injected property) rather
      # than a literal string here, this can't fail by construction --
      # delete this step and say so in a comment instead.
      - name: Verify tag matches the version in the tagged commit
        env:
          TAG: ${{ github.ref_name }}
        run: |
          set -euo pipefail
          version="$(sed -n 's/.*versionName *=\? *"\([^"]*\)".*/\1/p' app/build.gradle* | head -1)"
          if [ -z "$version" ]; then
            echo "::error::No versionName found in app/build.gradle(.kts). Refusing to publish."
            exit 1
          fi
          if [ "v${version}" != "$TAG" ]; then
            echo "::error::Tag $TAG is on a commit that declares ${version}. Merge the release first, then tag the merged commit."
            exit 1
          fi

      - name: Set up JDK
        uses: actions/setup-java@de7274f081f381c8f8158605e0321c36c376e2e6 # v6.0.1
        with:
          distribution: 'temurin'
          java-version: '17'

      # Also validates every Gradle wrapper jar in the repo against Gradle's
      # published checksums (validate-wrappers defaults to true), so a
      # tampered gradle-wrapper.jar fails here instead of running.
      # cache-provider: basic is the MIT-licensed actions/cache provider; the
      # default "enhanced" one is proprietary and free only on public repos.
      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@9c971963bec38e04b3d30dcc455b5382be2fdbfb # v6.3.0
        with:
          cache-provider: basic

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

      # The path goes through env:, never ${{ }} inside run: -- an expression
      # there is pasted into the script as code before bash ever sees it.
      - name: Create GitHub release with APK
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          APK_PATH: ${{ steps.apk.outputs.path }}
        run: |
          set -euo pipefail
          prerelease_flag=""
          case "$GITHUB_REF_NAME" in
            *-dev.*|*-alpha.*|*-beta.*|*-rc.*) prerelease_flag="--prerelease" ;;
          esac
          gh release create "$GITHUB_REF_NAME" \
            "$APK_PATH" \
            --title "$GITHUB_REF_NAME" \
            --notes-file release-notes.md \
            $prerelease_flag

      - name: Verify release has APK
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
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
