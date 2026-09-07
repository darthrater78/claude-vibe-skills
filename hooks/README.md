# Gate pre-flight hook

`gate-preflight.sh` is a `PreToolUse` hook that blocks git write operations when
the gates they require have not passed.

SKILL.md asks Claude to check the gates before every git write. This hook makes
that check unskippable for anything Claude executes itself — it is the
deterministic half of gate enforcement, and prose is the other half.

## What it covers, and what it can't

| Path | Covered |
|---|---|
| Claude runs `git commit` / `git push` / `git tag` / `gh pr create` / `gh pr merge` / `gh release create` | ✅ |
| Claude calls GitHub MCP write tools (`create_pull_request`, `merge_pull_request`, `push_files`, …) | ✅ |
| Claude **presents** commands for you to paste into your own terminal | ❌ — nothing intercepts your terminal |
| You run git yourself | ❌ |

That gap is why SKILL.md Section 1 defines presenting a command as performing it.
The hook is strongest exactly where Claude executes git directly — remote
container sessions (`GATE_REFERENCE.md`, session start, step 0) — and weakest on local sessions,
where presenting commands is the default.

## Install

The hook is **project-scoped by default**: it only governs repos you install it
in.

```bash
mkdir -p .claude/hooks
cp hooks/gate-preflight.sh .claude/hooks/
chmod +x .claude/hooks/gate-preflight.sh
```

Then merge `hooks/settings.example.json` into the repo's `.claude/settings.json`.
If that file already has a `hooks` key, merge the arrays rather than replacing
them.

To govern every repo instead, put the same block in `~/.claude/settings.json`
and use an absolute path to the script. Note that a global install enforces gates
in repos that have no gate state file, which the hook treats as "no evidence any
gate ran" — see Failure modes.

**Requires `jq` or `python3`** to parse the hook payload. The hook fails closed:
with neither available it denies rather than allows, per SKILL.md Section 4
("fail closed — when something unexpected happens, deny rather than allow").

## What it checks

Source of truth is `.claude/dev-skills-gates.md` (SKILL.md Section 2). A gate
counts as satisfied when its line carries ✅ (passed) or ➖ (N/A). Anything else
— ⬜ pending, ⏳ in progress, 🚫 blocked, or a gate missing from the file — blocks.

Required gates scale with the operation, matching the two tracks in Section 2:

| Operation | Gates required |
|---|---|
| `git commit`, `git push` to a branch | SECURITY |
| `gh pr create`, MCP `create_pull_request` | VERSION, BUILD, SECURITY, DOCS |
| `git tag`, `git push --tags`, `git push origin main`, `gh pr merge`, `gh release create`, MCP `merge_pull_request` | VERSION, BUILD, SECURITY, DOCS, RELEASE |

Read-only git (`status`, `diff`, `log`, `tag -l`, `fetch`) is never blocked.

## Failure modes

**No gate state file** → denied. There is no evidence any gate ran, and per
Section 2 unknown is never "passed." Re-derive state from evidence and write the
file.

**Neither `jq` nor `python3`** → denied, with instructions to install one.

**Bypass:** `DEV_SKILLS_GATE_HOOK=off` disables the hook entirely. It exists for
debugging the hook itself, not for getting past a gate — the supported way past
a gate is to run it, or to mark it ➖ N/A for a structural reason on the tracker.

## Testing it

```bash
# expect: deny
printf '{"tool_name":"Bash","cwd":"'"$PWD"'","tool_input":{"command":"git tag v1.0.0"}}' \
  | .claude/hooks/gate-preflight.sh

# expect: no output (allow)
printf '{"tool_name":"Bash","cwd":"'"$PWD"'","tool_input":{"command":"git status"}}' \
  | .claude/hooks/gate-preflight.sh
```
