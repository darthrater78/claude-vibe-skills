# Session End Reference

Loaded on demand by the dev-skills skill when the session winds down (`SKILL.md`
§8), a handoff is written (§5.6, §5.9) or the token impact estimate is due
(§5.7). The triggers stay in `SKILL.md`; this file holds the procedure and the
formats.

---

## Session-end checkpoint

**Fires when the session is winding down**: "thanks", "that's all", silence, or any sign the work is done. Before wrapping up, read the
evidence for steps 1–5 in one call (§5.1). It is `;`-separated so that one
failure cannot hide the rest, and each failure is itself a finding.
`<start>` is the `Start:` row of the gate file, the commit the session began
on (`SESSION_START.md`). If the row is missing, say so and diff against
`origin/<default>` instead:

```
git status -sb; git diff --stat <start>; git log --oneline origin/<default>..HEAD; git ls-remote --tags origin "v<version>"; cat .dev-skills-gates.md; docker ps --format '{{.Names}}'
```

1. **Were source files modified this session?** (`git status`, `git diff`
   against `<start>`.) If not, skip the rest, including the token
   estimate: the session was exploratory or advisory.
2. **Show the gate tracker.** Any gate not ✅ or ➖ N/A is unfinished work.
3. **Unmerged branches.** If a branch this session created has commits not
   merged via PR, flag it and offer to finish Gates 5–6.
4. **Untagged versions.** Compare `git ls-remote --tags origin` to the version
   file, and flag an untagged current version the same way. This is a
   backstop: a reclaimed container, a usage limit or a crash never reaches it,
   which is why `SESSION_START.md` step 7 is the primary check.
5. **Orphaned test containers.** Anything this session started for Gate 2
   testing must be gone from `docker ps`. Remove it now if not.
6. **Token impact estimate** (Section 5.7). This checkpoint is its firm
   trigger.
7. **Lessons for the skill itself.** If this session showed a rule, check or
   gap in *this skill* that should change, list them and ask once whether to
   record them (`LESSONS_REFERENCE.md`). A no drops them.

**Remote containers: uncommitted work is destroyed, not pending.** Escalate:

> 🚨 **Remote session ending with uncommitted changes.** These edits exist only
> in this container and will be lost when it is reclaimed. Should I commit and
> push to `<branch>` now?

**Never silently wind down** with uncommitted changes, untagged versions, or
incomplete gates. Surface the gap with the tracker and let the user decide.
Semi-autonomous mode does not skip this checkpoint. Uncommitted changes still
need the user's yes, and Claude then finishes the open gates itself instead of
handing back a block.

---

## Handoff

**One handoff, always replaced.** Write it to `.dev-skills-handoff.md` in the
repo root (gitignored; never under `.claude/`, which prompts on every edit),
overwriting the last one. **Local sessions: commit it locally, never push it**:
save it as a parentless commit on the local-only ref `refs/dev-skills/handoff`,
outside every branch, so no normal push sends it, it never touches the index,
and the one it replaces is garbage-collected. This bookkeeping needs no commit
approval. One call:

```
git update-ref refs/dev-skills/handoff "$(printf '100644 blob %s\tHANDOFF.md\n' "$(git hash-object -w .dev-skills-handoff.md)" | git mktree | xargs git -c user.name=dev-skills -c user.email=dev-skills@localhost commit-tree -m 'dev-skills handoff')"
```

Session start reads it back (`git show refs/dev-skills/handoff:HANDOFF.md`).
**Remote containers: commit and push the file on the working branch**, or it
dies with the container. The user can override either way.

**Handoff format** (also used for the usage-limit handoff below). Keep it under ~30 lines:

```
## Handoff: [task name]
**Goal:** one sentence
**Current state:** what's done, what's verified
**Gate status:** the tracker, with current state
**Mode:** what *this* session ran in; the next session asks again (Operating modes)
**Key files:** path:line — why it matters
**Decisions made:** constraints the next session must respect
**Shell environment:** [user's shell from session start, step 2]
**Next step:** the single concrete next action
```

## Token impact estimate

**Fires at every session-end checkpoint (Section 8) and on request** ("how did
we do?"). The only skip condition is the one gates use: the session modified no
tracked file. "This felt like a small task" is *not* a skip condition.

It is approximate, since billing data is not visible. Build it from per-request
overhead (MCP tools, skills), conversation growth, files loaded, and any time
spent above the Sonnet ceiling. A header and at most 3 lines. Include the MCP
line only when connections changed since the session-start MCP check:

```
Token impact (rough estimate):
✅ Saved ~40k — read only 2 relevant files instead of exploring the package
⚠️ ~30k/turn overhead — 5 connected MCP servers, none used this session
Biggest win next time: disable unused connectors
```

Never let the report become longer than the savings it describes.

## Usage limit handoff

**Offer a handoff (format above) when** a system message mentions overage,
rate limits or a usage cap; the user says they are running low; or the
conversation was compacted. **Do not gate this on a numeric token budget.** On
Claude Code for web it starts at 15M and never visibly falls, so a budget
check never fires. A genuinely low number still counts, but its absence is not
a reason to stay quiet.

> ⚠️ **Heads up — this session looks close to a limit.** If it cuts off mid-task
> you lose the working context. Want a handoff summary now?

Offer once. Don't nag.
