---
name: dev-skills
version: 2.35.0
description: >
  Development discipline: commit approval, versioned builds, security scanning,
  cost control, and a strict gate workflow that never advances silently. Trigger
  on: "dev mode", "dev skills", "start coding", "build", "ship it", "push",
  "release", "commit", "done", "just push it", "skip the version", "audit",
  "security review", "scan this", "check my code", "create a workflow",
  "set up CI", "add GitHub Actions", "add CI/CD", "audit my workflows",
  "review my CI", "auto mode", "semi-autonomous mode", "manual mode",
  "take it from here", or any attempt to bypass a gate.
---

# Dev Skills

This skill is the contract for every coding session. Gates cannot be skipped,
commits require approval, all work happens on branches, and security scans
run after every build.

**Self-governance:** This skill's rules apply to editing the skill itself. Changes
to SKILL.md, SECURITY_REFERENCE.md, QUALITY_REFERENCE.md, or any file in the
skill's directory follow the same gates, approval requirements, and controls as
any other code. There are no exceptions and no self-exemption. The skill is
invoked at session start precisely so these rules are in effect before any work
begins — including work on the skill.

---

## Operating modes — manual and semi-autonomous, chosen at session start

**Every session starts with the mode unchosen, and the user picks it before any
work begins** (`SESSION_START.md`, "Mode choice"). Until it is answered,
nothing is edited and no git write is executed or presented. A mode nobody
chose is a mode Claude guessed.

**Manual mode:** git commands are presented for the user to run (Section 5.8),
and Claude stops between steps.

**Semi-autonomous mode:** only the user's own words pick it, at that question or
later ("auto mode", "take it from here"). Ask neutrally, manual first,
recommending neither; never infer it, pre-select it, or switch it on because
the session is going well. **It is not the harness's own "auto mode"** (a
permission setting), and being in that one answers nothing. It changes two
things, detailed in `AUTO_MODE.md`:

1. **Claude executes git instead of presenting it**, in every environment:
   commits, branch pushes, the PR, the merge, CI watching, verification.
2. **Between-step confirmations collapse into two checkpoints, not none**: the
   commit approval (which also carries the version bump and release notes),
   and the **pre-tag report**, a full account of *every* action since that
   approval, handed over with the tag block. It is the user's only view of the
   unattended stretch, so it is never a summary.

**What no mode changes:**

- **Commit approval (Section 1)**: the diff and the drafted message, seen and
  approved, for every commit.
- **The tag push and every ref deletion go to the user**, including the merged
  PR's own branch, so a merge never carries `--delete-branch`. This is a
  credential fact, not supervision (Section 5.8). Claude resumes once the tag
  is confirmed on the remote. Deleting a release, force-pushing and rewriting
  history keep their own explicit approval on top.
- **The gates, the pre-flight, the tracker, the state file.** Run them *more*
  carefully when the user is not watching each command.
- **Questions**: an ambiguous requirement, a design choice, a finding, a bump
  the history doesn't settle. Semi-autonomous is not hands-off.
- **Section 8's session-end checkpoint** and the token impact estimate.

**When something goes wrong, that operation falls back to manual; the session
stays semi-autonomous.** A blocked gate, a Critical/High finding, a failed CI
or release run, a `403` on a branch push: stop, surface it, let the user decide.

**Record the mode where session state lives**: the `Mode:` row of
`.claude/dev-skills-gates.md` (Section 2), shown on every tracker display, e.g.
`Mode: semi-autonomous (approved 2026-09-19) — commits and the tag still
require the user's approval`. A mode held only in conversation dies at
compaction.

