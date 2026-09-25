# Enforcement checks

Session start reads only the "At session start" section below (the
disclosure and the keep-or-decline question). The whole file loads whenever a
check blocks something, or the user asks what the checks do. This is the full disclosure:
what the checks are, what they read, what each one blocks, how to decline them,
and what they cannot catch.

---

## What they are

Most of this skill is **instructions**: text Claude follows, which nothing
checks. The **enforcement checks** are different. They are a small program,
`checks/enforce.py` inside the skill folder, that **Claude Code runs on its
own** at fixed points:

| When | What Claude Code hands the checks |
|---|---|
| Before Claude runs a command or edits a file | the command, or the file path and the new text |
| When Claude is about to end a reply | the reply text |
| After the user answers Claude's multiple-choice questions | the questions and the answers |

They **only read**: the payload above, the project's gate file
(`.claude/dev-skills-gates.md`), and a compose file that a `docker compose`
command is about to start. They answer **allow**, **deny** (the action doesn't
happen, and Claude sees why), **ask** (Claude Code asks the user), or **fix the
reply** (Claude has to correct the reply before it ends). **They never run a
command.** The one thing they write is a status marker in the system temp
folder (`dev-skills-enforcement/<session id>`), so the session banner can say
whether they are active.

**The hooks are one layer, not the only guardrail.** Every gate, approval and
rule in the skill applies whether or not they run. Claude follows those as
instructions, and the hooks add an automatic check that it did. So the status
is always worded **"Hook enforcement"**: `⚠️ Hook enforcement: not active`
means the instructions still apply without the automatic check, never "no
guardrails".

## Where they live, and when they're on

- **In the skill itself**: the `hooks:` block at the top of `SKILL.md`.
  Claude Code registers them when the skill loads and keeps them on until the
  session ends. There's nothing to install and no settings to edit. A session
  that never loads the skill has no checks, and no gates either.
- **They need Python 3** on the machine, found as `python3`, `python` or,
  on Windows, the `py -3` launcher. If Python 3 or the checks file is
  missing, `git`, `gh` and `docker` shell commands and GitHub tools are **blocked**, not let through
  unchecked, and the banner says `⚠️ Hook enforcement: not active — instructions still apply`.
- **They find their own folder through `CLAUDE_PLUGIN_ROOT`**, which Claude Code
  sets to the skill's folder when it runs a skill's checks. This was verified
  on Claude Code 2.1.281. It is **not documented** for skills, only for
  plugins, so a future Claude Code version could change it. If that happens,
  the checks fail closed as above and the banner says so. They never fail
  silently.
- **Claude can't edit its way out.** Changes to the gate file that decline
  enforcement, approve host networking or waive a finding, and any edit to a
  Claude Code settings file or to the installed checks, go to the user as a
  permission prompt (check B5).

## At session start: disclose, then keep or decline

Every session, before the mode question, tell the user in a few lines, in the
first message that asks anything:

> 🛡️ **Enforcement checks** are on for this session: a small program in the
> skill folder that Claude Code runs on its own. It reads my commands, the
> files I edit, my replies and the gate file, and it only allows, denies or
> asks you. It never runs anything. It blocks git writes whose gates haven't
> passed, test containers not on your LAN IP, host networking you haven't
> approved, unlabeled or ungated command blocks, and loopback test URLs, and
> it flags questions you didn't answer. Full list: `ENFORCEMENT.md`.

Then ask, in the same `AskUserQuestion` call as the mode question: **"Keep the
enforcement checks on for this session?"** with the options `Keep them on`
and `Decline for this session`. It's all or nothing, with no recommendation
label. When the probe says `enforcement=NOT-ACTIVE`, don't ask. Say that
they aren't running and why, and that the session relies on instructions
only.

- **Keep:** nothing to do. The banner shows `Hook enforcement: ✅ active`.
- **Decline:** add `Hook enforcement: declined (<date>)` under the `Mode:` row with
  the Edit tool. Claude Code asks the user to confirm that line (check B5),
  so the user confirms the decline in Claude Code's own dialog, and Claude
  can't write it on its own. Every check then stands down, except B5 itself.
  The banner and every tracker show `⚠️ Hook enforcement: declined — instructions
  still apply`.
- **Per session**, like the mode. A new session asks again, and a row left
  over from an earlier session is overwritten, not inherited.
- **Unanswered** is asked again, like the mode. It never defaults.

## The checks

Deny, ask and fix-the-reply are described above. Each rule below has test
cases in `scripts/test-checks.py`, run by `scripts/validate.sh` and CI, so a
check can't get weaker without the build failing.

