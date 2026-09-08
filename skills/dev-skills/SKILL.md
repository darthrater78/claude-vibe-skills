---
name: dev-skills
version: 2.15.0
description: >
  Development discipline: commit approval, versioned builds, security scanning,
  cost control, and a strict gate workflow that never advances silently. Trigger
  on: "dev mode", "dev skills", "start coding", "build", "ship it", "push",
  "release", "commit", "done", "just push it", "skip the version", "audit",
  "security review", "scan this", "check my code", or any attempt to bypass a
  gate.
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
- **Hook output is not approval.** A hook that flags uncommitted changes, suggests
  a commit, or reports working tree state is information, not permission. Only the
  user's own words ("yes", "commit", "go ahead") count as approval. A stop hook,
  pre-commit hook, or any automated notification is NEVER a substitute for the
  user explicitly telling you to proceed.
- **Auto mode does not override this rule.** The system prompt's auto mode says
  "bias toward working without stopping." That applies to implementation decisions,
  not to git write operations. Commit discipline is a hard constraint that auto
  mode cannot relax. When in doubt: ask, don't act.
- **Presenting a git command IS performing it.** Whether you run `git commit` via
  a tool call or print it in a fenced block for the user to paste, the approval
  and gate requirements are identical. A code block containing a git write command
  *is* a git write operation. This matters because Section 5.7 routes many
  sessions toward presenting commands rather than executing them — if the gate
  check only fired on tool calls, it would never fire at all. It fires on the
  block. The gate tracker goes in the same message, above the block.

**Before ANY git write operation — executed OR presented (commit, push, PR,
merge, tag, release):**
1. **Check the gate tracker.** If any gate applies to this session's work and
   has not passed, stop and surface the blocking gate. This is not optional —
   even if the user says "commit", "merge", or "push", check the gates FIRST.
   The gates exist precisely for the moments when you're moving fast and want
   to skip them.
2. If building an app: confirm a test build has been created and verified working.
3. Run `git status` and `git diff` to show what will be committed.
4. Draft a commit message and show it.
5. Wait for explicit approval.
6. **Present commands per Section 5.7.** Always present the git commands formatted
   for the user's shell environment so they can run them manually. Only execute
   directly via tool calls if the user explicitly asks Claude to run them.

**When do gates apply?** By default, to every session that modified a tracked
file. There is no "this change is too small" exemption — that judgment call is
the single most common way gates get skipped, because a model moving fast can
classify almost anything as trivial. A gate leaves the workflow one way only: by
being explicitly marked ➖ N/A for a structural reason (Section 2), stated out
loud on the tracker.

Sessions that modified nothing tracked — questions, code reading, exploration —
have no gates, because they have no changes. That is the entire exemption.

---

## 2. The six gates

**MANDATORY PRE-FLIGHT.** Before any git write operation — `git commit`,
`git push`, `git tag`, `gh pr create`, `gh pr merge`, `gh release create`, or
their GitHub MCP equivalents — **whether you execute it or present it for the
user to run** (Section 1), STOP and do all four:

1. **Read the gate state file** (`.claude/dev-skills-gates.md`). If it is missing
   or stale, re-derive state from evidence using the table below. Unknown is
   never "passed."
2. **Name the track.** Work commit, or release sequence? (below)
3. **Show the tracker** in this message, above any command block.
4. **Block if a required gate for that track is not ✅ or ➖ N/A.** Surface the
   blocking gate by name and stop.

This pre-flight is the enforcement mechanism. It fires on every git write
operation, every time, with no exceptions. The user saying "commit", "push", or
"merge" does not bypass it — it triggers it.

A gate cannot be silently skipped. If the user tries to jump ahead, show the
gate tracker and surface the blocking gate.

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

The repo ships an optional `PreToolUse` hook (`hooks/gate-preflight.sh`) that
blocks git write operations whose required gates are not ✅ or ➖ N/A, reading
`.claude/dev-skills-gates.md` for state. Where it is installed, the pre-flight
above stops being advisory for anything Claude executes itself.

**If the hook denies a call, it is telling you a gate has not run.** The correct
response is to run the blocking gate and update the state file, then retry.
Never:
- edit `.claude/dev-skills-gates.md` to mark a gate ✅ that did not run
- mark a gate ➖ N/A to clear the block, unless the structural reason is real
  and stated on the tracker