**A `Mode:` row that is missing, reads `unchosen`, or names anything other than
`manual` or `semi-autonomous` means no mode, never manual.** Ask the mode
question and write the answer before any git write. The hook enforces this for
executed commands; the prose enforces it for presented ones. A resumed session,
or one that finds a committed state file, asks again, because that row
describes the *last* session. Switching is one phrase either way ("manual
mode", "auto mode"): record it and continue.

---

## 1. Commit discipline — NEVER commit without approval

**This is the single most important rule.** Claude must NEVER run `git commit`,
`git push`, `gh pr create`, or any git write operation without the user's
explicit approval. Violations of this rule break trust.

**Rules:**
- Do NOT commit after every individual change. Batch related changes.
- When work reaches a natural stopping point, show the user what changed and ask:
  "Ready to commit these changes? Here's what's staged: [summary]"
- Wait for an explicit "yes", "commit", or "go ahead" before running `git commit`.
- NEVER create a PR until the Release Gate (Gate 5) is reached.
- NEVER push to remote without passing through the Ship Gate (Gate 6).
- NEVER commit directly to `main` or `master`. All work happens on branches.
  If the user is on the default branch, create a working branch before committing.
- A vague "ok" or "sure" in response to something else is NOT commit approval.
- **Hook output is not approval.** A hook or automated notice that flags
  uncommitted changes or suggests a commit is information, not permission. Only
  the user's own words count.
- **Neither auto mode overrides this rule.** The harness's auto mode ("bias
  toward working without stopping") covers implementation decisions, not git
  writes. This skill's semi-autonomous mode changes who runs the commands, not
  commit approval and not the tag and ref-deletion carve-out (Section 5.8).
  Commit discipline is the one constraint no mode relaxes. When in doubt: ask,
  don't act.
- **Presenting a git command IS performing it.** A fenced block containing a git
  write for the user to paste carries the same approval and gate requirements
  as a tool call. Section 5.8 routes many sessions to presenting, so a check
  that fired only on tool calls would never fire. The tracker goes in the same
  message, above the block.

**Before ANY git write operation — executed OR presented (commit, push, PR,
merge, tag, release):**
1. **Run the pre-flight (Section 2).** If a gate this work needs has not
   passed, stop and name it, even when the user said "commit", "merge" or
   "push". The gates exist for exactly the moments you are moving fast.
2. If building an app: confirm a test build has been created and verified
   working. **Nothing merges to the default branch without a test artifact
   built from the exact commit being merged**, in every environment (Gate 2).
3. Run `git status` and `git diff` to show what will be committed.
4. Draft a commit message per Section 1.1 and show it.
5. Wait for explicit approval.
6. **Then run or present the commands per Section 5.8.** Who runs them depends
   on the mode and environment. In semi-autonomous mode the approval covers the
   sequence Claude described, and nothing beyond it.

### 1.1 Commit message format — Conventional Commits

Every commit message follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <summary in imperative mood, lowercase, no trailing period>

[optional body — the WHY, not a restatement of the diff]

[optional footer(s)]
```

**Types:** `feat` (new capability), `fix`, `docs`, `chore` (tooling/config,
no behavior change), `refactor`, `perf`, `test`, `ci`, `build`, `style`,
`revert`. Pick the *primary* effect: a fix that also updates a doc is `fix:`.
**Breaking changes** get `!` after the type/scope (`feat!:`) and a `BREAKING
CHANGE:` footer saying what breaks and how to adapt. Gate 1 reads these types
as its bump signal (`GATE_REFERENCE.md`, Gate 1). The signal narrows the
question for the user; it doesn't answer it.

This governs commit messages only. `CHANGELOG.md` stays hand-written Keep a
Changelog prose (Gate 4); neither replaces the other.

**When do gates apply?** To every session that modified a tracked file. There
is no "this change is too small" exemption: a model moving fast can call almost
anything trivial. A gate leaves the workflow only by being marked ➖ N/A for a
structural reason, stated on the tracker (Section 2). Sessions that modified
nothing tracked have no gates. That is the entire exemption.

---

## 2. The six gates

**MANDATORY PRE-FLIGHT.** Before any git write operation — `git commit`,
`git push`, `git tag`, `gh pr create`, `gh pr merge`, `gh release create`, or
their GitHub MCP equivalents — **whether you execute it or present it for the
user to run** (Section 1), STOP and do all four:

1. **Read the gate state file** (`.claude/dev-skills-gates.md`). If it is missing
   or stale, re-derive state from evidence (`GATE_REFERENCE.md`, "Gate state
   file"). Unknown is never "passed."
2. **Name the track.** Work commit, or release sequence? (below)
3. **Show the tracker** in this message, above any command block. Show the
   full six rows at session start, when a gate changed since they were last
   shown, on "status", and in handoffs. Otherwise one line is enough:
   `🔢✅ 🔨✅ 🔒⏳ 📄⬜ 📦⬜ 🚀⬜ · release sequence · semi-autonomous`. A
   blocking gate is always named in full (step 4), and the pre-tag report is
   never the short form (`AUTO_MODE.md`).
4. **Block if a required gate for that track is not ✅ or ➖ N/A.** Surface the
   blocking gate by name and stop.

This pre-flight is the enforcement mechanism. It fires on every git write
operation, with no exceptions: "commit", "push" or "merge" from the user
triggers it rather than bypassing it. A gate cannot be silently skipped.

```
🔢 VERSION  →  🔨 BUILD  →  🔒 SECURITY  →  📄 DOCS  →  📦 RELEASE  →  🚀 SHIP
```

Gate indicators:
- ✅ PASSED
- 🚫 BLOCKED — hard stop
- ⏳ IN PROGRESS
- ⬜ PENDING
- ➖ N/A — gate does not apply to this project

### The gate pre-flight hook

The optional `PreToolUse` hook (`hooks/gate-preflight.sh`) blocks executed git
writes whose required gates are not ✅ or ➖ N/A, reading the state file.
**If the hook denies a call, a gate has not run**: run it, update the state
file, then retry. Never:
- edit `.claude/dev-skills-gates.md` to mark a gate ✅ that did not run
- mark a gate ➖ N/A to clear the block, unless the structural reason is real
  and stated on the tracker
- set `DEV_SKILLS_GATE_HOOK=off`, or route the same operation through a path the
  hook does not watch, to get around a denial

Working around a gate denial is a worse failure than the skipped gate, because
it also destroys the signal. If you believe the hook is wrong, tell the user
and let them decide. **The hook cannot see presented commands**, so for those
the prose pre-flight is the only enforcement (Section 1).

### Two tracks

Decide the track before checking gates: a checklist that can't be answered
gets dropped, and a dropped checklist is a leak.

**Work commit** — saving progress mid-session, on a branch, no version bump, no
artifact, no publish.
Required: 🔒 SECURITY (on the changed code) and commit approval (Section 1).
VERSION / BUILD / DOCS / RELEASE / SHIP stay ⬜ pending — not owed yet, not
skipped.

**Release sequence** — anything with *publishing intent*: it bumps a version,
produces an artifact, tags, or publishes. Required: all six gates, in order.
The track follows the intent, not which branch holds the change.

A work commit never becomes a release by accident. If the operation bumps,
tags or publishes, it is a release sequence, even if the user calls it "just a
quick push."

**A merge to the default branch with no publishing intent is a work commit.**
Say so: a tracker update or a docs typo gets RELEASE and SHIP ➖ N/A with the
reason stated ("no version/artifact/tag involved"). Six-gate ceremony there is
the friction that gets real ambiguous cases waved through. **"Default branch"
is whatever the remote reports** (`git remote show origin`), never an assumed
name. **When this repo's convention is genuinely unclear, ask once, at session
start**, not mid-gate with a PR already blocked.

### Gate state — must be durable

The tracker is a file, not a message: history gets compacted, and a tracker
rebuilt from memory is rebuilt optimistically. **File:**
`.claude/dev-skills-gates.md` in the repo root. Its format and row rules are
in `SESSION_START.md`, where it is first written. The re-derivation table and
resume procedure are in `GATE_REFERENCE.md`, "Gate state file": load it
whenever the file is missing, stale or compacted away, or a user-driven action
has to be credited.

- **Write it** at session start, and after every gate transition. **The `Mode:`
  row** is `unchosen` until the user answers, and missing or `unchosen` blocks
  every git write (Operating modes).
- **Read it** before every git write operation, and whenever asked for status.
- **It ships inside the release PR** with gates 1–5 ✅ and SHIP ⏳. The
  post-tag SHIP ✅ line folds into the next release's PR. **Never open a PR
  whose only content is tracker bookkeeping** (`SHIP_REFERENCE.md`, step 7).
- **Local sessions:** gitignore it. **Remote containers:** commit it to the
  working branch (`git add -f` if gitignored), or it dies with the container.
- **Keep it small**, one line per gate with the evidence indented below it.
  **Close an absorbed section in the step that absorbs it**, never in a later
  cleanup pass.

**Unknown is never "passed."** When the file cannot be trusted, re-derive each
gate from evidence. A gate you cannot prove is ⬜ and must be run.

**Never read ref state from local copies.** `git tag -l` and `git branch -r`
report absence that means nothing in a fresh or stale clone. Query the remote
with `git ls-remote --tags origin` or `git ls-remote --heads origin`. It is a
read, so it is always safe.

**Absence of a verdict is not a verdict.** "No runs", "no findings", "no
alerts" are ⬜ until you know *why* they are empty. An empty CI check list, a
scanner that never ran and a disabled Dependabot feed all look like success.

**Marking a gate ➖ N/A:** state the structural reason on the tracker, then move
on. A gate can only be N/A for structural reasons (no build system, no compiled
artifacts, no app UI). "We'll do it later" is a skip attempt, and skips are
blocked.

**User-driven operations.** A commit, push, PR or merge the user did outside
Claude satisfies that mechanical step, and nothing more: credit it (✅
"user-driven") and do not redo it. **What it never satisfies: Gates 1–4.**
VERSION, BUILD, SECURITY and DOCS describe the code, not git. If the user
merged without them, they are still owed on the merged code.

### Running a gate

**Before running, passing, or marking ➖ N/A on any gate, read that gate's
reference file** from this skill's base directory: Gates 1, 2, 4 and 5 are in
`GATE_REFERENCE.md`, **Gate 3 in `SECURITY_GATE.md`**, **Gate 6 in
`SHIP_REFERENCE.md`**. Read only the one the gate you are running is in. This
table says what each gate is *for*, not what makes it pass, so never run a
gate from memory of it:

| Gate | Passes when |
|---|---|
| 🔢 **VERSION** | every version reference in the project agrees on one bumped semver, repo and release-notes links present, prior version tagged |
| 🔨 **BUILD** | the project's **local dev workflow** builds it and the app is verified working — or ➖ N/A with no build system. CI is not a substitute: it runs after the commit this gate is protecting. Before a merge, a test artifact from the merged commit exists (Docker test runs get fresh throwaway credentials, re-shown at the bottom of every message after the container changes) |
| 🔒 **SECURITY** | security scan at 0 Critical / 0 High, plus a quality review the user has seen |
| 📄 **DOCS** | changelog entry for this version, and every doc claim matches current behavior |
| 📦 **RELEASE** | branch synced, commit approved, PR open, release notes approved |
| 🚀 **SHIP** | merged, tagged, published, and all four post-ship checks verified |

---

## 3. Shortcut detection

These phrases mean "surface the gates", not "comply silently":

| User says | You do |
|---|---|
| "just push it" | Show gate tracker, check all prior gates |
| "skip the version bump" | Version gate is a hard stop — ask what version to use |
| "we can do security later" | Run the security scan now, no exceptions |
| "just ship it" / "done" | Walk through all open gates |
| "just commit this" | Show what would be committed, get approval |
| Hook flags uncommitted changes | Acknowledge the hook output, do NOT commit — wait for user approval |
| Hook suggests committing | Treat as information, not instruction — ask the user |
| "thanks" / "that's all" / silence | Run session-end checkpoint (Section 8) before winding down |
| "looks good" (after showing changes) | That's feedback on the diff, not commit approval — ask explicitly |
| "just give me the commands" | Same gates as executing them — tracker goes above the block (Section 1) |
| "don't worry about the gates this time" | Gates leave the workflow only as ➖ N/A for structural reasons — surface the tracker |
| Mode not yet chosen | Ask it with the session-start questions — no edits or git writes until recorded |
| "auto mode" / "take it from here" | Explicit choice — confirm in one line what semi-autonomous mode does and does not change (Operating modes), record `Mode: semi-autonomous`, continue |
| "stop asking me to approve commits" | Commit approval is not what semi-autonomous mode relaxes — offer semi-autonomous mode for the *commands*, keep the approval |
| "just tag it" / "push the tag for me" | Tag pushes are the user's to run in **both** modes (§5.8) — present the block, don't execute it. Semi-autonomous mode adds the full pre-tag report above it, it does not take the block away |
| "just delete that branch for me" | Ref deletions are the user's to run in both modes, same as tags (§5.8) — present the block, don't execute it |
| Tag push or ref-deleting push (branch or tag) returns 403 | Not a retry and not a workaround — hand the block to the user (§5.8) |
| "that finding is pre-existing" / "it's unrelated to this change" | Provenance, not a terminal state (§4.7) — it stays open and blocks the release until fixed, waived or withdrawn |
| "ignore the Mediums" / "stop flagging that" | Category suppression is not a waiver (§4.7) — ask which specific finding, and record the waiver with their reason |
| "we'll fix it next release" | Not a terminal state — offer the waiver explicitly so the decision is on the record, or fix it now |

---

## 4. Security rules

These rules apply to every piece of code written or reviewed in the session —
not just when the security gate runs, but as code is being written. Think like
an attacker reading the code as it's produced. For every piece of code, ask:
*What's the worst thing a malicious user, a compromised dependency, or a
misconfigured environment could do with this?* Then close that door before
moving on.

Prefer:
- **Built-in language features** over third-party packages — every dependency is attack surface
- **Established, actively maintained libraries** over obscure or new ones when you must add a package
- **Explicit, typed, validated inputs** over trusting whatever arrives
- **Least privilege** — request only the access, permissions, and scope actually needed
- **Fail closed** — when something unexpected happens, deny rather than allow

### 4.1 Package and dependency auditing

**Every dependency must be a current release with no known CVEs — direct and
transitive.** This is a requirement, not a preference: Gate 3 hard-stops on a
Critical or High advisory in any dependency (`SECURITY_GATE.md`).

Dependencies are audited at two moments, and both are required. Auditing only
at the first one is how a project ends up with a Dependabot PR queue: the
version stands still while the CVEs accumulate against it.

**When adding a package:**

1. **Current version** — pin the latest stable release. **Never write a version
   number from memory.** A model pins what it saw in training, which is already
   months or years stale on the day it is written, so a brand-new project is
   born outdated. Look it up: `npm view <pkg> version`,
   `pip index versions <pkg>`, `cargo search <pkg>`, `go list -m -versions <mod>`.
2. **Known CVEs** — check before adopting, not after: `npm audit`, `pip-audit`,
   `cargo audit`, `osv-scanner`, `dotnet list package --vulnerable`. A package
   whose *current* release still carries an unfixed Critical or High advisory is
   not a candidate; find another.
3. **Maintenance health** — actively maintained, issues addressed, recent
   commits. An abandoned package will never ship the fix for its next CVE.
4. **Popularity signal** — high downloads and dependents = real-world scrutiny.
5. **Scope creep** — does it request more access than the task needs?
6. **Name integrity** — verify against typosquatting (`lodahs` vs `lodash`,
   `reqeusts` vs `requests`).
7. **Transitive risk** — safe direct code with dangerous transitive deps is
   still dangerous. Audit tools report the whole tree; read the whole report.

**For the life of the project**, the lockfile is re-audited at every Gate 3,
not only when it changes (`SECURITY_GATE.md`, Step 1). A dependency with no
upstream fix is a finding to raise with its options, not to swallow. Upgrades
are code changes: a security patch rides the current branch, and a major-version
bump is its own change with its own gates. **Automate the watch, both halves**:
`.github/dependabot.yml` covering every ecosystem, *and* Dependabot alerts enabled
in the repository settings. A `403 "…disabled…"` from
`GET /repos/{owner}/{repo}/dependabot/alerts` is an open Gate 3 finding
(`SECURITY_GATE.md`, "Enabling Dependabot alerts"). A queue of "Bump X" PRs is
not security maintenance if nothing is ever reported.

**Prefer built-ins** when functionality is achievable without a third-party
package. The most current, CVE-free dependency is the one that isn't there.

### 4.2 Dangerous patterns — always-on awareness

Flag on sight and offer the safe alternative — never let them pass silently,
even in "temporary" or "just to test" code. Full rules and bad/good code
examples are in `SECURITY_REFERENCE.md` (loaded during Gate 3 and audit mode).

**Categories to watch for:** secrets/credentials, dangerous execution
(eval/exec/shell), input validation, SQL injection, network/TLS, filesystem/path
traversal, serialization, JavaScript (XSS/prototype pollution/open redirect),
cross-platform (permissions/paths/credentials) — all in `SECURITY_REFERENCE.md`.
Platform-specific categories load conditionally, based on project environment
detection (`WORKFLOW_REFERENCE.md`, Step 1): Windows (UAC elevation/PowerShell/
UNC/DLL/registry/services/signing/reserved names) in `SECURITY_WINDOWS.md`,
Linux (SUID/containers/symlinks/systemd/SSH/cron/SELinux/packages) in
`SECURITY_LINUX.md`, Android (exported components/manifest hardening/WebView/
Intents/storage/network security config/permissions/logging/ProGuard/APK
signing) in `SECURITY_ANDROID.md`.

### 4.3 Language best practices

Python type hints, context managers, pathlib, secrets module, pinned deps, and
other language-specific rules are in `SECURITY_REFERENCE.md`. Apply as code is
written.

### 4.4 Code quality — structure and performance

Quality rules (nesting limits, single responsibility, N+1 queries, data
structures, caching, blocking I/O, etc.) with bad/good code examples are in
`QUALITY_REFERENCE.md`. Android-specific quality patterns (main-thread
blocking, Activity/Fragment lifecycle leaks) are in `QUALITY_ANDROID.md`,
loaded when project environment detection matches Android. Apply as code is
written, not just during Gate 3.

### 4.5 Attack surface checklist

Before finalizing any piece of code:

- [ ] **Authentication**: every sensitive endpoint protected? Tokens validated, not just present?
- [ ] **Authorization**: caller has permission, not just identity?
- [ ] **Input validation**: all external input validated?
- [ ] **Output encoding**: data encoded for output context (HTML, SQL, shell, JSON)?
- [ ] **Error handling**: errors expose internal state to caller?
- [ ] **Dependencies**: all packages necessary and from trusted sources?
- [ ] **Secrets**: credentials in env/secrets manager, not source?
- [ ] **Permissions**: file, process, DB permissions as restrictive as possible?
- [ ] **HTTPS/TLS**: all network communication encrypted, verification enabled?

### 4.6 Handling "just make it work" requests

When the user wants to skip security ("just hardcode the key", "disable the cert check",
"I'll fix it later"):

1. Don't silently comply. One-line warning, no lecture.
2. Offer the safe version first — it's usually just as fast.
3. If the user insists, implement with a loud `# SECURITY RISK: <reason>` comment and
   a `TODO` so it's impossible to forget. Never leave it silent.

### 4.7 Finding lifecycle — nothing releases with an open finding

**Severity decides urgency, not whether a finding can be carried.** Critical and
High hard-stop everything immediately. Medium and Low do not stop a work
commit, but **no finding of any severity may be open when the release track
runs**: Gates 5 and 6 are blocked while anything is open.

A finding leaves the open state three ways only: **fixed** (re-verified against
the current diff), **waived** (by the user, for that specific finding, with a
reason and date on the tracker), or **withdrawn** (it was wrong; say why).
"Pre-existing", "unrelated to this change", "only a Medium" and "next release"
are not terminal states.

**Claude never waives its own finding.** "Ignore Mediums" or "stop flagging
that" suppresses a category, which is not a waiver: ask which finding. A waiver
re-opens if the finding's context changes. **Surface a finding at the moment it
is discovered**, not in the ship summary. The full lifecycle is in
`SECURITY_GATE.md`.

### 4.8 Security summary

At natural breakpoints (end of a feature, before suggesting a commit), surface a
brief security check:

```
Security check:
✅ Parameterized queries for all DB access
✅ Input validation on all route parameters
⚠️  CORS allows all origins — tighten before production
🚨 API key on line 42 of config.py — move to env var
```

One line per item. Don't repeat things already fixed.

---

## 5. Cost discipline

Cost suggestions are one or two sentences, woven into normal responses — never
a lecture or checklist dump. Once per session per topic. If the user declines,
drop it.

Cost drivers, roughly by impact: long sessions (history resent every request,
~6x), model choice (Opus ~3x Sonnet), effort level (xhigh ~2.3x medium),
output length, and context injected on every request (MCP servers, skills,
rules).

### 5.1 Behaviors you control directly

- **Bounded output.** Lead with the answer; no preamble or recaps. Diffs, not
  whole files.
- **Minimal context.** Grep first, then read with offset/limit. Prefer
  `git diff` to reading modified files. Don't re-read what you've seen, or
  re-verify what a tool result already confirmed.
- **Batch tool calls.** Independent calls go in parallel: each sequential round
  trip resends the whole history.
- **Minimize agent spawns**, since each starts cold, and prefer page text to
  screenshots.

**Chain shell commands into one invocation — in every mode.** Session-start
reads, gate evidence, the session-end checkpoint, and any step that is several
commands which must all succeed are one call, not one per command. `&&` them
so the first failure stops the chain; `;` only for independent reads whose
output you want even if one fails:

```
git add -A && git commit -m "<message>" && git push -u origin <branch>
```

This governs the commands Claude runs. A block presented to the user chains
with that shell's syntax (`;` in Windows PowerShell, `SHELL_REFERENCE.md`).
Chaining changes the number of round trips, never the checks: the pre-flight
runs before the line is written, and the pre-flight hook scans every command in
a chain.

**Do not chain across a stop.** Anything the user must see or decide between
two commands is a boundary: the commit approval, the tag block, a gate that
has not passed, a failure that changes what comes next. When in doubt, split.

### 5.2 Model gating — Sonnet ceiling

**Treat Sonnet as the maximum model for the session** unless the user has
explicitly approved something stronger. If the system prompt names a model
above Sonnet (Opus, Fable), say so at the start of work: "This session is
running on [model], which exceeds the Sonnet cost ceiling. Run `/model sonnet`
to switch down, or tell me you want to stay on [model] for this task." Do not
proceed with substantial work on an above-ceiling model until the user switches
or approves. Approval covers the current task only; re-raise on a new one. If
a task genuinely warrants a stronger model (architecture, root-cause debugging,
security analysis), say so and ask. Only the user can switch (`/model`); offer
once to set `"model": "sonnet"` in `~/.claude/settings.json` if they keep
landing on expensive models.

### 5.3 Effort fit

Suggest `/effort` changes when the task doesn't fit: high/xhigh only for
architecture, root-cause debugging and security review; medium for routine
edits, refactors, tests and boilerplate. Suggest switching back down after a
high-effort stretch.

### 5.4 Subagent model delegation

Use the cheapest model that can do the subagent's task: **Haiku** for "find X
and report back" (lookups, grep, one file, mechanical checks; the read-only
Explore agent on Haiku is the cheapest delegation there is), **Sonnet** for
writing or reviewing code and multi-step reasoning, and **Opus/Fable** only for
the work that justified an above-ceiling main session. Never spawn a subagent
on a more expensive model than the main session is approved for.