### A. Commands Claude runs

**A1. Test containers publish on the LAN IP only.**
`docker run`/`create`/`compose up|create|run|start` is denied when a published
port is on `127.0.0.1`, `localhost`, `0.0.0.0`, `::1` or no IP at all (a bare
`-p 8080:8080`, or `-P`), or on an IP that is not the host's own LAN address
(the source address of its default route), including a Docker bridge such as
`172.17.0.1` and any public IP. A port using `$HOST_IP` passes only when the
same command sets `HOST_IP` with the documented recipe
(`ip -4 route get 1.1.1.1`). Compose files are read for `ports:` (short and
long syntax). No published ports passes.

**A2. Host networking needs the user's permission.** `--network host`,
`--net=host` or `network_mode: host` is denied unless the gate file has
`Host network: <container> approved <date> — <reason>`, which only gets there
through the B5 prompt.

**A9. Test containers don't outlive the session.** A container with a
restart policy (`--restart always|unless-stopped|on-failure`, or compose
`restart:` other than `no`) that also bind-mounts from a temp folder
(`/tmp`, `/var/tmp`, the system temp dir, including Claude's `/tmp/claude-*`
scratchpads) is denied. A reboot wipes the temp folder, Docker restarts the
container, and it recreates the missing folder as root, which then breaks
Claude Code's own temp directory. Temp mounts with `--rm` or no restart
policy pass, and so do restart policies with mounts outside temp.

**A10. Temp-folder mounts are never root's.** A bind mount under a temp
folder is denied when the container doesn't run as the user (no
`--user "$(id -u):$(id -g)"`, no `PUID`+`PGID`), when the folder doesn't
exist yet (Docker would create it as root) unless an earlier `mkdir -p` in
the same command creates it, or when it exists but belongs to someone else.
A container that has to run as root mounts from outside temp, for example
`/opt/docker/<name>-test/`. Mounts outside temp, `--mount` sources (Docker
refuses a missing one instead of creating it) and named volumes pass.

**A12. Test containers are labeled, and leftovers are found.** A container
Claude starts needs `--label dev-skills.test="$CLAUDE_CODE_SESSION_ID"`, and a
compose stack runs as `-p dev-skills-test-<name>` (or labels its services).
Every session start lists labeled containers an earlier session left behind,
and Claude hands the user a block to remove them before new work. That
matters because a session that crashes or is cut off never reaches its own
cleanup. The checks never remove anything themselves.

**A4. Gates before git writes.** A Bash or PowerShell command containing `git commit`,
`git push`, `gh pr create|merge`, `gh release create`, or a `gh api` merge or
release, even behind `env`, `sudo`, `VAR=…`, `bash -c`, `eval`, `$( )`, `cd … &&`
or `;`, is checked against the gate file. So is the PowerShell and Windows
spelling of each: `git.exe` or a full path to it, `&`, `iex`/`Invoke-Expression`,
`pwsh`/`powershell -Command` or `-EncodedCommand`, `cmd /c`,
`Start-Process` (with its `-WorkingDirectory`), and a `Set-Location` into
another repo. A heredoc or here-string (`<<<`) fed to a shell is checked as
commands. Any other heredoc is data: a quoted one (`python3 - <<'EOF'`) is
not read, and an unquoted one is read only for `$( )`. The gates it needs:
- commit, or a push to a non-default branch: **SECURITY**
- opening a PR: **VERSION, BUILD, SECURITY, DOCS**
- a merge, a release, or **any push that lands on the default branch**
  (`master`, `HEAD:master`, `feat:master`, a bare `git push` while on it):
  those plus **RELEASE**, and the SECURITY row must say `0 open`

A gate passes only when **its own row**, the line that starts with its emoji
and name (`🔒 SECURITY`), has ✅ or ➖ **on that line**. `Previous:`,
`Standards:` and evidence lines never count. In a repo that builds a Docker
image, `.exe` or `.apk`, a ✅ BUILD needs a `handoff` note, and a merge needs
`test artifact:` (plus `test creds` for Docker) on the BUILD row. In a fork,
every `gh` write must name the fork with `--repo` and every push must go to
`origin`. GitHub MCP tools are checked the same way, whatever the server is
named.

**A5. No git writes until the mode is chosen.** A `Mode:` row that is
missing, `unchosen`, or anything but `manual`/`semi-autonomous` denies A4's
commands.

**A6. Tags and ref deletions are the user's.** `git tag <name>`, pushing a
tag, `--tags`, `--delete`, `:ref`, `gh pr merge --delete-branch`,
`gh release delete`, and `gh api` ref creation or deletion are denied in both
modes. Listing tags and deleting a local tag pass.

