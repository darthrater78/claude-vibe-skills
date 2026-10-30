# Scoped Repo Reference: a folder you own in someone else's repo

Loaded by the dev-skills skill **only when the session works in a shared
repo where the user owns one folder (or a few) and doesn't merge**: a
monorepo, a platform repo with team folders. The trigger is the user saying
so, or the probe's `role` key reading `contributor:<paths>` (`SESSION_START.md`).
It works the same on any forge. Section numbers point at `SKILL.md`.

---

## The role

**The user's folder is the project, and the PR is the finish line.** Claude
builds, tests, scans and documents the folder, then opens a PR to the repo's
default branch for its maintainers to review and merge. Claude never merges,
tags, releases or pushes to the default branch here, in either mode, and
doesn't hand the user a block that does. That is the repo owners' process.

**Set it up once per clone, at session start:**

1. Ask, if the user hasn't named them: "Which folder or folders do you own in
   this repo?" Check each exists (`git ls-files <path> | head -1`). If the repo
   has a `CODEOWNERS` (root, `.github/`, `.gitea/` or `docs/`), say whether
   it agrees. A mismatch is the user's to resolve.
2. Run `git config dev-skills.role "contributor:<path>[,<path>]"` (local config,
   this clone only), so the next session's probe reads it.
3. Write the gate file row with the Edit tool:

   ```
   Role: contributor — owns services/billing; merge, tags and releases belong to the repo's maintainers
   ```

   The checks then deny merges, default-branch writes, tags and releases
   (A4), and ask before an edit outside the folder (B9). Removing the row,
   or adding a folder to it, asks the user (B5). The banner adds `Role:
   contributor — owns <paths>; the open PR is the finish line`.

**Leaving the role** is the user's call ("I own this whole repo now"):
`git config --unset dev-skills.role`, then remove the row, which asks.

## The folder is the main page

Every rule the skill applies to "the repo root" or "the main page" applies
to **the owned folder** instead. Nothing the role produces goes into the
repo's root files.

| The skill's rule | In a scoped repo |
|---|---|
| README / main page (§10, standard 3; Gate 1, checks 5–6) | `<folder>/README.md`. Its top links to **the folder** on the forge (the tree URL: GitHub `/tree/<default>/<path>`, Gitea `/src/branch/<default>/<path>`, GitLab `/-/tree/<default>/<path>`) and to **the folder's changelog entry** for this version, since the folder has no releases of its own |
| `CHANGELOG.md` (Gate 4) | `<folder>/CHANGELOG.md`: one entry per change set the PR carries |
| Version (Gate 1) | the folder's own version file (`<folder>/VERSION`, `package.json`, `pyproject.toml`, …) when it has one, bumped only there. If it has none, `➖ version owned by the repo` |
| Security architecture section (§10, standard 7) | in `<folder>/README.md`, or `<folder>/SECURITY.md` |
| `DESIGN.md` (§10, standard 6) | `<folder>/DESIGN.md` |
| The CLAUDE.md line (`SESSION_START.md`, `claude_md`) | `<folder>/CLAUDE.md`, never the root one. Then `git config dev-skills.claudemd folder`, so the probe stops offering it |
| Gate file and handoff kept untracked (§2) | listed in `.git/info/exclude`, never the root `.gitignore`, which isn't the user's |
| Doc claims (Gate 4) | the folder's docs, plus any root doc that describes the folder (a root index, a service catalog). A root doc that is wrong about the folder is reported to the user, not edited |

A root-level file the change needs anyway (a workspace manifest, a shared
lockfile, a root CI list) asks first (B9), and the PR description names it,
so its owners see it.

## The gates, on this track

Record `Track: contribution — ends at the open PR`. It is the release
sequence cut off at the PR:

| Gate | Here |
|---|---|
| 🔢 VERSION | the folder's version (above), or ➖. Gate 1's tag and release-link checks don't apply: the folder has no tags |
| 🔨 BUILD | the folder's own target through the repo's tool: `make -C <folder>`, `pnpm --filter`, `nx run`, `bazel test //<folder>/...`, `go test ./<folder>/...`. The repo's CI for the PR is the second check, not a substitute (§2) |
| 🔒 SECURITY | scan the folder and its manifests. Findings in code outside it are still surfaced, but the fix belongs to its owners: the user waives them (§4.7) with "owned by <team>" as the reason, and they go in the PR description |
| 📄 DOCS | the folder's changelog and docs (above) |
| 📦 RELEASE | branch synced with the default branch, commit approved, **PR open, its description approved** in place of release notes. Request the reviewers `CODEOWNERS` names, and follow the repo's PR template |
| 🚀 SHIP | `➖ merge owned by the repo's maintainers` |

After the PR opens, the session's remaining job is review feedback:
commits on the same branch, each one approved (Section 1). Merge, tag and
release questions go to the repo's maintainers.

## What else changes

- **Stage by path:** `git add -- <folder>` (plus any root file the user
  approved), never `git add -A`.
- **Commit scope** (Section 1.1) is the folder's name: `fix(billing): …`.
- **Branch names and PR templates** follow the repo's convention. Read
  `CONTRIBUTING.md` and the PR template at session start, and ask once if
  there's no convention.
- **CI is the repo's.** Session start's "no CI" offers (`SESSION_START.md`,
  step 6) don't apply. Report a missing check, and don't create or change
  a workflow outside the folder. A failing check outside the folder is
  reported, with its log, to the user.
- **Session start's unfinished-release check** (step 7) is skipped: the folder
  doesn't tag. The **session-end checkpoint** treats an open PR as finished
  work, not an unmerged branch.
