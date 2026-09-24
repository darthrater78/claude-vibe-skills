# Shell Command Reference

This file is loaded on demand by the dev-skills skill when git commands need to
be formatted for the user's shell environment (Section 5.8). It contains the
environment rules in full: the rules and the labeled format every presented
block follows, manual mode's few-stops rules, why tag pushes and ref
deletions always go to the user, shell-specific syntax, and the Termux clone
flow.

**This file applies only when Claude is presenting commands for the user to run
in their own terminal** — that is, local and Termux sessions in manual mode.
Remote container sessions do not use it; see below. A session in **semi-autonomous mode**
(`SKILL.md`, Operating modes) runs most commands itself, but this file still
governs the two blocks it always hands over — the tag push and any ref deletion
— and any block it falls back to when an operation fails.

---

## Remote containers — do not format, execute

When the session runs in a remote container (`SESSION_START.md`, step 0), none of this
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
  `SESSION_START.md`, step 0.

Showing the user a summary of what you are about to run is fine. Handing them
commands *instead of* pushing is not.

---

## Tag and ref-deletion blocks carry no `cd`, and need no shell question

These two blocks are handed to the user in every environment and both modes
(below), which makes them the one place Claude does not know the path to write.
Do not invent one, do not ask for one, and do not emit a `cd <your-repo-path>`
placeholder — it is the one line the user cannot copy as given.

Say it in the prose instead, above the block:

> Run this from your local clone of the repo.

Someone pushing a release tag knows where their checkout is. The prose reminder
covers the case where their terminal is sitting somewhere else; the block covers
the part that is actually worth copying.

This also means these blocks need no shell question. Everything in them is a
plain single-line `git` invocation — `git checkout`, `git pull`, `git tag`,
`git push` — with no heredocs, no multi-line strings and no shell-specific
syntax, so with the `cd` gone there is nothing left that varies between the
seven shells above. Remote container sessions, which skip the shell question at
session start, therefore never need to come back and ask it.

---

## Tag pushes and ref deletions — always the user's, in both modes

SKILL.md Section 5.8 states the rule: creating a tag ref and deleting any ref go
to the user in every environment and in both modes, remote containers included.
This is why.

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

**Semi-autonomous mode does not soften any of this** (`SKILL.md`, Operating
modes). A mode is a statement about how much ceremony the user wants, not about
what credentials the remote will honour — and the denial above comes from the
remote. What that mode adds is the full pre-tag report that goes above the
block, so the user is deciding on an account of work they did not watch rather
than pasting commands cold.

The block's exact shape, the sync that must precede the tag, the `src refspec
does not match any` case that is *not* a permissions problem, and the GitHub UI
fallback for users with no local clone are in `SHIP_REFERENCE.md`.

---

## Forks — `origin` is the fork, and the session never targets upstream

When the working repo is a fork, every git write Claude runs or presents goes to the
fork: pushes, PRs (base repo *and* head repo), merges, releases, and the tag
block. The upstream repo is out of scope for the session in both modes. If the
user wants to open a PR upstream, sync the fork, or file an issue there, they do
it on GitHub directly. Claude does not present it, run it, or offer a
workaround. Session start checks and fixes the remote (`SESSION_START.md`,
step 1a). What holds for the rest of the session:

- **`origin` points at the fork.** A clone whose `origin` is the upstream repo
  is corrected before any work starts, not worked around with a second remote.
- **No `upstream` remote is added, and none is used for writes.** One that
  already exists stays read-only: Claude never pushes to it.
- **Every `gh` command that writes passes `--repo <fork-owner>/<repo>`.** In a
  fork, `gh pr create` defaults its *base* to the parent repo, so a bare
  `gh pr create` opens the PR upstream. That exact failure is why this rule
  exists. `gh repo set-default <fork-owner>/<repo>` is set at session start as
  a second guard, but the explicit `--repo` is the rule. The GitHub MCP
  equivalents take the fork's owner and repo, never the parent's.
- **The `Origin:` row in the gate state file records it** (`Origin:
  <owner>/<repo> (fork of <parent>)`). The enforcement checks read that row
  and block a `gh` write in a fork that has no `--repo`, or whose `--repo` is
  not the fork (`ENFORCEMENT.md`, A4).

**Session start's fork check, the four cases** (`SESSION_START.md`, step 1a,
from the probe's `gh_repo` and `gh_login`; without `gh`, the GitHub MCP
`get_repository` equivalent):

| What you find | What it means | Do |
|---|---|---|
| `isFork: true` | `origin` is the fork | Correct. Record `Origin: <owner>/<repo> (fork of <parent>)` and run `gh repo set-default <owner>/<repo>` |
| `isFork: false`, and `<login>/<repo>` exists with this repo as its `parent` | `origin` is **upstream**, and the user's fork exists | Stop. Fix the remote before any work: `git remote set-url origin <fork-url>`, then `git fetch origin`. Record the fork as above |
| `isFork: false`, the user is not the owner, `viewerPermission` is below `WRITE`, and no fork exists | They cloned someone else's repo and have nowhere to push | Stop and ask. The user creates the fork on GitHub (or approves `gh repo fork --remote=false`), and then the remote is fixed as above. Never plan a push or PR to the upstream repo |
| `isFork: false`, and the user owns it or has `WRITE` | An ordinary repo | Nothing to do. Record `Origin: <owner>/<repo> (not a fork)` |

The user's rule: **the user can go to GitHub directly if they want to go
upstream.** So the fix is always to repoint `origin` to the fork. Adding an
`upstream` remote beside it is not a fix. If an `upstream` remote already
exists, leave it alone and never push to it. Changing `set-url` is a local
config change, not a ref write: it follows the session's mode (presented in
manual, run by Claude in semi-autonomous), after the user has seen the
before and after URLs.

**Re-check after a fix, don't assume it worked.** `git remote -v` and the
`gh repo view` call must now both name the fork.

## Every presented block

**No `cd`, ever.** Every block assumes the user's terminal is already in the
repo, and the label names where to run it (`· in ~/claude-vibe-skills`).
A path the user has to edit is a broken first line, and a guessed one is
worse. The enforcement checks block a `cd` in a run block (`ENFORCEMENT.md`,
C4).

**Never use bare `git push`.** Every push specifies the remote and the branch:
`git push -u origin <branch-name>`. The `-u` sets upstream tracking, which
prevents the error on subsequent pushes.

**Verify the remote first.** Before presenting any push, run `git remote -v`. If
`origin` is not set, make `git remote add origin <url>` the first command in the
block, using the URL stored at session start (`SESSION_START.md`, step 1). This
prevents the "default repo has not been set" error.

**Explanation goes above or below the block, never inside it** as interleaved
prose. Brief `#` comments within the block are fine.

