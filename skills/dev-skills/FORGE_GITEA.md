# Gitea and Forgejo Reference

Loaded with `FORGE_REFERENCE.md` when the forge is Gitea or Forgejo, once
per session. That file has the shared rules (scope, tags on the user's yes,
onboarding). This one has the commands. Forgejo is a Gitea fork with the
same API under `/api/v1` and the same `tea` CLI; differences are marked.

---

## Login, CA, token

- **CLI:** `tea`. `tea login list` shows the logins; the user adds one with
  `tea login add --name <host> --url https://<host>` and enters the token at
  its prompt. tea keeps it in `~/.config/tea/config.yml` (mode `600`).
  Commands run in the clone pick the login from `origin`; outside a clone,
  pass `--login <name> --repo <owner>/<repo>`.
- **Token scopes:** `write:repository` (PRs, merges, releases, tags,
  branches) and `read:user` (tea's login check). Add `write:package` only when
  CI or Claude pushes images to the forge's registry.
- **REST calls** (when tea has no command for it) read the token from
  `~/.netrc` (mode `600`: `machine <host> login <user> password <token>`) through
  `curl -n`, so it never appears on a command line. Below, `$A` stands for
  `https://<host>/api/v1/repos/<owner>/<repo>`.
- **Private CA:** tea is a Go program, so it trusts `SSL_CERT_FILE=<ca.pem>`.
  Never use `tea login add --insecure`.

## The `gh` commands, mapped

| Step | `gh` | Gitea / Forgejo |
|---|---|---|
| Repo, fork, mirror (step 1a) | `gh repo view --json …` | `curl -n -sS $A` → `fork`, `parent.full_name`, `mirror`, `default_branch`, `permissions` |
| Open the PR (Gate 5) | `gh pr create` | `tea pr create --base <default> --head <branch> --title "…" --description "…"` |
| PR state | `gh pr view <n> --json state` | `curl -n -sS $A/pulls/<n>` → `state`, `merged`, `merge_commit_sha` |
| CI on a commit | `gh pr checks` / `gh run list --commit` | `curl -n -sS $A/commits/<sha>/status` → `state` (`pending`, `success`, `failure`, `error`) and `statuses[]` |
| Watch CI | `gh pr checks --watch` / `gh run watch` | poll that status every 20s until it isn't `pending`, then require `success` (below) |
| Merge (Gate 6) | `gh pr merge <n> --merge` | `tea pr merge <n> --style merge` |
| Merge and delete the branch | `--delete-branch` (the user's) | `curl -n -sS -X POST $A/pulls/<n>/merge -H 'Content-Type: application/json' -d '{"Do":"merge","delete_branch_after_merge":true}'`: asked (`FORGE_REFERENCE.md`) |
| Release (manual path) | `gh release create` | `tea releases create --tag v<V> --target <sha> --title v<V> --note "…"` |
| Release exists | `gh release view <tag>` | `curl -n -sS $A/releases/tags/<tag>` |
| Edit release notes | `gh release edit` | `tea releases edit <tag> --note "…"` |
| Delete a release | `gh release delete` | `tea releases delete <tag>`: asked, plus approval in chat (Recovery) |
| Secrets present | `gh secret list` | Settings → Actions → Secrets: `https://<host>/<owner>/<repo>/settings/actions/secrets` |
| Cancel a run | `gh run cancel` | the run's page → **Cancel** (Actions tab), or the user does it |
| Attestation | `gh attestation verify` | none: verify the artifact's SHA-256 against the checksum file the release workflow publishes |

**A status with no `statuses[]` means no CI ran on that commit, which is not a
pass** (§2, "Absence of a verdict"). Check the runner first.

**The CI wait, as one chained call** (needs `jq`):

```bash
s=pending; for i in $(seq 1 90); do s=$(curl -n -sS "$A/commits/$sha/status" | jq -r '.state + (if (.statuses|length)==0 then "-empty" else "" end)'); [ "$s" = pending ] || [ "$s" = pending-empty ] || break; sleep 20; done; echo "ci=$s"; [ "$s" = success ]
```

The tag is created from the confirmed merge SHA with plain `git tag <V>
<sha> && git push origin <V>` (`SHIP_REFERENCE.md`, step 3), which is asked.
**`tea releases create` on a tag that doesn't exist creates it**, so on the
manual path push the tag first and create the release on it: that keeps the
tag a separate, asked step.

## Actions: what differs from GitHub Actions

`WORKFLOW_REFERENCE.md`'s templates and checklist apply, with these changes:

- **Folder:** `.gitea/workflows/`. Forgejo reads `.forgejo/workflows/`
  (and `.gitea/workflows/` when that one is missing). The B8 checks read
  all three.
- **Runners:** `runs-on:` must match a label a registered runner
  (`act_runner` / `forgejo-runner`) offers. Check that one is online under
  Settings → Actions → Runners (repo, org or site level). A label no runner
  offers leaves the job waiting forever, which looks like `pending`.
- **Where `uses:` resolves:** the instance's `[actions] DEFAULT_ACTIONS_URL`
  is `github` (fetch from github.com) or `self` (fetch from this forge).
  With no internet, mirror each action into the forge (an `actions`
  organisation: `actions/checkout`, …) and either set `self` or write the
  full URL: `uses: https://<host>/actions/checkout@<40-char sha>`. **The SHA
  pin still applies** (B8), and the SHA must exist in the mirror. Re-sync the
  mirror before re-pinning (`WORKFLOW_DEPENDABOT.md`, the `ls-remote` lookup
  runs against the mirror's URL).
- **Images and packages:** `container:` and `services:` images come from the
  forge's registry (`<host>/<owner>/<image>:<version>`) or a local proxy when
  runners are offline. Pin them by version, as on GitHub.
- **Token:** the job token is `${{ secrets.GITEA_TOKEN }}` (`GITHUB_TOKEN`
  also works). Keep `permissions:` in every workflow. Releases that don't
  enforce it ignore it, so also keep secrets out of jobs that PRs from forks
  trigger.
- **Not available:** artifact attestations, OIDC to cloud providers on older
  releases, and GitHub-only actions (`github/codeql-action`, `actions/attest*`).
  Use a checksum file as the release's integrity check, and Trivy or osv-scanner
  in place of CodeQL's dependency half. Check the instance's version before
  relying on `concurrency:` or `workflow_dispatch` inputs.

## Links (Gate 1, checks 5–6)

- Repo: `https://<host>/<owner>/<repo>`
- Release notes: `https://<host>/<owner>/<repo>/releases/tag/v<VERSION>`
- A folder (`SCOPED_REPO.md`): `https://<host>/<owner>/<repo>/src/branch/<default>/<path>`

## Settings the user changes

Branch protection: Settings → Branches. Protected tags: Settings → Tags.
Push mirrors: Settings → Repository → Mirror settings. Claude can't change
these, so hand over the path with the host filled in.
