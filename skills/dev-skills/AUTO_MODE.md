# Semi-Autonomous Mode Reference

Loaded on demand by the dev-skills skill, **only when the user has opted into
semi-autonomous mode** (`SKILL.md`, "Operating modes"). A manual-mode session
never needs this file.

The contract is in `SKILL.md`: the user opts in explicitly, Claude runs the
commands instead of presenting them, the tag push and every ref deletion stay
with the user, and **commit approval is untouched**. This file is how that
runs — the two checkpoint formats, the per-step table, the round-trip rules,
and the stop conditions.

Section numbers referenced here (Section 1, 2, 5.7, …) point at `SKILL.md`.

---

## Semi-autonomous mode — execution

The contract is in `SKILL.md` (Operating modes): the user opts in explicitly,
Claude runs the commands instead of presenting them, the tag push and its
follow-on actions are Claude's, and **commit approval is untouched**. This
section is how that runs.

### Entering the mode

The user asks for it. Confirm in one short message — not a lecture — what
changes and what does not, then record it:

> **Semi-autonomous mode on.** I'll run the git commands myself from here —
> commits, pushes, the PR, the merge, watching CI, verification — and I won't
> hand you command blocks unless something fails. What stays yours: **every
> commit still needs your explicit yes**; **the tag push and any ref deletion
> are still yours to run**, because my credentials get `403`'d on exactly those,
> and I'll hand that one block over with a full report of everything I did; and
> anything that needs a decision still comes to you. Say "manual mode" to switch
> back.

Write `Mode: semi-autonomous (approved <date>) — commits and the tag still
require the user's approval` into
`.claude/dev-skills-gates.md` in the same turn. A mode that is agreed to in
conversation and not written down is a mode that disappears at the next
compaction.

On a remote container, nothing extra needs asking: the tag block this mode still
hands over carries no `cd` and no shell-specific syntax (`SESSION_START.md`, step 0,
item 4).

### Checkpoint 1 — the commit approval

Manual mode asks in three places during a release sequence — Gate 1's version
bump, Gate 5's release-notes approval, Gate 6's pre-ship confirmation
(`SHIP_REFERENCE.md`).
Semi-autonomous mode carries the first two into one approval at the commit; the
third becomes the pre-tag report below.

> **Ready to commit — this is the one approval for the release.**
>
> **Version:** 2.25.0 → 2.26.0 (MINOR — one `feat`, no breaking change)
> **Commit:** `feat(skill): add semi-autonomous mode`
> **Changes:** [files, line counts, what each does]
> **Gates:** 🔢 ✅ · 🔨 ✅ · 🔒 ✅ 0 Critical / 0 High · 📄 ✅ · 📦 ⬜ · 🚀 ⬜
> **Release notes (v2.26.0):**
> - [entry]
> - [entry]
>
> On your yes: commit, push the branch, open the PR, and merge it once CI is
> green. Then I'll come back with a full report of everything that happened and
> hand you the tag block to run. I'll stop sooner if anything fails or needs a
> decision.

Three rules about that message:

1. **It is an approval of the sequence it describes, and nothing else.** If the
   scope moves afterwards — more commits land, the notes change, the bump
   changes — present it again. Do not stretch one yes over a second release.
2. **It is not a summary to skim past.** The user is approving content they will
   not see again before it is public. The diff summary and the release notes go
   in it in full, not "see above."
3. **A work commit gets the short form.** No version, no notes, no ship plan —
   the diff, the message, and what Claude will do with it (commit and push to
   the branch). Most commits are work commits; do not run a release checkpoint
   for one, and a work commit has no second checkpoint because it never tags.

### Checkpoint 2 — the pre-tag report, and the tag block

**The tag is the one action in this sequence that publishes, and the user runs
it** — in this mode as in manual, because Claude's credentials are denied on
`refs/tags/*` (Section 5.8). Between the two checkpoints Claude has been running
unattended: commits, pushes, a PR, CI runs, a merge. Semi-autonomous mode pays
for that autonomy here, with a full accounting handed over *with* the tag block
— not a summary, and not a bare set of commands to paste.

**Claude never creates or pushes the tag ref itself, in either mode.** Run
Gate 6 step 2's merge confirmation and the version guard first, then report and
hand over the block:

