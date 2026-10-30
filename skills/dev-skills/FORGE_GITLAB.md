# GitLab Reference (self-managed)

Loaded with `FORGE_REFERENCE.md` when the forge is GitLab, once per
session. That file has the shared rules (scope, tags on the user's yes,
onboarding). This one has the commands. GitLab calls a pull request a
**merge request (MR)**, and its number in a project is the `iid`.

---

## Login, CA, token

- **CLI:** `glab`. `glab auth status --hostname <host>` shows the login; the
  user adds one with `glab auth login --hostname <host>` and enters the token
  at its prompt. glab keeps it in `~/.config/glab-cli/config.yml` (mode
  `600`), and picks the host from `origin` inside the clone.
- **Token scope:** `api`. GitLab has no narrower scope that can open or merge
  an MR (`write_repository` is git-only), so make it a **project access
  token**: one project, an expiry date, and the lowest role that works.
  **Developer** opens MRs. Merging into a protected default branch, and
  pushing a protected tag, need **Maintainer** or the role the protection
  names.
- **Private CA:** `glab config set ca_cert <ca.pem> --host <host>`. Never turn
  verification off.
- **REST calls** go through `glab api`, which carries the login, so no token
  appears. Below, `$P` stands for `projects/<group>%2F<project>` (the path,
  URL-encoded).

## The `gh` commands, mapped

| Step | `gh` | GitLab |
|---|---|---|
| Repo, fork, mirror (step 1a) | `gh repo view --json …` | `glab api $P` → `forked_from_project`, `mirror`, `default_branch`, `permissions` |
| Open the PR (Gate 5) | `gh pr create` | `glab mr create --source-branch <branch> --target-branch <default> --title "…" --description "…" --yes` |
| PR state | `gh pr view <n> --json state,mergeCommit` | `glab api $P/merge_requests/<iid>` → `state` (`merged`), `merge_commit_sha` (or `squash_commit_sha` on a squash, the head SHA on a fast-forward) |
| CI on a commit | `gh run list --commit` | `glab api "$P/pipelines?sha=<sha>"` → each pipeline's `status` |
| Watch CI | `gh pr checks --watch` | poll that every 20s until no pipeline is `created`, `pending`, `running`, `preparing` or `waiting_for_resource`, then require `success` |
| Merge (Gate 6) | `gh pr merge <n> --merge` | `glab mr merge <iid> --yes` |
| Merge and delete the branch | `--delete-branch` (the user's) | `glab mr merge <iid> --yes --remove-source-branch`: asked (`FORGE_REFERENCE.md`) |
| Release (manual path) | `gh release create` | `glab release create v<V> --ref <sha> --name v<V> --notes "…"` |
| Release exists | `gh release view <tag>` | `glab release view v<V>` |
| Delete a release | `gh release delete` | `glab release delete v<V>`: asked, plus approval in chat (Recovery) |
| Secrets present | `gh secret list` | Settings → CI/CD → Variables: `https://<host>/<group>/<project>/-/settings/ci_cd` |
| Runner online | (GitHub-hosted) | `glab api "$P/runners?status=online"` (needs Maintainer), or Settings → CI/CD → Runners |
| Attestation | `gh attestation verify` | verify the artifact's SHA-256 against the checksum file the release job publishes |

**Merging when the pipeline succeeds is auto-merge.** Recent `glab mr merge`
sets it by default, so the merge happens later, unchecked. The checks treat
every `glab mr merge` as a merge now, so all of its gates must pass first. Then
confirm on the remote that it merged, with `state` and the commit SHA, before
the tag. **An empty pipeline list means no CI ran**, which is not a pass. Check
the runner and the `rules:` first.

**Don't pass `--remove-source-branch` to `glab mr create`.** It schedules a
branch deletion for the merge, which nothing asks about at that point. The
checks ask about it at creation, so leave it off.

`glab release create` on a tag that doesn't exist creates it from `--ref`, so
on the manual path push the tag first (`git tag <V> <sha> && git push origin
<V>`, asked) and create the release on it.

## GitLab CI: not covered by the workflow checks yet

The B8 checks and `WORKFLOW_REFERENCE.md`'s templates are for Actions syntax.
`.gitlab-ci.yml` is **not read by any check**, and the skill doesn't generate
it. Say so when CI is created or audited. At Gate 3's workflow audit, read it
by hand against this list and report each miss as a finding:

- **Images pinned** to a version, a digest where the registry supports it,
  never `:latest`. `include:` from another project pins `ref:` to a SHA or
  tag; `include: remote:` points at nothing on the internet when runners are
  offline.
- **Every job has `timeout:`**, and long jobs `interruptible: true`.
- **Variables:** secrets are **masked and protected**, so MR pipelines from
  unprotected branches and forks don't see them. Nothing echoes them in
  `script:`. A deploy job runs only on protected refs (`rules:`).
- **Job token:** the project's CI/CD job token allowlist limits which
  projects `CI_JOB_TOKEN` can reach.
- **Artifacts** carry `expire_in`.
- **Dependency watch:** GitLab's dependency scanning needs the Ultimate tier.
  Without it, the watch is Renovate (`FORGE_REFERENCE.md`, onboarding step 7).

## Links (Gate 1, checks 5–6)

- Repo: `https://<host>/<group>/<project>`
- Release notes: `https://<host>/<group>/<project>/-/releases/v<VERSION>`
- A folder (`SCOPED_REPO.md`): `https://<host>/<group>/<project>/-/tree/<default>/<path>`

## Settings the user changes

Protected branches and protected tags: Settings → Repository. Mirroring:
Settings → Repository → Mirroring repositories. Approval rules: Settings →
Merge requests. Claude can't change these, so hand over the path with the
host filled in.