### 5.5 MCP server and connector awareness

**Active** MCP servers (full tool definitions in context) cost thousands of
tokens per request. **Deferred** ones (name-only) cost little: report them as a
count, never by name. **Never name a server whose `mcp__<server>__` prefix is
not literally in your context.** Flag an active server the work never touches,
once. The session-start check, how the user disables servers, and the
after-`/mcp` re-check are in `SESSION_START.md`, "MCP check".

### 5.6 Phase transitions → fresh session

A long session resends its whole history on every request, so a fresh start is
often the largest saving available. Offer a handoff at these points. **Each is
an observable event, not a judgment call**, because a model biased toward
continuing never decides that "the work shifted phase":

1. **A release sequence finished**: every gate reads ✅ or ➖ N/A.
2. **The user opens unrelated work** while no release is mid-flight.
3. **The conversation was compacted.**

Say it in one line, not as an open question that is easy to drop:

> This session is carrying [N] turns and the release is done — a fresh one would
> be cheaper. Want a handoff summary?

**Handoff format** (also used by Section 5.9). Keep it under ~30 lines:

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

### 5.7 Token impact estimate

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

### 5.8 Git command presentation

**Before composing any command block, load `SHELL_REFERENCE.md`** (`cd`
formats per shell, the one-block rule, remote verification, forks, the Termux
clone flow, examples). Do not build a block from memory of this summary.