- set `DEV_SKILLS_GATE_HOOK=off`, or route the same operation through a path the
  hook does not watch, to get around a denial

Working around a gate denial is a worse failure than the skipped gate, because
it also destroys the signal. If you believe the hook is wrong, say so to the
user and let them decide.

**The hook does not cover presented commands** — nothing intercepts the user's
own terminal. On local sessions, where presenting is the default (Section 5.7),
the prose pre-flight is the only enforcement there is. That is exactly why
presenting a command counts as performing it (Section 1).

### Two tracks

Not every git operation is a release. Decide which track the operation is on
before checking gates: a checklist that can't be answered tends to get dropped
entirely, and a dropped checklist is a leak.

**Work commit** — saving progress mid-session, on a branch, no version bump, no
artifact, no publish.
Required: 🔒 SECURITY (on the changed code) and commit approval (Section 1).
VERSION / BUILD / DOCS / RELEASE / SHIP stay ⬜ pending — not owed yet, not
skipped.

**Release sequence** — anything that bumps a version, produces an artifact,
merges to the default branch, tags, or publishes.
Required: all six gates, in order.

A work commit never becomes a release by accident. If the operation tags, merges
to the default branch, or publishes, it is a release sequence — regardless of
the user calling it "just a quick push."

### Gate state — must be durable

The tracker is not a message you printed once; it is a file. Conversation history
gets compacted away, and a tracker rebuilt from memory is rebuilt optimistically
("security ran earlier, I think"). Write the state down.

**File:** `.claude/dev-skills-gates.md` in the repo root.

- **Write it** at session start, and after every gate transition.
- **Read it** before every git write operation, and whenever asked for status.
- **Local sessions:** add it to `.gitignore` — it is session scratch.
- **Remote containers:** commit it to the working branch instead. The container
  is reclaimed when the session ends, and an uncommitted state file dies with it
  (`GATE_REFERENCE.md`, session start, step 0). If the repo already gitignores
  the file — this one does, for local users — stage it explicitly with
  `git add -f .claude/dev-skills-gates.md`, or accept that state will not survive
  the session and re-derive from evidence next time. Do not silently let it
  vanish.

Format:

```
# Dev Skills gate state
Track: release sequence
Version: 2.12.0
Updated: 2026-09-07

🔢 VERSION    ✅ all refs at 2.12.0
🔨 BUILD      ➖ N/A — skill repo, no build system
🔒 SECURITY   ✅ 0 Critical, 0 High
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜
```

**Never read tag state with `git tag -l`.** It lists *local* tags, and a fresh
clone — every remote container, and any `--no-tags` or shallow checkout — has
none, so it returns empty on repos with a hundred tags. Every tag check in this
skill uses the remote:

```
git ls-remote --tags origin              # all tags
git ls-remote --tags origin v1.2.3       # one tag
```

This matters more than it looks. A check that reports *every* prior version as
untagged is a check nobody reads, and a real missing tag hides in that noise.
Reading refs is not a write, so this is safe to run yourself even where tag
*pushes* are denied (Section 5.7).

**Re-derivation — when the state file is missing, stale, or the session was
compacted.** Do not guess, and do not treat a gate as passed because it feels
like it did. Rebuild from evidence:

| Gate | Evidence that it passed |
|---|---|
| 🔢 VERSION | every version-carrying file reads the same bumped semver, and `git ls-remote --tags origin` shows the previous version tagged |
| 🔨 BUILD | a build artifact exists newer than the last source edit — or the project has no build system (➖ N/A) |
| 🔒 SECURITY | a scan was run against the **current** diff; a scan of earlier code does not cover edits made after it |
| 📄 DOCS | the changelog has an entry for this version, and the README matches current behavior |
| 📦 RELEASE | a PR exists for this branch (`gh pr list`, or MCP `list_pull_requests`) |
| 🚀 SHIP | tag on remote, release exists, PR merged, expected assets attached |

Any gate you cannot prove from evidence is ⬜ pending and must be run.
"It probably ran" is ⬜.

**Marking a gate N/A:** Some gates don't apply to every project (e.g. no build
step for a docs-only or config repo). When a gate genuinely doesn't apply:
1. State why it doesn't apply (e.g. "no build step — this is a skill/config repo")
2. Mark it ➖ N/A on the tracker
3. Move to the next gate

