# Session End Reference

Loaded on demand by the dev-skills skill when a handoff is written
(`SKILL.md` §5.6, §5.9) or the token impact estimate is due (§5.7, §8). The
triggers stay in `SKILL.md`; this file holds the procedure and the formats.

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