> **Ready to tag v2.26.0 — full report of everything since your commit
> approval.**
>
> **Commits** (3)
> - `257b224` feat(skill): add semi-autonomous mode — 6 files, +412/−38
> - `4c1a88e` fix(hook): … — 1 file, +4/−2
> - `9ab0e12` chore: tracker — 1 file
>
> **Pushes:** `feature/x` → origin, 3 times (no force, no rewrite)
> **PR:** #48 "…" — opened, 2 review comments addressed, merged as `c3a49f7`
> **CI:** `validate` ✅ on 257b224 · ✅ on 9ab0e12 · ✅ on merge commit c3a49f7
>   (one earlier ❌ on 4c1a88e — shellcheck SC2086, fixed in 9ab0e12)
> **Gates:** 🔢 ✅ all refs 2.26.0, v2.25.0 tagged on remote · 🔨 ✅ validate.sh
>   green, bundle rebuilt · 🔒 ✅ 0 Critical / 0 High, docs-only diff ·
>   📄 ✅ CHANGELOG + README · 📦 ✅ PR #48 merged
> **Version guard:** `VERSION` in merged commit c3a49f7 reads `2.26.0`, matches
>   the tag about to be created ✅
> **Deviations from what you approved:** the CI failure above added one commit
>   that was not in the original diff; nothing else changed.
>
> **What the tag does:** pushing `v2.26.0` fires `.github/workflows/release.yml`,
> which builds the bundle and publishes the GitHub release with the notes you
> approved.
>
> **This one is yours to run** — my credentials get `403`'d on tag refs. From
> your local clone of the repo:
>
> ```
> git checkout main && git pull origin main \
>   && grep -q '^2.26.0$' VERSION \
>   && git tag v2.26.0 && git push origin v2.26.0
> ```
>
> Tell me when it's done and I'll take it from there — watch the run, add the
> notes, verify, and commit the SHIP record. The branch deletion is yours too;
> I'll give you that block at the end.

**Rules for this report:**

1. **Every action, not the highlights.** Commits with SHAs and messages, every
   push and whether any rewrote history, the PR and what happened on it, every
   CI run with its conclusion, the merge commit, each gate with the evidence
   that passed it, the version guard result.
2. **Failures, retries, and deviations are the part that matters most.** A run
   that failed and was fixed, a gate that had to be re-run, anything that
   differs from what the user approved at the commit — state it plainly. A
   report that only lists successes is the report nobody needed.
3. **Reconstruct it from evidence, not memory** (`git log`, `gh pr view`,
   `gh run list`, `git ls-remote`, the gate file). If the session was compacted,
   re-derive; a gap you cannot close is something to say, not something to omit.
4. **The block goes in the same message, below the report** (Section 1: the
   tracker and the report go above the block, never after it). No `cd` and no
   clone-path question — "from your local clone" in the prose, and the block
   copyable as given. If the user asks for changes instead of running it,
   nothing about the tag moves: handle the request and report again.
5. **Do not take "done" at face value.** 🚀 SHIP stays ⏳ until Claude has
   confirmed the tag on the remote *and* checked what it points at against the
   merge commit (`SHIP_REFERENCE.md`, step 3). Reading refs is not a write and is not
   restricted.
6. **It runs for pre-release tags too.** A `-dev`/`-rc` tag publishes an
   artifact; that is the trigger for this checkpoint, not the version's shape.

### Running the sequence

After the yes, the gates run in the normal order with the normal pass criteria.
What changes is only the execution:

| Step | Manual mode | Semi-autonomous mode |
|---|---|---|
| Commit | presented | Claude runs it |
| Branch push | presented (executed in a container) | Claude runs it |
| PR create | presented | Claude runs it |
| Release notes approval | separate ask (Gate 5, step 6) | folded into checkpoint 1 |
| PR merge | presented | Claude runs it, after the merge-confirmation checks — without `--delete-branch` |
| Pre-ship confirmation | separate "type ship" (Gate 6) | **checkpoint 2 — the full pre-tag report, handed over with the block** |
| Tag + tag push | **the user's, in every environment** | **the user's, in every environment** |
| Watch CI, add notes, verify | Claude, either way | Claude, either way |
| Branch cleanup (a ref deletion) | presented | presented — the user's in both modes |
| Tracker SHIP ✅ commit | presented | Claude runs it |