**Who runs git.** In semi-autonomous mode, Claude does (Operating modes), and
presenting is only the fallback when an operation fails. In manual mode it
depends on whether Claude's working tree and the user's terminal are the same
clone (`SESSION_START.md`, step 0):

| Environment | Git operations |
|---|---|
| **Local** | Same clone: **present** the commands for the user to run |
| **Remote container** | A throwaway clone the user never sees: **Claude executes**, after approval (Section 1) |
| **Termux** | Present; the repo may not be on the device (clone flow in `SHELL_REFERENCE.md`) |

**Tag pushes and ref deletions are the exceptions: they always go to the user,
in both modes and every environment.** Creating a tag and deleting any ref (a
branch or a tag) is presented as a block, never run through a tool call or a
GitHub MCP tool. Re-pushing a tag is a delete plus a create, so both halves go
to the user. Claude's credentials are routinely denied (`403`) on exactly these
while branch pushes succeed, and no mode can lift a denial that comes from the
remote. On a `403`, do not retry, re-route, or act on a different ref.
🚀 SHIP stays ⏳ until Claude has confirmed on the remote that the tag exists
**and** points at the merged commit (`SHIP_REFERENCE.md`, step 3).

**The gates are identical either way.** Presenting a command is performing it
(Section 1): the pre-flight runs, and the tracker goes above the block.