A gate can only be N/A for structural reasons (the project has no build system,
no compiled artifacts, no app UI). "We'll do it later" or "it's not important
this time" is not N/A — that's a skip attempt, and skips are blocked.

**User-driven operations.** The gates track the state of the work, not who typed
the command.

**What a user-driven git action satisfies: the mechanical step itself, and
nothing more.** If the user committed, pushed, opened a PR, or merged outside of
Claude — in their terminal, the GitHub UI, or another tool — do not re-do that
action. Credit it on the tracker (✅ "user-driven").

**What it never satisfies: Gates 1–4.** VERSION, BUILD, SECURITY, and DOCS are
statements about the state of the *code*, not about git. A commit existing is not
evidence that anything was scanned, built, or documented. If the user merged to
the default branch without security (Gate 3) or docs (Gate 4), those gates are
still owed — run them on the merged code and surface what you find.

When resuming work or checking gate status, detect what's already done:
1. Run `git log`, `git branch -r`, `git ls-remote --tags origin`, and `gh pr list` / `gh pr view`
   — or the GitHub MCP equivalents when `gh` is unavailable (`GATE_REFERENCE.md`, session start, step 0)
2. Credit completed steps on the tracker (✅ with "user-driven" or "already done")
3. Re-derive Gates 1–4 from evidence (table above) — never from the presence of
   a commit
4. Continue from the first gate that is not ✅ or ➖ N/A

### Running a gate

**Before running, passing, or marking ➖ N/A on any gate, read
`GATE_REFERENCE.md`** from this skill's base directory (shown when the skill
loaded, e.g. "Base directory for this skill: ..."). It holds each gate's
checks, pass criteria, blocked-output format, and the CI-versus-manual paths.
Do not run a gate from memory of this summary — the summary says what each gate
is *for*, not what makes it pass.

| Gate | Passes when |
|---|---|
| 🔢 **VERSION** | every version reference in the project agrees on one bumped semver, repo and release-notes links present, prior version tagged |
| 🔨 **BUILD** | the project's **local dev workflow** builds it and the app is verified working — or ➖ N/A with no build system. CI is not a substitute: it runs after the commit this gate is protecting |
| 🔒 **SECURITY** | security scan at 0 Critical / 0 High, plus a quality review the user has seen |
| 📄 **DOCS** | changelog entry for this version, and every doc claim matches current behavior |
| 📦 **RELEASE** | branch synced, commit approved, PR open, release notes approved |
| 🚀 **SHIP** | merged, tagged, published, and all four post-ship checks verified |

Gate 3 additionally loads `SECURITY_REFERENCE.md` and `QUALITY_REFERENCE.md`;
Gate 6's ship path depends on whether a CI release workflow exists. Both are
detailed in `GATE_REFERENCE.md`.

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
| "just tag it" / "push the tag for me" | Tag pushes are always the user's to run (§5.7) — present the block, don't execute it |
| Tag push returns 403 | Not a retry and not a workaround — hand the block to the user (§5.7) |

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

Before suggesting or accepting any new package, check:

1. **Maintenance health**: actively maintained, issues addressed, recent commits
2. **Popularity signal**: high downloads and dependents = real-world scrutiny
3. **Scope creep**: does it request more access than the task needs?
4. **Name integrity**: verify against typosquatting (`lodahs` vs `lodash`, `reqeusts` vs `requests`)
5. **Known CVEs**: run `npm audit`, `pip audit`, `cargo audit`, or equivalent
6. **Transitive risk**: safe direct code with dangerous transitive deps is still dangerous

**Prefer built-ins** when functionality is achievable without a third-party package.

### 4.2 Dangerous patterns — always-on awareness

Flag on sight and offer the safe alternative — never let them pass silently,
even in "temporary" or "just to test" code. Full rules and bad/good code
examples are in `SECURITY_REFERENCE.md` (loaded during Gate 3 and audit mode).

**Categories to watch for:** secrets/credentials, dangerous execution
(eval/exec/shell), input validation, SQL injection, network/TLS, filesystem/path
traversal, serialization, JavaScript (XSS/prototype pollution/open redirect),
Windows (PowerShell/UNC/DLL/registry/services/signing/reserved names), Linux
(SUID/containers/symlinks/systemd/SSH/cron/SELinux/packages), Android
(exported components/manifest hardening/WebView/Intents/storage/network security
config/permissions/logging/ProGuard/APK signing), cross-platform (permissions/paths/credentials).

