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
| Before Claude runs a command, edits a file, or calls a GitHub tool | the command, the file path and the new text, or the tool's arguments |
| When Claude is about to end a reply | the reply text |
| After the user answers Claude's multiple-choice questions | the questions and the answers |

They **only read**: the payload above, the project's gate file
(`.dev-skills-gates.md`), a compose file that a `docker compose`
command is about to start, and the `[alias]` sections of your git config
(`~/.gitconfig`, `~/.config/git/config` and the repo's `.git/config`), so an
alias can't hide a git write. They answer **allow**, **deny** (the action doesn't
happen, and Claude sees why), **ask** (Claude Code asks the user), or **fix the
reply** (Claude has to correct the reply before it ends). **They never run a
command.** The one thing they write is a status marker in the system temp
folder (`dev-skills-enforcement-<user>/<session id>`), so the session banner can say
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
- **On Windows they run in Git Bash**, which Git for Windows installs and
  Claude Code finds by itself (or through `CLAUDE_CODE_GIT_BASH_PATH`). The
  hooks are pinned to bash, so without Git Bash Claude Code reports "requires
  bash but Git Bash was not found" and the banner shows them not active. The
  checks read and write UTF-8 whatever the Windows code page is, and they cover
  the PowerShell tool as well as Bash.
- **They find their own folder through `CLAUDE_PLUGIN_ROOT`**, which Claude Code
  sets to the skill's folder when it runs a skill's checks. This was verified
  on Claude Code 2.1.281, and on 2.1.284 for both a hand-installed copy and
  one synced from claude.ai. Claude Code's own hook error says it "is available
  for skill hooks", but the docs still describe it only for plugins, so a
  future Claude Code version could change it. If that happens,
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
> approved, unlabeled or ungated command blocks, loopback test URLs, and
> workflow edits that add an unpinned action or a `${{ }}` in a script, and
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
same command sets `HOST_IP` with the documented recipe (`ip -4 route get
1.1.1.1` on Linux, `Find-NetRoute -RemoteIPAddress 1.1.1.1` on Windows, from
PowerShell or through `powershell.exe` in Git Bash). Compose files are read for `ports:` (short and
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
policy pass, and so do restart policies with mounts outside temp. Linux hosts
only: Windows doesn't clear `%TEMP%` at boot.

**A10. Temp-folder mounts are never root's.** A bind mount under a temp
folder is denied when the container doesn't run as the user (no
`--user "$(id -u):$(id -g)"`, no `PUID`+`PGID`), when the folder doesn't
exist yet (Docker would create it as root) unless an earlier `mkdir -p` in
the same command creates it, or when it exists but belongs to someone else.
A container that has to run as root mounts from outside temp, for example
`/opt/docker/<name>-test/`. Linux hosts only: Docker Desktop on Windows
creates a missing mount folder as the Windows user. Mounts outside temp, `--mount` sources (Docker
refuses a missing one instead of creating it) and named volumes pass.

**A12. Test containers are labeled, and leftovers are found.** A container
Claude starts needs `--label dev-skills.test="$CLAUDE_CODE_SESSION_ID"`, and a
compose stack runs as `-p dev-skills-test-<name>` (or labels its services).
Every session start lists labeled containers an earlier session left behind,
and Claude hands the user a block to remove them before new work. That
matters because a session that crashes or is cut off never reaches its own
cleanup. The checks never remove anything themselves.

