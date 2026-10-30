# Self-Hosted Forge Reference

Loaded by the dev-skills skill **only when `origin` is not on github.com**:
the probe's `forge` key reads `other:<host>`, or a recorded forge
(`SESSION_START.md`). Read it before step 1a, then the forge's own file:
`FORGE_GITEA.md` (Gitea and Forgejo) or `FORGE_GITLAB.md`. Those hold the
command for each step, and this file holds what they share. GitHub-hosted
repos never load any of the three. Section numbers point at `SKILL.md`.

---

## Scope: a local session on the same network as the forge

The forge runs on the user's own network and is not reachable from the
internet. **Claude Code runs locally on that network**: the environment is
**Local** (step 0), and git is presented or run as that step and the mode
say. A remote container cannot reach a LAN forge at all. If step 0 resolves to
a remote container, say so before any work: "This repo's forge
(`<host>`) is on your network, which a cloud session can't reach. Run this
session locally, or through Remote Control." Then stop.

**What changes, and what doesn't:**

| | GitHub | Self-hosted forge |
|---|---|---|
| `gh` / GitHub MCP | yes | the forge's CLI (`tea`, `glab`), its MCP server, or its REST API, in that order of preference |
| Gates, tracks, commit approval, mode | unchanged | **unchanged** |
| Tag push, ref deletions (§5.8) | the user runs them | **Claude may run them, and the user is asked each time** (below) |
| CI | GitHub Actions | Gitea/Forgejo Actions (same syntax) or GitLab CI |
| Dependency watch (§4.1) | Dependabot file + alerts | Renovate, plus an offline vulnerability database at Gate 3 (below) |
| Attestations, `githubstatus.com` | yes | no. The post-ship check uses a checksum, and the status check is the forge's own health page |

## Tags and ref deletions: Claude runs them, the user is asked every time

On GitHub these go to the user because Claude's credentials are denied on
them (§5.8). On the user's own forge they are not, so the reason is gone.
The approval stays: **every tag push, tag creation, ref deletion and release
deletion is asked of the user, one by one, in Claude Code's own permission
prompt.** The enforcement checks turn A6's deny into that ask while the gate
file carries the `Forge:` row (`ENFORCEMENT.md`, A6). A blanket "yes to all
tags" doesn't exist: each one is asked.

- **Everything before it is unchanged.** The tag still waits for Gate 6's
  merge confirmation and version guard (`SHIP_REFERENCE.md`, step 3). In
  semi-autonomous mode the pre-tag report is still written in full, and the
  push follows it in the same turn, so the prompt is the user's yes on that
  report (`AUTO_MODE.md`, checkpoint 2). In manual mode the block is still
  presented.
- **A merge may delete its branch** (`--remove-source-branch`,
  `delete_branch_after_merge`). That is a ref deletion, so it is asked too.
- **A protected-tag or permission error is a stop**, like a `403` on GitHub:
  report it, don't retry with another tool or ref.
- **Recovery deletes a tag** (`SHIP_REFERENCE.md`, "Recovery"), and each
  deletion still needs the user's explicit approval in chat, on top of the
  prompt, because it un-publishes.

## Onboarding: once per clone

Run this when the probe's `forge` key reads `other:<host>`. A clone that
has been onboarded reads `gitea@<host>`, `forgejo@<host>` or `gitlab@<host>`
from `git config dev-skills.forge`: skip to "Every session". Chain the reads
into one call (§5.1), then ask the questions that apply (steps 1, 2, 4, 6) in
one `AskUserQuestion` call, together with the session-start questions.

1. **Identify the forge with unauthenticated reads.** Never guess it from
   the hostname.
   - `curl -sS https://<host>/api/v1/version` → `{"version":"1.22.3"}` is
     Gitea; a version with `+gitea` or `forgejo` in it, or an answer from
     `/api/forgejo/v1/version`, is Forgejo.
   - `curl -sS -o /dev/null -w '%{http_code}' https://<host>/api/v4/version`
     → `401` (or `200`) is GitLab.
   - `https://<host>/api/v3/meta` answering is GitHub Enterprise Server: use
     the GitHub path with `GH_HOST=<host>`, and this file no longer applies
     past its scope rules.
   - Nothing answers: ask "Which forge serves `<host>`: Gitea, Forgejo or
     GitLab?"