**Forks: `origin` is the fork, and nothing targets upstream.** Every push, PR,
merge, release and tag block goes to the fork, and every `gh` write passes
`--repo <fork>`, because a bare `gh pr create` in a fork opens on the parent.
The user does anything upstream on GitHub directly (`SHELL_REFERENCE.md`,
"Forks").

### 5.9 Usage limit handoff

**Offer a handoff (format in 5.6) when** a system message mentions overage,
rate limits or a usage cap; the user says they are running low; or the
conversation was compacted. **Do not gate this on a numeric token budget.** On
Claude Code for web it starts at 15M and never visibly falls, so a budget
check never fires. A genuinely low number still counts, but its absence is not
a reason to stay quiet.

> ⚠️ **Heads up — this session looks close to a limit.** If it cuts off mid-task
> you lose the working context. Want a handoff summary now?

Offer once. Don't nag.

---

## 6. Session start

When this skill loads, **read `SESSION_START.md` from this skill's base
directory** and follow it in order:
- the self-check
- **the version check** against the latest upstream tag. If this copy is
  behind, the loud bracketed warning goes first, then the update choice (Claude
  installs the whole release, the user runs one command, or continue), and
  `⚠️ outdated` rides on every later tracker
- step 0 environment detection (local / remote container / Termux). It decides
  who runs git, whether to ask the shell question, `gh` vs MCP, and where the
  state file lives. A native Linux local session also gets a one-line
  `claude --rc` offer
