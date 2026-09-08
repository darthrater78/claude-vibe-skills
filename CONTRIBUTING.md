# Contributing to claude-vibe-skills

Thanks for your interest in improving the dev-skills skill.

## Getting started

1. Fork the repo and clone it
2. Install the skill locally by extracting `dev-skills.skill` (it's a zip) to `~/.claude/skills/dev-skills/`
3. Make your changes to files in `skills/dev-skills/`

## The gate workflow

This project follows the same 6-gate workflow the skill enforces. See the [README](README.md) for details. In short:

1. **Version** — bump `VERSION`, `skills/dev-skills/SKILL.md` frontmatter, and `README.md`
2. **Build** — N/A for this repo (no build system)
3. **Security & Quality** — scan your changes
4. **Docs** — update the changelog in `CHANGELOG.md` and any affected README sections
5. **Release** — create a branch, commit, and open a PR
6. **Ship** — merge, tag, and create a GitHub release

## Validation

Rebuild the packaged skill after changing anything under `skills/dev-skills/`,
then run the checks:

```bash
bash scripts/build-skill.sh
bash scripts/validate.sh
```

`validate.sh` checks version consistency across every file, the README size
table, and the bundle against its source — so a stale `dev-skills.skill` fails
validation even when every source file is correct.

**On Git Bash (Windows), `validate.sh` may stall partway through and never
return.** It spawns a few hundred subprocesses across its per-file loops, and
Git Bash emulates `fork()` rather than calling it. This is not a failure — the
stall has no exit code, moves position between runs, and every command it
stops at runs fine on its own. Run the script's sections as separate
invocations (its `echo` headers mark the boundaries), or run it under WSL,
which is also what CI uses. See "Git Bash stalls on spawn-heavy scripts" in
`skills/dev-skills/SHELL_REFERENCE.md`.

## Pull requests

- One logical change per PR
- Branch from `master`, target `master`
- Include a changelog entry for your version
- Keep SKILL.md changes focused — it's loaded every turn, so size matters

## Reporting issues

Use the issue templates for bug reports and feature requests.
