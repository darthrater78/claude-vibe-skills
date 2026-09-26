# Skill Lessons Reference

Loaded on demand by the dev-skills skill, **only when a session has found a
lesson that would make the skill itself better** (`SKILL.md` Section 8), and at
session start in the skill's own repo when lessons are waiting there. Section
numbers point at `SKILL.md`.

---

## What counts as a lesson

Something this session showed about **the skill**, not about the project:

- a rule that misfired, or that Claude had to guess at because it was unclear
- an enforcement check that blocked something it shouldn't have, or missed
  something it should have caught
- two skill files that disagree, or a reference that points nowhere
- a case the skill doesn't cover that came up for real
- a recurring cost the skill caused (a reply bounced again and again, a
  question asked every session for no reason)
- the user correcting how the skill made Claude behave

Not a lesson: a bug in the project, a preference that only fits this project,
or anything already fixed in a newer skill release (`skill_latest`).

## Calling it out, and asking

Note each lesson in one line when it happens, and keep working. **Ask once**,
at the session-end checkpoint or with the handoff, whichever comes first, for
all of them together:

> 💡 **This session turned up [N] lesson(s) for the dev-skills skill itself:**
> - [one line each]
>
> Want me to record them for the skill? [Where they'd go, per below.]

**Declined means dropped**: don't ask again this session and don't record
them. Never record one without a yes.

**What goes in a lesson:** what happened (the rule or check, the file and
section), why it was wrong or costly, and a proposed fix. Describe the skill's
behavior, never the project: no code, file contents, secrets, hostnames or
customer details. Name the project only by its repo name.

## Where it goes

**Find the skill's repo on this machine** (only after the yes):

```bash
for d in "$HOME"/*/ "$HOME"/*/*/; do [ -e "$d.git" ] && git -C "$d" remote get-url origin 2>/dev/null | grep -qi 'claude-vibe-skills' && echo "$d"; done; true
```

**Found:** append to the lessons ref there, a local-only commit on
`refs/dev-skills/lessons` (the same idea as the handoff ref, `SKILL.md` §5.6).
It never touches that repo's working tree, index, branches or its own
handoff, and nothing pushes it. Lessons **append** until a session in the
skill repo takes them up, so one from another project isn't lost. One call,
with the repo path written out literally:

```bash
R=/home/me/claude-vibe-skills; { git -C "$R" show refs/dev-skills/lessons:LESSONS.md 2>/dev/null; cat <<'EOF'
## <YYYY-MM-DD> · from <project repo name> (skill v<installed version>)
- **What happened:** …
- **Why it matters:** …
- **Proposed fix:** <file, section, change>
EOF
} | git -C "$R" hash-object -w --stdin | xargs printf '100644 blob %s\tLESSONS.md\n' | git -C "$R" mktree | xargs git -C "$R" -c user.name=dev-skills -c user.email=dev-skills@localhost commit-tree -m 'dev-skills lessons' | xargs git -C "$R" update-ref refs/dev-skills/lessons
```

Then confirm in one line where it went.

**Not found:** show it as a blurb the user can keep or paste into an issue at
`https://github.com/darthrater78/claude-vibe-skills/issues/new`, in a
`📄 FOR READING — don't run` block with the same three lines per lesson.

## In the skill's repo: picking them up

The session-start probe's `lessons` key shows a date when lessons are
waiting. Read them (`git show refs/dev-skills/lessons:LESSONS.md`) and list
them in one line each before "What are we building?". The user picks which to
work on. Once they have been taken up or dismissed, clear the ref
(`git update-ref -d refs/dev-skills/lessons`, a local ref, not a remote one).
A lesson the user wants kept for later stays until they say otherwise.