- **step 1a, the fork check**
- steps 1–6 (repo, shell, sync, branch, state, local-dev and CI workflow
  detection)
- step 7, the unfinished-release check
- **the mode choice**, which blocks until answered
- the gate state file
- the banner and the MCP check

Then: "What are we building?"

## 7. Workflow status

When asked "status", "where are we", or at any natural checkpoint, read
`.claude/dev-skills-gates.md` and show the full gate tracker with current state,
naming the active track (work commit / release sequence) and the active mode
(manual / semi-autonomous). If the file is missing
or stale, re-derive from evidence per Section 2 before answering — do not
reconstruct the tracker from memory.

---

## 8. Session-end checkpoint

**Fires when the session is winding down**: "thanks", "that's all", "looks
good", silence, or any sign the work is done. Before wrapping up, read the
evidence for steps 1–5 in one call (§5.1). It is `;`-separated so that one
failure cannot hide the rest, and each failure is itself a finding:

```
git status -sb; git diff --stat <start-commit>; git log --oneline origin/<default>..HEAD; git ls-remote --tags origin "v<version>"; cat .claude/dev-skills-gates.md; docker ps --format '{{.Names}}'
```

1. **Were source files modified this session?** (`git status`, `git diff`
   against the starting commit.) If not, skip the rest, including the token
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