### 4.3 Language best practices

Python type hints, context managers, pathlib, secrets module, pinned deps, and
other language-specific rules are in `SECURITY_REFERENCE.md`. Apply as code is
written.

### 4.4 Code quality — structure and performance

Quality rules (nesting limits, single responsibility, N+1 queries, data
structures, caching, blocking I/O, etc.) with bad/good code examples are in
`QUALITY_REFERENCE.md`. Apply as code is written, not just during Gate 3.

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

### 4.7 Security summary

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

The big cost drivers, in rough order of impact:
1. **Long sessions** — the whole history is resent every request (~6x cost difference)
2. **Model choice** — Opus everywhere is ~3x the cost of Sonnet
3. **Effort level** — xhigh vs medium is ~2.3x per request
4. **Output length** — doubling output is ~2.2x per request
5. **Context size** — every MCP server, skill, and rule is injected into every request

### 5.1 Behaviors you control directly

**Bounded output.** Lead with the answer. No preamble, no recaps. Show diffs, not
whole files. If three sentences suffice, use three sentences.

**Minimal context.** Read only what the task needs. Use offset/limit and targeted
grep. Don't re-read files already seen.

**No redundant verification.** Don't re-run tests or re-read files when the tool
result already confirmed success.

**Batch tool calls.** Independent calls go in parallel — each sequential round trip
resends the full conversation history. Five parallel calls cost the same as one.

**Grep before reading.** Find the right lines first, then read with offset/limit.
Never read a 2000-line file to check one function.

**Git diff over full reads.** When reviewing changes, `git diff` is far cheaper
than reading every modified file end to end.

**Minimize agent spawns.** Each subagent starts cold with full context re-injection.
Only spawn when the work justifies it — not for a single grep or file read.

**Text over screenshots.** `read_page` / `get_page_text` costs a fraction of a
screenshot when you only need to verify text content or structure.

### 5.2 Model gating — Sonnet ceiling

Treat Sonnet as the maximum model for the session unless the user has explicitly
approved something stronger. Concretely:

- At the start of work, check which model is powering the session (stated in the
  system prompt). If it's above Sonnet — Opus or Fable — tell the user immediately:
  "This session is running on [model], which exceeds the Sonnet cost ceiling.
  Run `/model sonnet` to switch down, or tell me you want to stay on [model]
  for this task."
- Do not proceed with substantial work on an above-ceiling model until the user
  either switches down or explicitly approves staying. A simple "yes, stay on Opus"
  counts — but it applies to the current task only. Re-raise if work moves to a
  new task.
- If a task genuinely warrants a stronger model (architecture, nasty root-cause
  debugging, security analysis), say so and ask for approval rather than silently
  accepting the expensive model.
- You cannot switch the model yourself — only the user can, via `/model`. What you
  *can* do is set `"model": "sonnet"` in `~/.claude/settings.json` so every new
  session starts on Sonnet. Offer this once if the user keeps landing on expensive
  models unintentionally.

### 5.3 Effort fit

Recommend `/effort` changes when the task doesn't match the current level:
- **high/xhigh**: only for architecture decisions, root-cause debugging, security review
- **medium**: routine edits, mechanical refactors, running tests, writing boilerplate
- Remind the user to switch back down after a high-effort stretch

### 5.4 MCP server and connector awareness

MCP servers add per-request overhead. Check how their tools are loaded before
reporting — don't conflate the two states:

- **Active tools** (full definitions in context): expensive — often thousands to
  tens of thousands of tokens per server, on every request.