---

## Manual mode: few stops, clear blocks

Every stop in manual mode costs one model request, which resends the whole
conversation, so stops are few and every command block is impossible to miss.

**Every block the user is meant to run looks like this, in every mode**
(semi-autonomous hands over the tag and ref-deletion blocks this way too):

````
`🔢✅ 🔨➖ 🔒✅ 📄✅ 📦⬜ 🚀⬜ · work commit · manual`

### ▶️ RUN THIS — commit + push + open PR · in ~/myapp · 1 block
```bash
# ════════ ▶️ START: commit + push + open PR ════════
git checkout -b feat/x && git add -A \
  && git commit -m "feat: add x" \
  && git push -u origin feat/x \
  && gh pr create --title "feat: add x" --body-file notes.md \
  && echo "✅ DONE: PR open" || echo "❌ STOPPED: scroll up for the error"
# ════════ ⏹️ END ════════
```
### ⏹️ END — nothing else to run
No need to reply. Your next message starts with me checking the PR.
````

- **The label** says what the block does, where to run it, and how many
  blocks there are (`block 1 of 2` when there are several, and the first
  one's END line says "then block 2 below").
- **The START and END comment lines** travel with the paste and do nothing.
  The last command prints ✅ or ❌, so the user sees in their own terminal
  whether the whole chain ran.
- **The tracker line goes above the first block**, and "No need to reply"
  under the last. A test container's 🔑 login stays the very last thing in
  the message, below the block.
- **Anything else in a code box** (a diff, an example, a snippet to read) is
  labeled `📄 FOR READING — don't run`, so it can't be mistaken for a command.

The enforcement checks hold every reply to this (`ENFORCEMENT.md`, C2–C7).

**One block per stop, not per command.** Chain everything up to the next
real decision with `&&`, so the first failure stops everything after it. **A
step that must pass before the next runs is a chained check, not a stop**:
`gh pr checks "$n" --watch --fail-fast` exits non-zero when CI fails, so a
merge chained after it only runs on green. Split only when the user must
**decide** something the shell can't: a conflict, a finding, a result to
inspect by eye.

**A release is two blocks.** Block 1 runs commit → push → open PR, and the
user looks at the PR. Block 2 runs checks → merge → confirm the merge
commit → CI on it → version guard → tag (`SHIP_REFERENCE.md`, step 3).

**No "done" turn.** Say "No need to reply" under every run block. The
user's next message, about anything, starts with one chained read that
verifies the block's result from git state. **When that read finds the block
failed or never ran, raise it first**, before the new request, with the
error and a fixed block. Never "assuming that worked." "Done" still works
for a user with nothing else to say. It just isn't required.

**Timers and watchers save nothing.** A wakeup or a background loop that
waits for the user's paste still ends in a model request, which costs the
same as their reply. A wakeup that fires too early costs more.

**Chained ✅/❌ by shell:** bash, zsh, Git Bash, Termux, WSL and pwsh 7 use
`&& echo "✅ DONE" || echo "❌ STOPPED"`. Windows PowerShell 5.1 has no `&&`:
chain with `; if ($?) { … }` and end with
`if ($?) { "✅ DONE" } else { "❌ STOPPED" }`.

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
environment where Claude presents a clone step. Remote containers arrive
pre-cloned, and local sessions are already in the repo.
- **First time:** a block that clones straight into its final path:
  `git clone <url> ~/storage/shared/projects/<repo>`. Every later block's
  label says `· in ~/storage/shared/projects/<repo>`.
- **Already cloned:** start the block with
  `git fetch origin && git pull origin <branch>` to sync before any work.