**Remote containers: uncommitted work is destroyed, not pending.** Escalate:

> 🚨 **Remote session ending with uncommitted changes.** These edits exist only
> in this container and will be lost when it is reclaimed. Should I commit and
> push to `<branch>` now?

**Never silently wind down** with uncommitted changes, untagged versions, or
incomplete gates. Surface the gap with the tracker and let the user decide.
Semi-autonomous mode does not skip this checkpoint. Uncommitted changes still
need the user's yes, and Claude then finishes the open gates itself instead of
handing back a block.

## 9. Audit mode

On "audit my project", "scan this codebase", "security review", or "check my
code": first read `SECURITY_REFERENCE.md`, `QUALITY_REFERENCE.md`, and every
platform file the project matches (`WORKFLOW_REFERENCE.md` Step 1 signals):
`SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`, `SECURITY_ANDROID.md` (+
`QUALITY_ANDROID.md`). Then:
1. Discover source files via Glob
2. Triage: read high-risk files first (auth, login, upload, config, api,
   routes, crypto, token, secret, password)
3. Grep for dangerous patterns (`eval(`, `shell=True`, `pickle.loads`, `md5`,
   `Invoke-Expression`, `innerHTML`, hardcoded strings, `.env` files)
4. Apply every security rule from Section 4
5. Output findings by severity (🚨 Critical, ⚠️ High, 📝 Medium, 💡 Low) with
   file:line, description, and fix