- **Deferred tools** (name-only, schemas loaded on demand): low overhead — a few
  hundred tokens per turn. Report only the count for deferred servers ("N connectors
  deferred — low overhead, no action needed"). Do not list their names.

**CRITICAL: Never name a connector you cannot see.** Only list servers whose
`mcp__<server>__` tool prefixes are literally present in your context. Do not
infer or guess based on the user's role or company.

**Only flag servers with full active tool definitions for removal** — deferred
servers are already in the cheapest state. If you notice active servers the current
work never touches, mention it once and offer both paths:

**How the user can disable them:**
- CLI-added: `claude mcp list` to see, `claude mcp remove <name>` to remove,
  `/mcp` inside a session to toggle
- Project-level in `.mcp.json`: add to `"disabledMcpjsonServers"` in
  `.claude/settings.json`
- Desktop app connectors: toggle in app UI (Settings → Connectors/Extensions) —
  Claude cannot change these
- CLI clean start: `claude --strict-mcp-config --mcp-config '{"mcpServers":{}}'`
  launches with zero MCP servers — suggest a shell alias for users who want a
  cheap default

**After `/mcp` changes:** Re-check what's connected by examining your own context
(tool prefixes). Do NOT use `claude mcp list` — it returns the full catalog
including unconnected servers. Give a short before/after:

```
Connections now: Home Assistant, Slack (was: + Jira, Gmail, Calendar, Drive)
Estimated overhead: ~12k/turn, down from ~40k/turn
```

### 5.5 Phase transitions → fresh session

When work shifts phase (exploration → implementation, implementation → testing,
task complete → new task), offer a handoff summary:

> "Good point to start a fresh session — this one's carrying [N] messages of
> exploration history. Want a handoff summary to paste into a new session?"

If yes, produce:

```
## Handoff: [task name]
**Goal:** one sentence
**Current state:** what's done, what's verified
**Key files:** path:line — why it matters
**Decisions made:** constraints the next session must respect
**Next step:** the single concrete next action
```

Keep it under ~30 lines. The point is to replace a long history with a cheap
restart.

### 5.6 End-of-task token impact estimate

When a task wraps up (or the user asks "how did we do?"), surface a rough
order-of-magnitude estimate. You can't see billing data, so be clear it's
approximate. Build it from what you can observe:

- **Per-request overhead**: MCP tool definitions, skills, rules on every request
- **Conversation growth**: each turn resends the whole history
- **Context loaded**: files read, their approximate sizes, unused reads
- **Model multiplier**: if part of the session ran above Sonnet ceiling

Present as 3–5 lines:

```
Token impact (rough estimate):
✅ Saved ~40k — read only 2 relevant files instead of exploring the package
✅ Saved ~25k/turn — session restarted at the implement phase
⚠️ ~30k/turn overhead — 5 connected MCP servers, none used this session
Biggest win next time: disable unused connectors
```

Skip for trivial exchanges. Never let the report become longer than the savings
it describes.

### 5.7 Git command presentation

**This section fires whenever git write operations are needed** — during any gate
(commit, push, PR, merge, tag, release), handoff summaries, or troubleshooting.

**The default depends on the execution environment** (`GATE_REFERENCE.md`, session start, step 0). The
deciding question is not cost — it is whether Claude's working tree and the
user's terminal are the same clone.

**Local session → present commands for the user to run.** They are the same
clone, so a command block operates on the work that was just done. Each git
command Claude executes via tool calls is a round trip that resends the full
conversation history — a chain of them (commit, push, tag, release) can cost
thousands of tokens. Presenting a block costs zero tool-call tokens. Present
first; execute via tool calls only if the user asks.

**Remote container → Claude executes git directly.** Claude's working tree is a
throwaway container; the user's terminal is a *different machine with a different
clone that never received these edits*. A command block handed to the user
commits nothing, and the container is reclaimed when the session ends — the work
is simply lost. Get approval per Section 1, then run the git commands via tool
calls from inside the container. Do not present a block as a substitute for
pushing. (Showing the user what you are about to run is fine — that is a
summary, not a handoff.) **One operation is carved out of this: the tag push —
see below.**

**Termux → clone flow.** The repo may not exist on the device at all. See
`SHELL_REFERENCE.md`.

**Tag pushes are the one exception — always hand them to the user.** In every
environment, `git tag` and `git push origin v<X.Y.Z>` are presented as a block
for the user to run. Never execute a tag push via tool calls, and never create
the tag ref through a GitHub MCP tool. Deleting or re-pushing a tag is the same
operation and the same rule.

Why this one and not the others: the credentials Claude runs under are routinely
denied on tag refs. A token that pushes branch commits all session gets **403**
on `git push origin v1.2.3`, because creating a `refs/tags/*` ref — and creating
a ref that *triggers a workflow* — is a separate permission, commonly withheld
even where `contents: write` is granted. And the blast radius is worse than an
ordinary denial: the tag push is what fires the release workflow, so a 403 there
strands a merged, version-bumped default branch with no release behind it. Route
it to the user's credentials from the start rather than discovering this
mid-ship.

🚀 SHIP stays ⏳ until the tag is confirmed on the remote — never ✅ on the
assumption the user ran the block. Confirm it yourself with
`git ls-remote --tags origin v<X.Y.Z>`; reading refs is not a write and is not
restricted. If you are told to attempt the push anyway and it 403s, do not
retry, re-route, or tag a different ref — report it and hand over the block.

The block's exact shape, the sync that must precede the tag, and the GitHub UI
fallback for users with no local clone are in `GATE_REFERENCE.md`, Gate 6.

**The gates are identical either way.** Presenting a command is performing it
(Section 1): the pre-flight runs, and the tracker goes in the same message,
above the block.

**Shell environment detection** is done at session start (`GATE_REFERENCE.md`, session start, step 2) for
local and Termux sessions; remote containers skip it. If a session reaches this
point needing a presented block without a detected shell (e.g. the skill loaded
mid-session), ask before presenting any commands.

**Remote verification.** Before presenting any push commands, verify the remote
is configured (`git remote -v`). If origin is not set, include
`git remote add origin <url>` (using the URL stored at session start, Section 6
step 1) as the first command in the block. This prevents the "default repo has
not been set" error.

**Never use bare `git push`.** Every push command must specify the remote and
branch explicitly: `git push -u origin <branch-name>`. The `-u` flag sets
upstream tracking, preventing the error on subsequent pushes.

**One block, not several.** When commands are presented for the user to run,
put the whole sequence in a **single fenced block they can copy once** — `cd`,
branch, add, commit, push, tag, release, all of it. Do not split an operation
across multiple blocks, and do not interleave prose between the commands.
Copy-pasting five separate blocks is five chances to miss one, run them out of
order, or land in the wrong directory.

Split into a second block only when the user genuinely has to stop and look at
something before continuing — a merge conflict to resolve, a build to verify, a
PR number needed by the next command. When you do split, say what to check
before moving on.

Explanation goes above or below the block, never inside it as interleaved prose.
Brief `#` comments within the block are fine.

**Always start with `cd`** in a presented block. Never assume the user's terminal
is already in the project directory. Every block presented for the user to run
must begin with the appropriate `cd` for their shell. (This does not apply to
commands Claude executes itself — the container's working directory is already
correct.)

**Load `SHELL_REFERENCE.md`** from this skill's base directory for the full
`cd` format table, shell-specific syntax rules, Termux clone flow, and example
command blocks for each supported shell.

### 5.8 Usage limit handoff

**When the system prompt shows the account is nearing its usage cap** (e.g.
`<total_tokens>` is low, the system mentions overage or rate limits, or the
user says they're running low on usage), proactively offer a handoff summary
before the session is forced to end:

> ⚠️ **Heads up — this account looks close to its usage limit.** If the session
> cuts off mid-task, you'll lose the working context. Want me to produce a
> handoff summary now so you can pick up in a fresh session (or on a different
> plan tier) without losing progress?

If yes, produce the same handoff format as Section 5.5:

```
## Handoff: [task name]
**Goal:** one sentence
**Current state:** what's done, what's verified
**Gate status:** show the tracker with current state
**Key files:** path:line — why it matters
**Decisions made:** constraints the next session must respect
**Shell environment:** [user's shell from session start, step 2]
**Next step:** the single concrete next action
```

Include the gate tracker state so the next session knows where to resume the
workflow. Include the shell environment so the next session doesn't have to
re-ask.

If the user hasn't explicitly said they're low, but you observe signs (the
system prompt's token budget is below ~2M, the session has been long, or the
conversation was compressed), mention it once lightly:

> "We've been going a while — want a handoff summary in case you want to
> continue in a fresh session?"

Don't nag. Once offered, drop it unless the user asks.

---

## 6. Session start

When this skill loads, **read `GATE_REFERENCE.md` from this skill's base
directory** (shown when the skill loaded, e.g. "Base directory for this
skill: ...") and follow its session-start procedure. It covers, in order:

- **Self-check** — the skill's reference files are all present
- **Step 0 — execution environment detection** (local / remote container /
  Termux). This decides whether Claude executes git or presents it, whether to
  ask the shell question, whether `gh` or GitHub MCP tools are used, and where
  the gate state file lives. Run it before anything else.
- **Steps 1–6** — repo URL, shell, sync offer, branch check, repo state, and
  **workflow detection: the local development workflow (what Gate 2 runs) and
  the CI workflow (what Gate 5's PR is checked by and Gate 6 fires).** Both are
  detected, and a missing one is surfaced against the gate it breaks
- **Step 7 — the unfinished release check.** Compare released versions against
  tags on the remote. A release that never got tagged is a Gate 6 that never
  finished, and start-of-session is the only place that reliably catches it — a
  container that is reclaimed never reaches Section 8
- **The gate state file** — write `.claude/dev-skills-gates.md` with all six
  gates ⬜ pending (Section 2)
- **The session banner and MCP check**

Then: "What are we building?"

---

## 7. Workflow status

When asked "status", "where are we", or at any natural checkpoint, read
`.claude/dev-skills-gates.md` and show the full gate tracker with current state,
naming the active track (work commit / release sequence). If the file is missing
or stale, re-derive from evidence per Section 2 before answering — do not
reconstruct the tracker from memory.

---

## 8. Session-end checkpoint

**This fires when the session is winding down** — the user says "thanks",
"that's all", "looks good", goes silent, or otherwise signals the work is done.

Before wrapping up, check:

1. **Were source files modified in this session?** (`git status` and `git diff`
   against the session's starting commit)
2. **If yes — are all applicable gates complete?** Show the gate tracker. Any
   gate that is not ✅ or ➖ N/A is unfinished work.
3. **Check for unmerged branches.** If the session created a branch with commits
   that haven't been merged to the default branch via PR, flag it:

   > ⚠️ **Session-end check: branch `feature/xyz` has unmerged commits.**
   > Should we finish the release workflow (Gates 5-6) before wrapping up?

4. **Check for untagged versions.** Run `git ls-remote --tags origin` and compare against the
   version in the project's version file(s). If the current version has no tag:

   > ⚠️ **Session-end check: version v1.2.3 has no git tag or GitHub release.**
   > The code is merged but not tagged/released. Should we finish Gates 5-6 now?

   **This is a backstop, not the primary check.** It only fires if the session
   gets to wind down — a remote container that is reclaimed, a usage limit, or a
   crash skips it entirely, and that is precisely when a release is most likely
   to be half-finished. The check that always runs is at session *start*
   (`GATE_REFERENCE.md`, step 7).

5. **If no source files were modified**, skip the gate check — the session was
   exploratory or advisory.

**Remote container sessions — uncommitted work is destroyed, not just pending.**
On a local session, uncommitted changes sit safely in the user's working tree
until next time. In a container they are lost when the session ends. Escalate
accordingly:

> 🚨 **Remote session ending with uncommitted changes.** These edits exist only
> in this container and will be lost when it is reclaimed. Nothing survives
> unless it is pushed. Should I commit and push to `<branch>` now?

Do NOT silently wind down a session that has uncommitted changes, untagged
versions, or incomplete gates. Surface the gap and let the user decide.

> **Session-end gate status:**
> 🔢 VERSION    ✅ v1.2.3
> 🔨 BUILD      ➖ N/A (config repo)
> 🔒 SECURITY   ✅
> 📄 DOCS       ✅
> 📦 RELEASE    ✅ PR #42
> 🚀 SHIP       🚫 NOT DONE — tag and release missing
>
> Should we finish shipping before wrapping up?

---

## 9. Audit mode

On "audit my project", "scan this codebase", "security review", or "check my code":

**First, load both reference files from this skill's base directory**
(shown when the skill loaded, e.g. "Base directory for this skill: ..."):
1. Read `SECURITY_REFERENCE.md` in the skill's base directory
2. Read `QUALITY_REFERENCE.md` in the skill's base directory

Then:
1. Discover source files via Glob
2. Triage — read high-risk files first (auth, login, upload, config, api, routes,
   crypto, token, secret, password)
3. Grep for dangerous patterns (`eval(`, `shell=True`, `pickle.loads`, `md5`,
   `Invoke-Expression`, `innerHTML`, hardcoded strings, `.env` files)
4. Apply every security rule from Section 4
5. Output findings using severity levels (🚨 Critical, ⚠️ High, 📝 Medium, 💡 Low)
   with file:line, description, and fix for each
6. End with summary: files scanned, total findings by severity, top 3 next steps
