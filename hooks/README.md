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

**Semi-autonomous mode moves every path into the covered half.** When a session opts
into semi-autonomous mode (`SKILL.md`, Operating modes), Claude runs the commits,
pushes, PR, merge, and the tag push itself, so each one arrives as a tool call
this hook inspects — including `git tag` and `git push origin v1.2.3`, which in
manual mode are handed to you and never reach it. Installing the hook matters
most in exactly that mode: it is the only enforcement that does not depend on
Claude remembering to run the pre-flight it just granted itself more room in.

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
counts as satisfied when its **row** — the line naming the gate, plus any
continuation lines below it up to the next gate or a blank line — carries
✅ (passed) or ➖ (N/A). Anything else — ⬜ pending, ⏳ in progress, 🚫 blocked,
or a gate missing from the file — blocks. (Reading only the first line used
to miss a status or `handoff` annotation that wrapped onto a continuation
line; the hook now reads the whole row.)

Required gates scale with the operation, matching the two tracks in Section 2:

| Operation | Gates required |
|---|---|
| `git commit`, `git push` to a branch | SECURITY |
| `gh pr create`, MCP `create_pull_request` | VERSION, BUILD, SECURITY, DOCS |
| `git tag`, `git push --tags`, `git push origin main`, `gh pr merge`, `gh release create`, MCP `merge_pull_request` | VERSION, BUILD, SECURITY, DOCS, RELEASE |

Read-only git (`status`, `diff`, `log`, `tag -l`, `fetch`) is never blocked.

**Local-artifact-handoff annotation (BUILD only).** GATE_REFERENCE.md's Gate 2
requires offering the user a way to try a compiled artifact (Docker image,
Windows `.exe`, Android `.apk`) by hand before BUILD passes — a conversational
step the hook cannot observe directly. Where BUILD is required for the
operation, the hook additionally denies a BUILD line marked ✅ that contains no
`handoff` annotation, in any repo with a Docker/.exe/.apk build signal
(`Dockerfile`, `.csproj`/`.sln`, or an Android Gradle project — `build.gradle`,
`build.gradle.kts`, or `AndroidManifest.xml`). Write the outcome onto the BUILD
line itself, e.g. `✅ debug build verified; handoff offered, user declined to
try it` or `✅ ...; handoff n/a (remote container / Termux session)` — see
GATE_REFERENCE.md, Gate 2, for the full convention. A ✅ with no annotation in a
matching repo reads as "the offer never happened," not "forgot to write it
down."

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

# handoff annotation check — run from a repo with a Dockerfile/.csproj/.sln/
# Android Gradle project and a gate state file with a bare "BUILD ✅" line
# (no "handoff" text):
# expect: deny, naming the missing handoff annotation
printf '{"tool_name":"Bash","cwd":"'"$PWD"'","tool_input":{"command":"gh pr create --title x --body y"}}' \
  | .claude/hooks/gate-preflight.sh
```
