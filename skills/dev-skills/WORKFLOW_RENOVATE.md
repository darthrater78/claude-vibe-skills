# Renovate Reference: the dependency watch off GitHub

Loaded by the dev-skills skill **only on a self-hosted forge, when the repo
needs its dependency watch set up, checked or fixed**: onboarding step 7 of
`FORGE_REFERENCE.md`, or the Gate 3 finding for a missing or stale watch. It
does the job `WORKFLOW_DEPENDABOT.md` does on GitHub. Section numbers point at
`SKILL.md`.

**Renovate is the watch half only.** It opens update PRs. The alerts half is
the `osv-scanner` run at every Gate 3 (`FORGE_REFERENCE.md`, onboarding step
7), because Gitea, Forgejo and GitLab below Ultimate have no alerts feed of
their own.

---

## 1. Is one running already?

Two reads, chained into one call (§5.1):

- **A config:** `renovate.json`, `renovate.json5`, `.renovaterc`,
  `.renovaterc.json`, `.github/renovate.json`, `.gitlab/renovate.json`, or a
  `"renovate"` key in `package.json`.
- **Proof that it runs:** its **Dependency Dashboard** issue, updated within
  the last 7 days, or the schedule's recent runs (§2) in the CI history. No
  Renovate PRs proves nothing, since a bot that never runs opens none either
  (§2, "Absence of a verdict").

| Found | Gate 3 |
|---|---|
| Config, and a run in the last 7 days | ✅ `deps: renovate (dashboard <date>)` |
| Config, but no run in 7 days, or a failed last run | Medium: the watch is configured but not running |
| No config | Medium, like a missing `dependabot.yml` |

## 2. The repo config

Create `renovate.json` at the repo root (in a shared repo the folder's
owners can't add one, so report it, `SCOPED_REPO.md`):

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended", "helpers:pinGitHubActionDigests"],
  "github-actions": {
    "managerFilePatterns": ["/(^|/)\\.(github|gitea|forgejo)/workflows/[^/]+\\.ya?ml$/"]
  },
  "minimumReleaseAge": "3 days",
  "prConcurrentLimit": 5,
  "packageRules": [
    { "matchUpdateTypes": ["major"], "dependencyDashboardApproval": true }
  ]
}
```

- **Every ecosystem is on by default.** `config:recommended` detects each
  manifest in the repo. Check the first Dependency Dashboard: every ecosystem
  in the repo is listed under "Detected dependencies". A missing one is a
  config gap, not a clean bill.
- **Workflow pins stay SHAs.** `helpers:pinGitHubActionDigests` keeps
  `uses:` on a 40-character SHA with the version as a comment, which is the B8
  rule. `managerFilePatterns` adds the Gitea and Forgejo workflow folders.
  Older Renovate releases call it `fileMatch`, with plain regex strings:
  check the version the forge runs (§3).
- **Majors wait for a yes** on the dashboard: a major-version bump is its own
  change with its own gates (§4.1).
- **LTS lines stay on LTS** (`SECURITY_REFERENCE.md`, "LTS lines"): give the
  runtime an `allowedVersions` rule for its line, for example
  `{ "matchPackageNames": ["node"], "allowedVersions": "/^22\\./" }`.
- **`minimumReleaseAge`** keeps a just-published (or just-hijacked) release out
  for 3 days. A security fix can be merged sooner, by hand.

**Offline.** When Renovate can't reach the public registries, point each
datasource at the local proxy, for example
`{ "matchDatasources": ["npm"], "registryUrls": ["https://nexus.lan/repository/npm/"] }`.
Actions mirrored onto the forge can't be looked up on github.com: set
`"github-actions": { "enabled": false }`, and refresh those pins by hand
against the mirror (`WORKFLOW_DEPENDABOT.md`, the `ls-remote` lookup, with the
mirror's URL). Set `"osvVulnerabilityAlerts": true` only where Renovate
reaches osv.dev. It labels security updates, but it is not the alerts half.

## 3. Running it

Renovate runs as a schedule on the forge itself, with a **dedicated bot
user's token**, never a person's and never the job token. PRs opened with the
job token don't trigger CI, so they'd never show a check. The user creates the
token and stores it as a secret named `RENOVATE_TOKEN`. Pin the image to a
version, from the local registry when runners are offline. Renovate then
updates its own image.

**Gitea / Forgejo:** `.gitea/workflows/renovate.yml` (or `.forgejo/`).
Token scopes: `write:repository`, `write:issue` (the dashboard), `read:user`,
plus `read:package` if it reads the forge's own packages.

```yaml
name: renovate
on:
  schedule:
    - cron: "17 3 * * *"
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: renovate
  cancel-in-progress: false
jobs:
  renovate:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    container:
      image: <registry>/renovatebot/renovate:<version>
    steps:
      - name: Run Renovate
        env:
          RENOVATE_PLATFORM: gitea
          RENOVATE_ENDPOINT: ${{ vars.RENOVATE_ENDPOINT }}   # https://<host>/api/v1
          RENOVATE_TOKEN: ${{ secrets.RENOVATE_TOKEN }}
          RENOVATE_REPOSITORIES: ${{ github.repository }}
        run: renovate
```

**GitLab:** a job in `.gitlab-ci.yml`, run by a pipeline schedule
(Build → Pipeline schedules) with the variable `RENOVATE_SCHEDULE=1`.
`RENOVATE_TOKEN` is a masked, protected CI/CD variable holding a project
access token (`api` scope, Developer role).

```yaml
renovate:
  image: <registry>/renovatebot/renovate:<version>
  rules:
    - if: '$CI_PIPELINE_SOURCE == "schedule" && $RENOVATE_SCHEDULE == "1"'
  timeout: 30m
  variables:
    RENOVATE_PLATFORM: gitlab
    RENOVATE_ENDPOINT: $CI_API_V4_URL
    RENOVATE_REPOSITORIES: $CI_PROJECT_PATH
  script:
    - renovate
```

One Renovate for many repos (a single bot repo with `RENOVATE_AUTODISCOVER`
and a filter) also passes, as long as this repo shows up in its runs.

**Both are workflows, so they go through the gates**: the B8 checks for the
Actions one, `FORGE_GITLAB.md`'s hand checklist for the GitLab one, and the
secret is the user's to add (the forge file's secrets path). Renovate's PRs
are code changes like any other: each one merges through the gates (§4.1).
