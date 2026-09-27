# Dependabot and SHA pin upkeep

Loaded on demand by the dev-skills skill, alongside `WORKFLOW_REFERENCE.md`,
**only when a repo needs a `.github/dependabot.yml`** (new workflows, or the
audit's missing-Dependabot finding), an existing one is missing an ecosystem,
or a SHA pin has to be refreshed by hand. The workflow selection and audit
procedures, the review checklist and the template best practices stay in
`WORKFLOW_REFERENCE.md`.

---

## Keeping action SHAs current with Dependabot

Action SHAs should be updated when new versions are released. Dependabot
automates this — it opens small PRs that bump one action at a time, with the
changelog linked. You review and merge; nothing else changes.

**What it does:** Dependabot watches the versions your repo depends on — both
GitHub Action SHAs and application packages. When a new version is released it
opens a PR with the changelog linked. You review the PR, confirm CI passes, and
merge.

**Recommend adding this file to every project**, and **cover every ecosystem the
repo actually uses, not just `github-actions`.** An actions-only config is the
common mistake: the workflow pins stay current while the application's own
packages drift for months, which is exactly the backlog SKILL.md Section 4.1
exists to prevent. Each ecosystem needs its own `updates:` entry — Dependabot
does not infer them.

### `.github/dependabot.yml`

```yaml
version: 2
updates:
  # 1. GitHub Actions — keeps SHA pins and their version comments current
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    # Group all action updates into a single PR to reduce noise
    groups:
      actions:
        patterns:
          - "*"

  # 2. Application packages — one entry per ecosystem in the repo.
  #    Replace "npm" with the real one: pip, cargo, gomod, nuget, maven,
  #    gradle, bundler, composer, docker, terraform, ...
  #    `directory` points at the folder holding the manifest/lockfile.
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    groups:
      # Patch and minor bumps ride together: one review, not one risk class.
      # A minor bump can still demand a major toolchain change — only a build
      # settles it. Group for review convenience, never as a risk judgement.
      minor-and-patch:
        update-types:
          - "minor"
          - "patch"
    # Majors stay ungrouped: each is a breaking change with its own gates.
```

**Security updates are a separate feature — this file does NOT configure
them.** `dependabot.yml` controls *version updates*: the scheduled "Bump X
from A to B" PRs above. Advisory-driven *security updates* are repository
settings, not a file — **Settings → Code security → Dependabot alerts** and
**Dependabot security updates**. Both must be turned on, and once they are,
they work from the dependency graph for every ecosystem in the repo, whether
or not that ecosystem has an `updates:` entry here.

A repo with a perfect `dependabot.yml` and alerts left off is current but
unwatched: it gets version churn and zero CVE coverage, which reads as
security maintenance and is not — the "Bump X" PRs above never name a CVE or
GHSA identifier, because they can't; nothing was ever watching for one.
Claude cannot flip a repository setting, so when alerts are disabled
(`GET /repos/{owner}/{repo}/dependabot/alerts` returning `403`) this is a
Gate 3 finding to surface, not something to assume is handled because the
file looks right.

**Adaptation notes:**
- Change `interval` to `"monthly"` for less-active projects
- Remove the `groups` section if you prefer one PR per update (easier to review
  individually but more PRs)
- Add `reviewers:` to assign specific people to review these PRs
- For monorepos, add one entry per manifest location with different `directory:`
  values — a nested `package.json` or `requirements.txt` is invisible to a
  root-only entry
- `ignore:` a specific package only with a stated reason; it silences security
  PRs for it too

**What the PRs look like:**

Dependabot will open PRs like:
> Bump actions/checkout from v7.0.0 to v7.0.1
>
> Updates actions/checkout from 3d3c42e... (v7.0.0) to abc1234... (v7.0.1)
> - [Release notes](link)
> - [Changelog](link)
> - [Commits](link)

The PR updates both the SHA and the version comment automatically.

**Driving a Dependabot PR from an agent: comments don't work.** Posting
`@dependabot rebase` (or `merge`, `squash`) through the GitHub API or an MCP
tool does not trigger Dependabot — the `@` mention arrives with invisible
separators inserted (`·@·d·ependabot`) and Dependabot's own listener never
matches it. The comment posts successfully and nothing happens, which is the
dangerous part: it looks like it worked. Use `update_pull_request_branch`
(GitHub's own "Update branch" action) instead — it merges the base branch in
and fires the push event CI responds to, the same mechanical effect a
`@dependabot rebase` comment was trying to produce.

---

## Updating action SHA pins

Action SHAs should be updated when new versions are released. The best
approach is Dependabot (above) — it
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