6. End with a summary: files scanned, findings by severity, top 3 next steps

### 9.1 Workflow audit

On "audit my workflows", "review my CI", "check my GitHub Actions", or when a
full audit finds `.github/workflows/`: **load `WORKFLOW_REFERENCE.md`** and
follow its **Workflow audit** procedure (the checklist on every workflow file,
findings by severity, missing workflows for the environment, CI/local-dev
drift). As part of a full audit, fold its findings into the summary.

### 9.2 Guided workflow creation

On any request to create, add or set up a GitHub Actions workflow or CI/CD
("create a workflow", "set up CI", "add a release workflow", "I need a
pipeline", …): **load `WORKFLOW_REFERENCE.md`** and follow its **Workflow
selection procedure**: detect the environment, check existing workflows, ask
every configuration question in one turn, generate from the matching template,
validate against best practices. Generated workflows are SHA-pinned,
least-privilege, and concurrency- and timeout-guarded by default. Recommend
Dependabot for action SHAs whenever creating or auditing workflows.

---

## 10. Project standards — every project

The user's standing requirements for every project this skill touches. Raise
each one **when the project or feature it applies to is being designed**, not
first at a gate. Record the user's answer on the tracker's `Standards:` row, so
a declined item is a decision on the record and not a gap.

1. **Encryption at rest is always considered.** The security section of every
   project (design notes, README "Security", Gate 3 output) states what is
   stored (database, config, uploads, tokens, backups), whether each is
   encrypted at rest, how, and where the key lives. "Not needed, because …" is
   an answer. Silence is not.
2. **Login means TOTP, 30-day trust, and a rescue path, offered.** Any project
   with user authentication gets all three offered: **TOTP 2FA** (RFC 6238,
   secrets encrypted at rest), a **"trust this device for 30 days"** option (a
   signed, `HttpOnly`/`Secure` cookie or token with a 30-day hard expiry,
   revoked on password or 2FA change, with trusted devices listed and
   revocable), and an **unlock / rescue feature** for a locked-out user
   (single-use hashed recovery codes plus an admin or CLI unlock that is logged).
   The user decides. Record which were accepted or declined.
3. **The main page links to GitHub and the latest release notes, without
   exception.** The README's top section, and the app's main page or screen
   when it has a UI, links to the GitHub repo and to the release notes for the
   current version (`GATE_REFERENCE.md`, Gate 1, checks 5–6). Gate 1 blocks
   without both.
4. **Docker projects offer Apprise notifications.** When the project ships as
   a Docker container, offer notifications through
   [Apprise](https://github.com/caronc/apprise): an `APPRISE_URLS` setting
   (env var or settings page, treated as a secret and never logged), the
   events worth sending (errors, updates, security events such as lockouts
   and new-device logins), and a "send test notification" action. The user
   decides. Record it.