**A4. Gates before git writes.** A Bash or PowerShell command containing `git commit`,
anything else that writes a commit (`git merge`, `cherry-pick`, `revert`, `am`,
except `--ff-only`, `--no-commit`, `--squash` and `--abort`; a `git pull` of a
branch other than the one checked out, except `--ff-only` and `--rebase`),
`git push`, `gh pr create|merge|update-branch`, `gh release create|edit|upload`,
`gh repo sync <repo>`,
or a `gh api` merge, release, pull request, branch update or contents write, even behind `env`, `sudo`, `VAR=…`, `bash -c`, `eval`, `$( )`, `cd … &&`
or `;`, is checked against the gate file. So is the PowerShell and Windows
spelling of each: a git alias that expands to one (from `-c alias.…` or your
git config, shell `!` aliases included), `git.exe` or a full path to it, `&`, `iex`/`Invoke-Expression`,
`pwsh`/`powershell -Command` or `-EncodedCommand`, `cmd /c`,
`Start-Process` (with its `-WorkingDirectory`), and a `Set-Location` into
another repo. A heredoc or here-string (`<<<`) fed to a shell is checked as
commands. Any other heredoc is data: a quoted one (`python3 - <<'EOF'`) is
not read, and an unquoted one is read only for `$( )`. The gates it needs:
- commit, a PR branch update, or a push to a non-default branch: **SECURITY**,
  which also passes as `⏳ open — 0 Critical, 0 High, …` (Medium and Low don't
  stop a work commit; the `0 Critical, 0 High` is read from the row's first line)
- opening a PR: **VERSION, BUILD, SECURITY, DOCS**
- a merge, **turning on auto-merge** (a merge that later runs unchecked), a
  release or an edit to one, or **any write that lands on the default branch**
  (`master`, `HEAD:master`, `feat:master`, a bare `git push` while on it, a
  `gh api` contents write with no `branch`):
  those plus **RELEASE**, and the SECURITY row must say `0 open`

**No dev version reaches the default branch.** Any write that lands on it (a
push, a merge, a `gh api` merge) is denied while the working tree declares a
pre-release version: `1.2.0-dev.1`, `-alpha`, `-beta`, `-rc`, `-pre`,
`-preview`, `-SNAPSHOT`, or PEP 440's `1.2.0.dev1`, `a1`, `b1`, `rc1`. It reads
`VERSION`, `package.json`, `pyproject.toml`, `Cargo.toml`,
`app/build.gradle(.kts)` `versionName`, `custom_components/*/manifest.json`, and
the newest version heading in `CHANGELOG.md`. Dev builds stay on their feature
branch (`WORKFLOW_DEVRELEASE.md`); set the final version, then merge. Gates
passing don't lift it.

**A merge with no publishing intent** (`SKILL.md` §2) passes with VERSION,
RELEASE and SHIP marked `➖ no publishing intent`, but only while the file reads
`Track: work commit`, and only on those three rows. While either holds, a tag,
a tag push or a GitHub release is denied: a release runs all six gates.

A gate passes only when **its own row**, the line that starts with its emoji
and name (`🔒 SECURITY`), has ✅ or ➖ **on that line**. `Previous:`,
`Standards:` and evidence lines never count. In a repo that builds a Docker
image, `.exe` or `.apk`, a ✅ BUILD needs a `handoff` note, and a merge needs
`test artifact:` (plus `test creds` for Docker) on the BUILD row. A
work-commit merge can carry `test artifact: n/a — no app code changed`
instead; the release track can't. In a fork,
every `gh` write must name the fork with `--repo` and every push must go to
`origin`. GitHub MCP tools are checked the same way, whatever the server is
named: `create_pull_request`, `merge_pull_request`, `enable_pr_auto_merge`,
`create_release`, `push_files`, `create_or_update_file`, `delete_file` and
`update_pull_request_branch`. Other MCP servers never start the checks.

**A5. No git writes until the mode is chosen.** A `Mode:` row that is
missing, `unchosen`, or anything but `manual`/`semi-autonomous` denies A4's
commands.

**A6. Tags and ref deletions are the user's.** `git tag <name>`, pushing a
tag, `--tags`, `--delete`, `:ref`, `gh pr merge --delete-branch`,
`gh release delete`, and `gh api` ref creation or deletion are denied in both
modes. Listing tags and deleting a local tag pass.

### B. Files Claude edits

**B5. The gate file, settings and the checks go through the user.** An edit
to `.dev-skills-gates.md` that **adds** any of these lines asks the
user, showing the lines:
- `Hook enforcement: declined`
- `Host network: … approved`
- `test artifact: n/a` (a merge that skips the test artifact, Gate 2)
- a new or changed waiver clause: the text from "waive" to the next `;`,
  `·`, `|`, `)` or line end, so `🔕 waived 2026-09-26 by user: …` and
  `(…; waived M1)` both count. The clause is compared, not the whole line:
  editing other evidence on a line that already carries an approved waiver
  passes, while widening it (`waived M1` → `waived M1 M2`) or adding another
  asks. 2.44.1 and earlier compared whole lines, so every update to a
  SECURITY or Standards row that mentioned a waiver asked again.

**Gate rows and the `Mode:` line pass without asking, in both modes.** The
mode is the user's answer to the session-start question, and a gate passing
is shown on the tracker and backed by the commit approval (and, in
semi-autonomous mode, the pre-tag report). A prompt for each would ask the
user to approve bookkeeping they already approved. A gate row that adds a
waiver still asks, because of the waiver.

Other gate-file edits (⏳, evidence, a new session's ⬜ rows) pass. Any edit to
a Claude Code `settings.json`/`settings.local.json` (`/` or Windows `\`
paths) or to the installed checks folder asks. A shell command that looks
like it writes a settings file or the checks asks, including PowerShell's
`Set-Content`/`Out-File`/`Copy-Item` family, their aliases and
`[IO.File]::` writes.

**A shell command on the gate file follows the Edit rule.** It asks only when
it deletes or empties the file (`rm`, `git rm` without `--cached`,
`Remove-Item`, `find -delete`, `: >`, `truncate`), writes it with one of the
lines above in the command (a waiver clause, `Hook enforcement: declined`,
`Host network: … approved`, `test artifact: n/a`), or writes it from text the
command doesn't show (`cp`/`mv` onto it, `git checkout`/`restore` of it, a
redirect from `cat <file>`, `base64 -d`, `git show` or escape codes), since
those can't be checked for waivers. Routine row and
evidence updates, reads, and commands that only name the file (the
session-start probe, `git add`, an ignore entry, `git rm --cached`) pass.
Through 2.45.0 any command naming the file with a write-like token asked,
which prompted on nearly every session. Waivers still belong in an Edit, where
the change is shown line by line.

**B6. The gate file stays out of local commits.** A `git add` that names
`.dev-skills-gates.md`, or force-adds `.`, `-A` or `.claude/` (where a
pre-2.40.0 copy may still sit), is
denied on a local session. Every session rewrites the file, so a committed
copy leaves the tree dirty and blocks `git checkout`. A remote container
(`CLAUDE_CODE_REMOTE` set, as Claude Code on the web does) may stage it,
because its copy dies with the container.

**B7. Handoffs stay local unless the user says otherwise.** Locally the
handoff is committed to the local-only ref `refs/dev-skills/handoff`, which
passes. A `git add` of `.dev-skills-handoff.md` (or an old `.claude/handoffs/`)
onto a branch, or a push of `refs/dev-skills/…`, asks the user on a local
session, so it only leaves the machine when they approve. A remote container
does both freely, because its copy dies with the container.

**B8. Workflow edits meet the workflow checklist's mechanical rules.** A
Write or Edit to `.github/workflows/*.yml` (or `.yaml`) is **denied** when it
adds what `WORKFLOW_REFERENCE.md` rates Critical:
- a `uses:` not pinned to a 40-character commit SHA (a version tag or a
  branch like `@main`). Local actions (`./…`) and `docker://` refs pass, and
  so does `hacs/action`, the one documented exception (Template best
  practices, Security);
- `${{ }}` inside a `run:` script, one-line or block, comment lines included,
  since Actions substitutes it before the shell reads the line. Pass the
  value through `env:`. A `${{ }}` in a YAML comment outside the script
  passes;
- an `actions/checkout` step without `persist-credentials:`. An explicit
  `persist-credentials: true` passes, because a job that pushes needs it and
  said so.

It **asks** when an edit adds what the checklist rates High: no
`permissions:` block anywhere in the file, a job without `timeout-minutes`
(a job that calls a reusable workflow can't set one, so it passes), or a job
whose `run:` calls `./gradlew` before any step in **that job** validates the
wrapper jar (`gradle/actions/wrapper-validation`, or `setup-gradle` without
`validate-wrappers: false`). Each job is its own runner, so validation in
another job doesn't count.

Only problems the edit *adds* count, compared with the file on disk, so
fixing one thing in an old, unhardened workflow isn't blocked by everything
else wrong with it. A new file is checked in full.

### C. Claude's replies

**C1. No loopback or bridge test URLs.** An `http(s)://` URL to `localhost`,
`127.x`, `0.0.0.0`, `[::1]` or `172.17–19.x` in the reply must be replaced with
the LAN URL that `curl` reached.

**C2. Presented git blocks obey the gates.** A code block with a git write is
checked exactly like A4 and A5, because presenting a command is performing it.
A tag push or ref deletion in a presented block also needs every gate
through RELEASE ✅, so it can't be handed over before the merge is confirmed.

**C3. Run blocks are labeled.** A code block labeled `▶️ RUN THIS`, or one
with a `gh` command or a git command that changes something (`add`, `commit`,
`push`, `pull`, `checkout`, `merge`, `tag`, …), needs the lines below. A block
of reads only (`git status`, `log`, `diff`, `fetch`, `ls-remote`) is left
alone unless it is labeled. When a reply is sent back for C3, C5 or C7, the
message includes the block shape to copy.
- `### ▶️ RUN THIS — <what it does>` directly above it
- `# ════════ ▶️ START: <what>` as its first line
- `# ════════ ⏹️ END` as its last line
- `### ⏹️ END` directly below it

With more than one run block, each label says `block N of M`. Blocks inside a
`>` quote count. A block labeled `📄 FOR READING — don't run` is exempt.

**C4. No `cd` in run blocks** (nor `Set-Location`, `sl`, `pushd`, `chdir`).
Blocks assume the terminal is already in the repo. A block fenced as
`powershell` is read as PowerShell, so a git write inside `if ($?) { … }` is
still checked.

**C5. The gate tracker appears above the first run block.**

**C7. "No need to reply" appears under the last run block**, or words that
mean it ("you don't need to reply"). A reply that asks the user something
after the block (a line ending in `?`, or starting "Tell me", "Let me know",
"Reply with") is exempt: it does need an answer.

A reply is sent back for fixing at most twice per user message. The third
time it goes through with a visible warning listing what's still wrong, so a
check that misfires can't trap the session. The count starts over with each
new reply, on every Claude Code version. Each send-back makes Claude write the
reply again, so it costs a full reply's output: the block shape in the
message is there to make the first fix the last one.

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
- **A script that copies text into the gate file from elsewhere**, such as a
  Python heredoc that reads another file and writes it there. B5 reads the
  command, not the result, so a waiver that never appears in the command gets
  through. Edit/Write stays the rule for the gate file.
- **A gate file that is already tracked.** B6 stops it being staged by name,
  but once an earlier commit tracks it, `git add -A` or `git commit -a` picks
  up its changes. Session start untracks it (`SESSION_START.md`).
- **Aliases from config files the checks don't read**: the system config
  (`/etc/gitconfig`) and anything pulled in through `include.path`.
- **Most of the workflow checklist.** B8 reads workflow YAML line by line
  and covers only the rules a line can prove. Release gates, a secret written
  to disk before a dependency install, whether a pin resolves to its tag,
  and anything in a composite action are the workflow audit's job, and a
  workflow written from the shell isn't seen at all.
- **A merge of a PR that isn't checked out.** The dev-version check (A4)
  reads the working tree, so `gh pr merge 12` from a different branch checks
  that branch's version, not the PR's. Merge from the PR's branch, or let
  the release workflow's tag/version check catch it.
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