2. **TLS: trust the forge's certificate authority (CA), never skip
   verification.** If `curl` fails with a certificate error, the forge uses a
   private CA. Ask for the CA file. Then scope it to that host only: `git
   config --global http.https://<host>/.sslCAInfo <ca.pem>`, plus the CLI's own
   setting (forge file). `-k`, `GIT_SSL_NO_VERIFY` and `insecure: true` are
   §4's disabled-TLS pattern, so flag them on sight, offline or not.
3. **Tooling and login.** Check the CLI first (`tea login list`, `glab auth
   status --hostname <host>`), then an MCP server whose name says `gitea`,
   `forgejo` or `gitlab`, then the REST API with a token. If none is logged
   in, the user creates a token with the scopes the forge file names (no more
   than those). The user enters it into the CLI's login themselves (`tea login
   add` / `glab auth login`), so **the token never appears in the
   conversation, a command line, a URL or a file in the repo**. Note where the
   CLI stores it (the forge file says) and that the file stays mode `600`.
4. **The source of truth.** Read the repo from the API (forge file:
   `mirror`, `fork`, `parent`, default branch, permissions). **Mirrors** are
   common here, for example a Gitea repo push-mirrored to GitHub, or a
   read-only pull mirror. Ask once: "Which copy is canonical, the one PRs go
   to?" `origin` must be that one. A pull mirror can't take pushes, so it is
   never `origin`. PRs, tags and releases go to the canonical repo only. A fork
   follows `SHELL_REFERENCE.md`, "Forks", with the forge's commands.
5. **CI: find it, then prove it runs.** Look in `.gitea/workflows/`,
   `.forgejo/workflows/` or `.gitlab-ci.yml`. A workflow with no runner never
   runs, and no runs looks the same as no failures (§2, "Absence of a
   verdict"). So check that at least one runner is online for the repo (forge
   file), and record it.
6. **Where CI fetches from.** The runners may have no internet. A workflow
   that pulls `actions/checkout` from github.com, an image from Docker Hub, or
   packages from a public registry fails there. Ask once whether the runners
   reach the internet. If they don't, actions come from the forge's own mirror
   (forge file), images from the local registry, and packages from a local
   proxy (Nexus, Artifactory, devpi, Verdaccio). Write the answer on the
   `Forge:` row.
7. **The dependency watch** (§4.1). There is no Dependabot, so the two halves
   become:
   - **The watch.** Renovate running on the forge, configured for every
     ecosystem in the repo. Checking, configuring and scheduling it is in
     `WORKFLOW_RENOVATE.md`: load it for this step, and at Gate 3 when the
     watch is missing or stale (an open Medium either way).
   - **The alerts.** At every Gate 3, `osv-scanner` over the lockfiles. Use its
     offline database mode where the scanning machine can't reach osv.dev,
     and refresh the database at least weekly. A database older than 7 days
     is a finding, not a pass. A GitHub alerts `403` never applies here.
8. **Record it.** Run `git config dev-skills.forge <kind>@<host>` (local config,
   this clone only), and write the gate file row with the Edit tool. Adding
   it asks the user (B5), because it changes who runs tags:

   ```
   Forge: gitea @ git.home.lan — self-hosted · tea (login ok) · runner online · CI offline: actions from git.home.lan/actions · deps: renovate + osv offline db
   ```

## Every session

- **Re-measure, don't inherit** (`SESSION_START.md`, "Measure, don't
  infer"). In the probe's call: the CLI's login status, the repo read (fork,
  mirror, default branch), and a runner check. Write the `Forge:` row fresh.
  A changed row asks the user (B5).
- **CI lives in the forge's folder.** The probe's `workflows` and
  `release_workflow` keys read `.github/workflows/` only, so list
  `.gitea/workflows/`, `.forgejo/workflows/` or `.gitlab-ci.yml` in the
  same call. Step 6's "no CI" offers create files there, never under
  `.github/`.
- **Load the forge file** (`FORGE_GITEA.md` or `FORGE_GITLAB.md`) once. Every
  `gh` command in `RELEASE_GATES.md`, `SHIP_REFERENCE.md` and
  `SECURITY_GATE.md` maps to its table, the way `REMOTE_SESSION.md` item 3
  maps them to MCP.
- **Links** (§10, standard 3; `RELEASE_GATES.md`, Gate 1, checks 5–6): the
  repo and release-notes links point at the forge, using the URL forms in the
  forge file. A repo with no internet exposure still gets them, because the
  people who read the README are on the same network.
- **The banner** adds `Forge: <kind> @ <host> (self-hosted) — Claude runs tags
  and ref deletions on your yes, each time`.