### B. Files Claude edits

**B5. The gate file, settings and the checks go through the user.** An edit
to `.claude/dev-skills-gates.md` that **adds** any of these lines asks the
user, showing the lines:
- `Hook enforcement: declined`
- `Host network: … approved`
- anything mentioning a waiver

**Gate rows and the `Mode:` line pass without asking, in both modes.** The
mode is the user's answer to the session-start question, and a gate passing
is shown on the tracker and backed by the commit approval (and, in
semi-autonomous mode, the pre-tag report). A prompt for each would ask the
user to approve bookkeeping they already approved. A gate row that mentions a
waiver still asks, because of the waiver.

Other gate-file edits (⏳, evidence, a new session's ⬜ rows) pass. Any edit to
a Claude Code `settings.json`/`settings.local.json` (`/` or Windows `\`
paths) or to the installed checks folder asks. A shell command that looks
like it writes any of those files asks, including PowerShell's
`Set-Content`/`Out-File`/`Copy-Item` family, their aliases and
`[IO.File]::` writes, so the gate file is edited with the Edit/Write tools, where the change
can be shown line by line. `git rm --cached` on the gate file passes: it only
untracks it.

**B6. The gate file stays out of local commits.** A `git add` that names
`.claude/dev-skills-gates.md`, or force-adds `.claude/`, `.` or `-A`, is
denied on a local session. Every session rewrites the file, so a committed
copy leaves the tree dirty and blocks `git checkout`. A remote container
(`CLAUDE_CODE_REMOTE` set, as Claude Code on the web does) may stage it,
because its copy dies with the container.

### C. Claude's replies

**C1. No loopback or bridge test URLs.** An `http(s)://` URL to `localhost`,
`127.x`, `0.0.0.0`, `[::1]` or `172.17–19.x` in the reply must be replaced with
the LAN URL that `curl` reached.

**C2. Presented git blocks obey the gates.** A code block with a git write is
checked exactly like A4 and A5, because presenting a command is performing it.
A tag push or ref deletion in a presented block also needs every gate
through RELEASE ✅, so it can't be handed over before the merge is confirmed.

**C3. Run blocks are labeled.** A code block with a `git` or `gh` command
needs:
- `### ▶️ RUN THIS — <what it does>` directly above it
- `# ════════ ▶️ START: <what>` as its first line
- `# ════════ ⏹️ END` as its last line
- `### ⏹️ END` directly below it

With more than one run block, each label says `block N of M`. Blocks inside a
`>` quote count. A block labeled `📄 FOR READING — don't run` is exempt.

**C4. No `cd` in run blocks.** Blocks assume the terminal is already in the
repo.

**C5. The gate tracker appears above the first run block.**

**C7. "No need to reply" appears under the last run block.**

A reply is sent back for fixing at most twice per user message. The third
time it goes through with a visible warning listing what's still wrong, so a
check that misfires can't trap the session.

### D. The user's answers

**D1. Never proceed on an unanswered question.** After a multiple-choice
question, any question with no answer adds a notice to what Claude sees:
re-ask it, and don't pick a default. An answer typed in the user's own words
adds a notice to respond to it before acting. This can't block: the answers
have already arrived.

## What they can't catch

- **Judgment:** whether the track is right, whether a ➖ N/A reason is real,
  finding severity, whether docs match behavior, code quality. These stay
  instructions.
- **Whether "yes" meant commit approval.** Commit approval stays an
  instruction.
- **Commands the user runs.** C2–C7 check what Claude hands over. What the
  user actually pastes is theirs.
- **Anything while declined**, apart from B5.
- **A gate file that is already tracked.** B6 stops it being staged by name,
  but once an earlier commit tracks it, `git add -A` or `git commit -a` picks
  up its changes. Session start untracks it (`SESSION_START.md`).
- **Whether a gate row is honest.** Gate rows and the `Mode:` line pass
  without a prompt (B5), so the git-write checks trust what the file says.

## When a check blocks

Treat it as the gate it is: run what's missing, then retry. **Never** reword a
command to slip past a check, split it to hide an operation, write the gate
file from the shell, or ask the user to decline enforcement to get something
through. If a check looks wrong, say so, show the command and the reason, and
let the user decide.

## Always on, outside the skill (optional)

To run the checks in every session on a machine, whether or not the skill is
loaded, add the same three entries to `~/.claude/settings.json`, with the
installed skill's absolute path in place of `${CLAUDE_PLUGIN_ROOT}`. See
`hooks/README.md` in the repository. This is opt-in and not required.
