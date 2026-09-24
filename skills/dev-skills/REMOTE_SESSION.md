# Remote Session Reference

Loaded by the dev-skills skill **only when step 0 resolves to a remote
container** (`SESSION_START.md`, step 0), before step 1. Local and Termux
sessions never need it. Section numbers point at `SKILL.md`.

---

## Remote container specifics

1. **Nothing needs cloning — the repo is already there.** The container is
   provisioned with a fresh clone at session start. Never present `git clone`,
   and never treat a missing local repo as the user's problem to fix.
2. **The work exists only in the container until it is pushed.** Say this once,
   early:

   > ⚠️ **Remote session:** these edits live in this container. It is reclaimed
   > when the session ends, so anything uncommitted is lost. I'll commit and
   > push from here once you approve.

3. **`gh` is typically not installed.** The probe's `gh_installed` and
   `gh_repo` keys say whether it is there and whether it works. If absent, every
   `gh` command in Gates 5 and 6 maps to a GitHub MCP tool (`mcp__github__*`):

   | `gh` command | MCP equivalent |
   |---|---|
   | `gh pr create` | `create_pull_request` |
   | `gh pr list` / `gh pr view` | `list_pull_requests` / `pull_request_read` |
   | `gh pr merge` | `merge_pull_request` |
   | `gh release create` / `gh release view` | `list_releases` / `get_release_by_tag` + release API |
   | `gh run list` / `gh run view` | `actions_list` / `actions_get` / `get_job_logs` |

   If neither `gh` nor GitHub MCP tools are present, say so *before* Gate 5
   rather than discovering it mid-ship.
4. **Skip step 2 (shell detection) entirely — including for the tag and
   ref-deletion blocks.** Every git command Claude runs here uses the
   container's own bash. The tag-push and ref-deletion carve-out (Section 5.8)
   still hands the user a block to run on their own machine, but that block
   carries no `cd` and nothing else that varies by shell: it is plain
   single-line `git` commands (`git checkout`, `git pull`, `git tag`,
   `git push`) that run unmodified in every shell `SHELL_REFERENCE.md` lists.
   So there is no clone path to ask for and no shell to ask about — put "run
   this from your local clone" in the prose above the block and leave the block
   itself copyable as given (`SHELL_REFERENCE.md`, "Tag and ref-deletion blocks
   carry no `cd`").
5. **Step 3 (sync offer) is usually unnecessary** — the clone is fresh as of
   session start. Still run `git fetch origin` before Gate 5 in case the branch
   moved during a long session.
6. **Gate state file goes on the working branch,** not in `.gitignore`
   (Section 2).
7. **Executing git here does not extend to tag pushes.** Container credentials
   are commonly denied (`403`) on `refs/tags/*`, and that is exactly the push
   that fires the release workflow. Present the tag block to the user even
   though everything else runs here — Section 5.8, "Tag pushes and ref
   deletions are the exceptions." Semi-autonomous mode does not change this;
   it only adds the full pre-tag report above the block ("Semi-autonomous mode
   — execution", below).
8. **Docker in a web container: only for projects with a Docker build
   signal** (`Dockerfile`, `docker-compose.yml`/`compose.yaml`). Measure the
   daemon, not the binary: `docker info`. A web container often ships the
   CLI with no daemon behind it. If `docker info` fails, say so and offer a
   choice. This is a real limitation, not something to route around:

   > ⚠️ **Docker isn't usable in this container** — the `docker` CLI is
   > present but `docker info` can't reach a daemon, so I can't build or
   > verify the image here. Two ways forward:
   > 1. **Work commit now** — save progress on the branch so you can finish
   >    Gate 2 on a machine with a working Docker daemon.
   > 2. **CI-only BUILD** — if a release workflow builds and tests the image
   >    in CI, Gate 2 can pass on that basis (Gate 2, "CI-only").
   >
   > Which do you want?

   This is separate from the test artifact. Either way, nothing merges to the
   default branch until CI has produced a test image from the PR head
   (`GATE_REFERENCE.md`, Gate 2, "Test artifact before merge").
