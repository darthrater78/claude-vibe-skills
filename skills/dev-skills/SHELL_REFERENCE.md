# Shell Command Reference

This file is loaded on demand by the dev-skills skill when git commands need to
be formatted for the user's shell environment (Section 5.7). It contains the
environment rules in full: the `cd` format table, the rules every presented
block follows, why tag pushes and ref deletions always go to the user,
shell-specific syntax, the Termux clone flow, and example blocks for each
supported shell.

**This file applies only when Claude is presenting commands for the user to run
in their own terminal** — that is, local and Termux sessions. Remote container
sessions do not use it; see below.

---

## Remote containers — do not format, execute

When the session runs in a remote container (`GATE_REFERENCE.md`, session start, step 0), none of this
file applies:

- **There is no clone step.** The container is provisioned with the repo already
  cloned. Never present `git clone`.
- **There is no `cd` step.** Claude's working directory is already the repo.
- **There is no shell question.** The shell is the container's own bash.
- **Do not hand the user a command block to run.** Their terminal is a different
  machine with a different clone that never received these edits — pasting the
  block would commit nothing, and the container's work is destroyed when the
  session ends. Claude commits and pushes from inside the container, after
  approval (Section 1).
- **`gh` is usually absent.** Use the GitHub MCP mapping table in
  `GATE_REFERENCE.md`, session start, step 0.

Showing the user a summary of what you are about to run is fine. Handing them
commands *instead of* pushing is not.

---

## Remote containers ask for the clone path, not the shell

Step 0 of the session-start procedure skips the shell question for remote
containers, and the tag carve-out below is the one moment that would seem to
need it back. It does not. Everything in a tag or ref-deletion block below `cd`
is a plain single-line `git` invocation — `git checkout`, `git pull`, `git tag`,
`git push` — with no heredocs, no multi-line strings and no shell-specific
syntax, so it runs unmodified in all seven shells above. The only line that
varies is `cd`, and a quoted path parses the same way in every one of them.

So ask for the clone path, and ask when the block is about to be presented — a
session that never releases and never deletes a ref never needs it:

> Before I hand you this block — **what's the path to your local clone**, so it
> starts in the right directory?

Store it for the rest of the session. Presenting `cd <your-repo-path>` as a
placeholder is a defect, not a neutral default: it is the one line the user
cannot copy as given, in the one block they must run by hand.

---

## Tag pushes and ref deletions — always the user's

SKILL.md Section 5.7 states the rule: creating a tag ref and deleting any ref go
to the user in every environment, remote containers included. This is why.

The credentials Claude runs under are routinely denied on two specific ref
operations, both narrower than the `contents: write` scope that lets branch
commits push fine all session:

- **Creating a `refs/tags/*` ref** — especially one that *triggers a workflow* —
  is commonly withheld even where ordinary pushes succeed.
- **Deleting any ref**, tag or branch, is its own separate permission again. A
  token that pushes commits and creates tags without issue all session can still
  **403** on `git push origin --delete some-branch`. Same failure, different
  command, and easy to miss the pattern and go looking for a fix in the wrong
  place.

The tag side also carries a worse blast radius than an ordinary denial: the tag
push is what fires the release workflow, so a `403` there strands a merged,
version-bumped default branch with no release behind it. Route both kinds to the
user's credentials from the start rather than discovering this mid-ship or
mid-cleanup.

**If you are told to attempt either push anyway and it 403s:** do not retry, do
not re-route through another tool, and do not act on a different ref. Report it
and hand over the block.

The block's exact shape, the sync that must precede the tag, the `src refspec
does not match any` case that is *not* a permissions problem, and the GitHub UI
fallback for users with no local clone are in `GATE_REFERENCE.md`, Gate 6.

---

## Every presented block

**Always start with `cd`.** Never assume the user's terminal is in the project
directory. Use the `cd` format for their shell from the table above. (This does
not apply to commands Claude executes itself — the container's working directory
is already correct.)

**Never use bare `git push`.** Every push specifies the remote and the branch:
`git push -u origin <branch-name>`. The `-u` sets upstream tracking, which
prevents the error on subsequent pushes.

**Verify the remote first.** Before presenting any push, run `git remote -v`. If
`origin` is not set, make `git remote add origin <url>` the first command in the
block, using the URL stored at session start (`GATE_REFERENCE.md`, step 1). This
prevents the "default repo has not been set" error.

**Explanation goes above or below the block, never inside it** as interleaved
prose. Brief `#` comments within the block are fine.
---

## One block per operation

Present the entire sequence in a single fenced block the user can copy once —
`cd` through push. Do not split an operation across several blocks or interleave
prose between commands. The examples at the bottom of this
file show the intended shape: one block, one paste.

Split only when the user must stop and inspect something first (a conflict, a
build, a PR number). Say what to check before the next block.

---

## `cd` format by shell

| Shell | `cd` format |
|---|---|
| Windows PowerShell | `cd "C:\Users\steve\Desktop\git\project-name"` |
| Linux PowerShell (pwsh) | `cd "/home/user/projects/project-name"` |
| Git Bash (Windows) | `cd "/c/Users/steve/Desktop/git/project-name"` |
| Termux (Android) | `cd ~/storage/shared/projects/project-name` |
| macOS Terminal | `cd ~/projects/project-name` |
| Linux Terminal | `cd ~/projects/project-name` |
| WSL | `cd /mnt/c/Users/steve/Desktop/git/project-name` |