**The last column is where the mode's value is, and the two rows that don't move
are why it is still called semi-autonomous.** Everything Claude can actually do
with its own credentials, it does; the two ref operations the remote denies stay
where they have always been.

**Everything that was a check stays a check.** In particular, `SHIP_REFERENCE.md` step 2's
merge confirmation (`state` reads `MERGED`, and CI ran green *on the merge
commit*) is not a formality that existed because a human was about to paste a
block — it is what stops the tag from landing on the previous commit. Run it
before tagging, exactly as written. The version guard that manual mode chains
into the tag block (`grep -q` against the version file) becomes a check Claude
performs before `git tag`: read the version out of the merged commit, compare it
to the tag being created, and stop if they differ.

**Pre-release tags are handed over the same way.** A dev, alpha, beta, or rc
tag (`v1.2.3-dev.1` — `WORKFLOW_REFERENCE.md`, "Dev releases") is a tag push, so
both modes hand it to the user, with the pre-tag report above it in this one.
What it is *not* is a shortcut around the track rules: a pre-release tag still publishes an artifact,
so it is a release sequence with all six gates, not a work commit. The one thing
it relaxes is the branch — a pre-release tag is expected on a feature branch,
and the workflow's tag-on-default-branch check skips it by design.

**Report progress as a running line, not a narration.** One message when the
sequence starts, one at the pre-tag report, one when it finishes, and one
whenever it stops. Between those, the tracker file is the record — and it is
also where the pre-tag report is reconstructed from, which is another reason to
keep it current as each gate transitions rather than at the end.

### Round trips — what this mode costs, and how to spend less of it

This mode's one real cost is tool-call round trips. A presented block costs
nothing to produce; a chain of executed commands resends the whole conversation
on every call, so the same sequence gets more expensive the more calls it is
split across. That is the trade the user accepted when they opted in
(`SKILL.md` §5.8) — it is not a reason to talk them out of the mode, and not a
reason to skip a check. It is a reason not to spend calls carelessly.

**Chain a step's commands into one invocation.** The commit-and-push step is
one call, not three:

```
git add -A && git commit -m "<message>" && git push -u origin <branch>
```

The gates are unchanged by this — the pre-flight ran before the first
character of that line was written, and the approval covers the sequence it
described. What changes is that three round trips become one. The same applies
anywhere a step is several commands that must all succeed: `&&` them, and let
the first failure stop the chain.

**Gather evidence in one call, not one per source.** Checkpoint 2's report is
reconstructed from `git log`, `gh pr view`, `gh run list` and the gate file.
Read them together:

```
git log --oneline <base>..HEAD && gh pr view --json state,mergeCommit,url \
  && gh run list --limit 5 && cat .claude/dev-skills-gates.md
```

**Do not chain across a stop.** Anything the user must see or decide between
two commands is a boundary the chain does not cross: the commit approval, the
tag block, a gate that has not passed, a failed command whose output changes
what comes next. Chaining is for commands that were always going to run in
sequence with no judgment between them. When in doubt, split — a wasted round
trip is cheaper than an action the user did not approve.

### When it stops

Semi-autonomous mode falls back to manual behavior for the operation that failed. The
session stays semi-autonomous; the tracker is updated before Claude reports.

| What happened | What Claude does |
|---|---|
| A required gate is not ✅ or ➖ N/A | Stop, surface the blocking gate by name, run it. Never edit the tracker to clear it |
| Branch push returns `403` | Present the block, report it plainly. No retry, no re-route, no different ref |
| The tag or a ref deletion is due | Not a failure — the block goes to the user by design, with the report above it (checkpoint 2) |
| `src refspec ... does not match any` | Not a permissions failure: the tag was never created. Re-run `git tag`, then push (`SHIP_REFERENCE.md`, step 3) |
| CI fails on the PR | Stop before merging. Report the failing job and its output, propose a fix, wait |
| The release workflow fails after the tag | Stop. Recovery needs a tag deletion, which needs its own approval (`SKILL.md`, Operating modes) |
| A Critical or High security finding | Hard stop, same as manual |
| A decision with more than one defensible answer | Ask. Semi-autonomous mode is not permission to pick for the user |

