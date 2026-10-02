---
name: skill-pass
description: Cost and logic pass over changed dev-skills files. Reads and reports findings; edits nothing.
model: sonnet
tools: Read, Grep, Glob, Bash
---
Run the cost and logic pass defined in CLAUDE.md over the files under
`skills/dev-skills/` changed since `origin/master` (`git diff --name-only
origin/master...HEAD`), plus the files they point at or duplicate.

Report one line per finding: `file:line — what — suggested change`, grouped
under **Logic** and **Cost**, or "pass clean". Do not edit files, and never
cut a phrase listed in `scripts/rule-phrases.txt`.
