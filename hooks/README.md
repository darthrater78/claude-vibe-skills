# Enforcement checks — optional "always on" install

**You don't need anything in this folder for the checks to work.** Since
2.37.0 the enforcement checks ship inside the skill (`checks/enforce.py`), and
Claude Code turns them on by itself when the skill loads, via the `hooks:`
block at the top of `SKILL.md`. Every check, what it reads, and how to decline
them for a session is in
[`skills/dev-skills/ENFORCEMENT.md`](../skills/dev-skills/ENFORCEMENT.md).

This folder is for one extra case: running the same checks in **every**
session on a machine, including sessions that never load the skill.

## Before you do this

- **They run in every project.** A repo with no gate file gets its git writes
  denied ("no gate file"), which is right for dev-skills projects and noise
  for anything else. The skill-loaded default doesn't have this problem.
- **Declining still works.** It's the same `Hook enforcement: declined` row in the
  project's gate file.
- **They need Python 3.** Unlike the skill-loaded version, the commands here
  have no fallback: if `python3` is missing, the check errors and Claude Code
  lets the action through. The skill-loaded version blocks git, gh and docker
  instead.

## Install

1. Install the skill as usual, so `checks/enforce.py` exists under your skills
   folder (normally `~/.claude/skills/dev-skills/`).
2. Merge [`settings.example.json`](settings.example.json) into
   `~/.claude/settings.json`. If that file already has a `hooks` key, merge
   the arrays rather than replacing them. If your skills folder is elsewhere
   (a custom `CLAUDE_CONFIG_DIR`, for example), change the three paths.
3. Start a new session and check the banner for `Hook enforcement: ✅ active`.

When both this install and the skill are active, each check runs twice with
the same answer. That's harmless, but you can drop this install again once you
only use dev-skills sessions.

## Replaced: `gate-preflight.sh`

Before 2.37.0 this folder held `gate-preflight.sh`, a bash checker you had to
install by hand. Nothing installed it automatically, so on most machines it
never ran. `checks/enforce.py` replaces it: it covers everything the old
checker did, closes the gaps found in the 2.37.0 review (prefixed and wrapped
commands, pushes to the default branch, decoy ✅ lines), and adds the Docker,
gate-file, reply and unanswered-question checks. If you installed the old
script, remove its entries from your `settings.json` and delete
`.claude/hooks/gate-preflight.sh`.