Use the actual project path from the current working directory. For Git Bash,
convert Windows paths (`C:\foo\bar`) to Unix-style (`/c/foo/bar`). For WSL,
convert to `/mnt/c/...` form.

---

## Shell-specific syntax

- **Multi-line strings:** PowerShell uses here-strings (`@'...'@`), Bash/Termux/
  macOS/Linux use heredocs or `$'...'`, Git Bash follows Bash rules
- **Variable expansion:** PowerShell uses `$var`, Bash uses `$var` or `${var}` —
  but quoting rules differ
- **Command chaining:** PowerShell uses `;` (no `&&`), Bash/Git Bash/Termux use
  `&&`
- **Line continuation:** PowerShell uses backtick (`` ` ``), Bash uses backslash
  (`\`)
- **Path separators:** PowerShell and Windows use `\`, everything else uses `/`
- **Termux quirks:** limited PATH, may need `pkg install` for tools like `gh`,
  smaller screen so keep commands concise

---

## Git Bash stalls on spawn-heavy scripts — split the invocation

Git Bash (and MSYS2/Cygwin) emulate `fork()` on Windows rather than calling it.
Every subprocess pays that emulation cost, and real-time antivirus scans each
spawned image on top of it. A shell script that is unremarkable on Linux — a
loop calling `grep`, `sed`, `wc`, `basename`, `unzip` once per file — can spawn
several hundred processes and **stall indefinitely partway through**.

Recognise it by shape, not by guessing:

- partial output, then nothing; the script never returns and never errors
- killing it gives exit `137` (SIGKILL) or `124` (`timeout`), never a real
  non-zero exit from the script itself
- the commands it stalled on run fine when executed individually
- re-running stalls at a *different* point — the position is not reproducible

That last two are what separate this from a real defect. **A script that
behaves this way is not broken, and the stall is not a finding.** Do not
"fix" the script, and do not go hunting for a bug in the command it happened
to stop at.

**The fix is to split the run, not to skip it.** Run the script's sections as
separate invocations — its natural blocks (version checks, file checks, archive
checks) are usually already delimited by its own `echo` headers. Each
invocation spawns a fraction of the processes and completes. Wrap every one in
`timeout <n>` so a stall costs seconds instead of wedging the session.

Rules for a split run:

- **Every section must actually execute.** A split run passes only when the
  sections together cover everything the whole script would have done. Sections
  you skipped are ⬜, exactly as if the script had never run.
- **A partial run is never a pass.** Output that got as far as "OK" on three
  checks proves those three checks, and nothing about the ones after it. This
  is the failure mode the split is guarding against, so do not re-introduce it.
- **Record that it was split** in `.claude/dev-skills-gates.md`, with the
  sections covered and the total error count. A later session reading "BUILD
  PASSED" needs to know the verification was complete, not merely started.
- **Do not defer to CI instead.** CI runs after the commit Gate 2 exists to
  protect (`GATE_REFERENCE.md`, Gate 2). Splitting keeps the check local, which
  is the whole point of the gate; moving it to CI silently converts a
  pre-commit gate into a post-commit report.

WSL is the durable answer where the user has it — a real kernel, real `fork()`,
and the same environment CI runs on. Offer it once, as a suggestion. It is not
a precondition: the split run is a complete local verification on its own, and
a user who does not want WSL is not thereby blocked from passing Gate 2.

---

## Termux clone flow

On Termux (Android), the repo may not exist on the device. This is the only
environment where Claude presents a clone step — remote containers arrive
pre-cloned, and local sessions are already in the repo. When the user's shell is
Termux, every command block must account for this:
- **First time (repo not yet cloned):** start with `git clone <url>` then `cd`
  into the cloned directory. Use the repo URL stored at session start
  (`GATE_REFERENCE.md`, step 1).
- **Subsequent commands (repo already cloned):** start with `cd` then
  `git fetch origin && git pull origin <branch>` to sync before any work.

---

## Example output (Windows PowerShell)

```powershell
cd "C:\Users\steve\Desktop\git\claude-vibe-skills"
git checkout -b release/v2.10.0
git add -A
git commit -m @'
v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
'@
git push -u origin release/v2.10.0
```

## Example output (Git Bash)

```bash
cd "/c/Users/steve/Desktop/git/claude-vibe-skills"
git checkout -b release/v2.10.0
git add -A
git commit -m "v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push -u origin release/v2.10.0
```

## Example output (Termux — first time, repo not yet cloned)

```bash
cd ~/storage/shared/projects
git clone https://github.com/owner/repo.git
cd repo
git fetch origin && git pull origin main
git checkout -b release/v2.10.0
git add -A
git commit -m "v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push -u origin release/v2.10.0
```

## Example output (Termux — repo already cloned)

```bash
cd ~/storage/shared/projects/repo
git fetch origin && git pull origin main
git checkout -b release/v2.10.0
git add -A
git commit -m "v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push -u origin release/v2.10.0
```
