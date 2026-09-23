---
name: dev-skills
version: 2.30.0
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
nothing is edited and no git write is executed or presented. This is a hard
stop, not a default: a mode nobody chose is a mode Claude guessed.

**Manual mode:** git commands are presented for the user to run (Section 5.8),
the tag push and every ref deletion come back to the user, and Claude stops
between steps. This is what the skill has always done.

**Semi-autonomous mode:** the user's own words pick it, at that question or
later ("auto mode", "take it from here"). It changes *who runs most of the
commands*, not what has to be true before they run, and not the two ref
operations the remote denies. Ask neutrally, manual first, recommending
neither; never infer, pre-select, or switch it on because the session is going
well. **It is not the harness's own "auto mode"** (a permission setting) —
being in that one answers nothing.

It changes two things (`AUTO_MODE.md` holds the checkpoint formats, the
per-step table and the stop conditions; chaining commands is §5.1, for every
mode):

1. **Claude executes git instead of presenting it**, in every environment:
   commits, branch pushes, the PR, the merge, CI watching, post-ship
   verification, tracker commits.
2. **Between-step confirmations collapse into two checkpoints, not none.** The
   version bump and release notes fold into the commit approval; the pre-ship
   confirmation becomes the **pre-tag report**, a full account of *every*
   action since the commit approval (commits, pushes, PR, every CI run, the
   merge commit, each gate's evidence, the version guard, and anything that
   failed, was retried or deviated), handed over with the tag block. It is
   the user's only view of the unattended stretch, so it is never a summary.

**What no mode changes:**

- **Commit approval (Section 1)**: every commit, with the diff and the drafted
  message seen and approved first. "Semi-autonomous" describes the commands,
  never the content.
- **The tag push and every ref deletion go to the user**, including the merged
  PR's own branch, so a merge never carries `--delete-branch`. This is a
  credential fact, not supervision: Claude's credentials are routinely `403`'d
  on exactly these (Section 5.8), and a mode cannot grant what the remote
  withholds. Claude resumes by itself once the tag is confirmed on the remote.
  Deleting a release, force-pushing and rewriting history keep their own
  explicit approval on top.
- **The gates, the pre-flight, the tracker, the state file.** Run them *more*
  carefully here, because the user is no longer watching each command.
- **Questions**: an ambiguous requirement, a design choice, a finding to
  resolve, a bump the history doesn't settle. The user chose semi-autonomous,
  not hands-off.
- **Section 8's session-end checkpoint** and the token impact estimate.

**When something goes wrong, that operation falls back to manual; the session
stays semi-autonomous.** A blocked gate, a Critical/High finding, a failed CI
or release run, a `403` on a branch push: stop, surface it, let the user decide.
Do not retry, re-route, or act on a different ref (Section 5.8).

**Record the mode where session state lives** — a `Mode:` line in
`.claude/dev-skills-gates.md` (Section 2), and on every tracker display:

```
Mode: semi-autonomous (approved 2026-09-19) — commits and the tag still
      require the user's approval
```

A mode held only in conversation dies at compaction.

**A `Mode:` row that is missing, reads `unchosen`, or names anything other than
`manual` or `semi-autonomous` means no mode, never manual.** Treat it like an
unpassed gate: ask the mode question and write the answer before any git
write. The hook enforces this for executed commands, and the prose enforces it
for presented ones (Section 1). A resumed session, or one that finds a
committed state file, asks again, because that `Mode:` line describes the
*last* session. Switching is one phrase either way ("manual mode", "auto
mode"): record it and continue.

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
- **Neither auto mode overrides this rule.** The *harness's* auto mode (the
  system prompt's "bias toward working without stopping") applies to
  implementation decisions, not to git write operations. This skill's own
  **semi-autonomous mode** (Operating modes) changes who runs the commands. It
  does not lift the tag-push and ref-deletion carve-out (Section 5.8), and it
  does not touch commit approval. Under both, the
  user's explicit yes on the diff and the drafted message comes first. Commit
  discipline is the one constraint no mode relaxes. When in doubt: ask, don't
  act.
- **Presenting a git command IS performing it.** Whether you run `git commit` via
  a tool call or print it in a fenced block for the user to paste, the approval
  and gate requirements are identical. A code block containing a git write command
  *is* a git write operation. This matters because Section 5.8 routes many
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
4. Draft a commit message per Section 1.1 and show it.
5. Wait for explicit approval.
6. **Present commands per Section 5.8.** In manual mode, present the git commands
   formatted for the user's shell environment so they can run them manually; only
   execute directly via tool calls if the user explicitly asks Claude to run them.
   In semi-autonomous mode (Operating modes) Claude executes them itself once the
   approval in step 5 is given — the approval covers the sequence Claude
   described, and nothing beyond it.

### 1.1 Commit message format — Conventional Commits

Every commit message follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <summary in imperative mood, lowercase, no trailing period>

[optional body — the WHY, not a restatement of the diff]

[optional footer(s)]
```

**Types:** `feat` (new capability), `fix` (bug fix), `docs`, `chore`
(tooling/config, no source behavior change), `refactor`, `perf`, `test`,
`ci`, `build`, `style`, `revert`. Pick the one that best describes the
*primary* effect of the commit — a fix that also updates a doc is still
`fix:`, not `docs:`.

**Breaking changes** get `!` right after the type/scope (`feat!:`,
`fix(api)!:`) and a `BREAKING CHANGE:` footer explaining what breaks and how
to adapt. This is not decorative — Gate 1 (VERSION) uses it as the strongest
available signal for the semver bump (below).

**This governs commit message text only.** It's a different convention from
`CHANGELOG.md`'s Keep a Changelog format (Section 4 / Gate 4's `## [X.Y.Z]` /
`### Added` structure) — that file stays hand-written prose grouped by
change type for a human reading the release, not generated from commit
messages. The two coexist; neither replaces the other.

**Feeding Gate 1 (VERSION).** When drafting the version bump, use the
commit types since the last tag as a signal, not a silent decision: any
`!` or `BREAKING CHANGE:` footer → MAJOR; any `feat` with no breaking change
→ MINOR; only `fix`/`chore`/`docs`/etc. → PATCH — the same mapping
semver.org itself describes. State which commits drove the call and confirm
the bump with the user (`GATE_REFERENCE.md`, Gate 1) — this narrows the
question, it doesn't answer it for them.

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
3. **Show the tracker** in this message, above any command block. Show the
   full six rows at session start, when a gate changed since they were last
   shown, on "status", and in handoffs. Otherwise one line is enough:
   `🔢✅ 🔨✅ 🔒⏳ 📄⬜ 📦⬜ 🚀⬜ · release sequence · semi-autonomous`. A
   blocking gate is always named in full (step 4), and the pre-tag report is
   never the short form (`AUTO_MODE.md`).
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
own terminal. On local sessions, where presenting is the default (Section 5.8),
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

**"Default branch" is whatever the remote reports** (`git remote show origin`
→ `HEAD branch:`, or `gh repo view --json defaultBranchRef`), never an assumed
name. The release track is triggered by *publishing intent* (a version bump,
an artifact, a tag, a publish), not by which branch holds the change or what it
is called.

**A merge to the default branch with no publishing intent is a work commit.**
Say so explicitly: a tracker update, a docs typo, a chore that bumps and tags
nothing gets RELEASE and SHIP ➖ N/A with the reason stated ("no version/
artifact/tag involved — bookkeeping only"). Six-gate ceremony on those is the
friction that gets real ambiguous cases waved through. **When this repo's
convention is genuinely unclear, ask once, at session start, with
`AskUserQuestion`**, not mid-gate with a PR already blocked.

### Gate state — must be durable

The tracker is not a message you printed once; it is a file. Conversation history
gets compacted away, and a tracker rebuilt from memory is rebuilt optimistically
("security ran earlier, I think"). Write the state down.

**File:** `.claude/dev-skills-gates.md` in the repo root.

- **Write it** at session start, and after every gate transition.
- **The `Mode:` row is written at session start too** — `unchosen` until the
  user answers, then their choice, rewritten whenever it changes. Missing or
  `unchosen` blocks every git write; it never means manual (Operating modes).
- **Read it** before every git write operation, and whenever asked for status.
- **It ships inside the release PR**, staged with the release commit at Gate 5
  — gates 1–5 ✅ and SHIP ⏳, since the tag does not exist yet. The post-tag
  SHIP ✅ line folds into the next release's PR. **Never open a PR whose only
  content is tracker bookkeeping**: a release PR that omits the state file
  leaves the tagged commit describing a release that had not happened
  (`SHIP_REFERENCE.md`, step 7).
- **Local sessions:** add it to `.gitignore` — it is session scratch.
- **Remote containers:** commit it to the working branch instead. The container
  is reclaimed when the session ends, and an uncommitted state file dies with it
  (`SESSION_START.md`, step 0). If the repo already gitignores
  the file — this one does, for local users — stage it explicitly with
  `git add -f .claude/dev-skills-gates.md`, or accept that state will not survive
  the session and re-derive from evidence next time. Do not silently let it
  vanish.

Format:

```
# Dev Skills gate state
Track: release sequence
Mode: manual
Origin: owner/repo (not a fork)
Version: 2.12.0
Updated: 2026-09-07

🔢 VERSION    ✅ all refs at 2.12.0
🔨 BUILD      ➖ N/A — skill repo, no build system
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜
```

**Row format: the status symbol and every word the hook checks go on the row's
first line.** The hook and re-derivation both read the ✅/➖/⏳/🚫/⬜ symbol and
annotations like `handoff` or `0 open` line by line, so a check that wraps to
line two reads as absent. Keep line one to the symbol plus a short label, and
put the why and the evidence on indented lines below it.

**Keep the file small.** It is read in full on every gate check and every git
write. Long write-ups belong in the commit message or `CHANGELOG.md`.
**Close an absorbed section in the step that absorbs it** (a VERSION or SHIP
step folding earlier work-commit entries into a release), never in a later
cleanup pass. A stale "IN PROGRESS" reads as open work to the next session.

**Never read ref state from local copies.** `git tag -l` returns empty in any
fresh or shallow clone, and `git branch -r` lists stale cached refs. Both
report absence that means nothing. Query the remote. Reading refs is not a
write, so this is always safe to run:

```
git ls-remote --tags origin              # all tags
git ls-remote --tags origin v1.2.3       # one tag
git ls-remote --heads origin             # all branches
git ls-remote --heads origin main        # one branch
```

**Re-derivation — when the state file is missing, stale, or the session was
compacted.** Do not guess, and do not treat a gate as passed because it feels
like it did. Rebuild from evidence:

| Gate | Evidence that it passed |
|---|---|
| 🔢 VERSION | every version-carrying file reads the same bumped semver, and `git ls-remote --tags origin` shows the previous version tagged |
| 🔨 BUILD | a build artifact exists newer than the last source edit — or the project has no build system (➖ N/A). **A check list with zero runs is ⬜, never ✅** — see below |
| 🔒 SECURITY | a scan was run against the **current** diff; a scan of earlier code does not cover edits made after it |
| 📄 DOCS | the changelog has an entry for this version, and the README matches current behavior |
| 📦 RELEASE | a PR exists for this branch (`gh pr list`, or MCP `list_pull_requests`) |
| 🚀 SHIP | tag on remote, release exists, PR merged, expected assets attached |

Any gate you cannot prove from evidence is ⬜ pending and must be run.
"It probably ran" is ⬜.

**Absence of a verdict is not a verdict.** "No runs", "no findings", "no
alerts", "no output" are all ⬜ until you have established *why* they are
empty. Confirm the mechanism actually ran before reading its silence as a
pass: an empty CI check list, a scanner that never executed, and a Dependabot
feed that is disabled rather than clean all look like success.

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
1. Run `git log`, `git ls-remote --heads origin`, `git ls-remote --tags origin`, and `gh pr list` / `gh pr view`
   — or the GitHub MCP equivalents when `gh` is unavailable (`SESSION_START.md`, step 0)
2. Credit completed steps on the tracker (✅ with "user-driven" or "already done")
3. Re-derive Gates 1–4 from evidence (table above) — never from the presence of
   a commit
4. Continue from the first gate that is not ✅ or ➖ N/A

### Running a gate

**Before running, passing, or marking ➖ N/A on any gate, read that gate's
reference file** from this skill's base directory (shown when the skill loaded,
e.g. "Base directory for this skill: ..."). Gates 1–5 are in
`GATE_REFERENCE.md`, except **Gate 3, which is in `SECURITY_GATE.md`** and
**Gate 6, in `SHIP_REFERENCE.md`**. Each holds its gates' checks, pass criteria, blocked-output format, and the CI-versus-manual
paths. Do not run a gate from memory of this summary — the summary says what
each gate is *for*, not what makes it pass.

**Read the one the gate you are running is in, not both.** The ship path is the
largest of the six and fires once, at the end; loading it during Gate 1 costs
the tokens without the content ever being used.

| Gate | Passes when |
|---|---|
| 🔢 **VERSION** | every version reference in the project agrees on one bumped semver, repo and release-notes links present, prior version tagged |
| 🔨 **BUILD** | the project's **local dev workflow** builds it and the app is verified working — or ➖ N/A with no build system. CI is not a substitute: it runs after the commit this gate is protecting |
| 🔒 **SECURITY** | security scan at 0 Critical / 0 High, plus a quality review the user has seen |
| 📄 **DOCS** | changelog entry for this version, and every doc claim matches current behavior |
| 📦 **RELEASE** | branch synced, commit approved, PR open, release notes approved |
| 🚀 **SHIP** | merged, tagged, published, and all four post-ship checks verified |

Gate 3 (`SECURITY_GATE.md`) additionally loads `SECURITY_REFERENCE.md` and
`QUALITY_REFERENCE.md`; Gate 6's ship path depends on whether a CI release workflow exists, and both of
its paths are in `SHIP_REFERENCE.md`.

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

**For the life of the project** — the manifest is re-audited on every security
gate, not just when it changes:

- Run the ecosystem's audit tool against the **current** lockfile at Gate 3.
  Critical/High blocks; Medium/Low is surfaced for the user to accept.
- Treat a dependency with no upstream fix available as a finding to raise, not
  to swallow: report the advisory, the affected path, and the options
  (pin forward, patch, vendor, replace, or accept with a documented reason).
- Upgrades are code changes. A security patch bump rides the current branch; a
  major-version bump is its own change with its own gates, never folded silently
  into an unrelated PR.
- **Automate the watch, both halves.** (1) Version updates:
  `.github/dependabot.yml` covering every ecosystem (`WORKFLOW_REFERENCE.md`).
  (2) Alerts and security updates: a repository *setting*, not a file. Check
  `GET /repos/{owner}/{repo}/dependabot/alerts`. A `403 "…disabled…"` is an
  open **Gate 3 finding** that blocks the release. Give the user the
  enablement steps in `SECURITY_GATE.md` ("Enabling Dependabot alerts") and
  re-check the endpoint before marking it fixed. Having only (1) is the trap:
  a queue of "Bump X" PRs looks like security maintenance while nothing is
  ever reported.

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
High hard-stop everything immediately. Medium and Low do not stop a work commit
— progress must be savable — but **no finding of any severity may be open when
the release track runs.** Gate 5 and Gate 6 are blocked while anything is open.

A finding leaves the open state three ways, and no others: **fixed** (and
re-verified against the current diff), **waived** (only the user, for that
specific finding, with a reason and date on the tracker), or **withdrawn** (it
was wrong — say why). "Pre-existing", "unrelated to this change", "only a
Medium", "next release" are not terminal states; they are how a real finding
rode across two releases of this repo with every gate reading ✅.

**Claude never waives its own finding**, and "ignore Mediums" or "stop flagging
that" is a request to suppress a category, not a waiver — ask for the specific
finding instead. A waiver covers the finding as it stands and re-opens if its
context changes.

**Surface a finding at the moment it is discovered**, not in the ship summary.
A finding raised after the tag is a finding raised past every point where the
user could have acted on it. Full lifecycle, the tracker format, and the hook's
illegal state are in `SECURITY_GATE.md`.

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

**Chain shell commands into one invocation — in every mode.** Session-start
reads, gate evidence, the session-end checkpoint, and any step that is several
commands which must all succeed are one call, not one per command. `&&` them
so the first failure stops the chain; `;` only for independent read-only
commands whose output you want even if one fails. Examples:

```
git status -sb && git diff --stat && git ls-remote --tags origin
git add -A && git commit -m "<message>" && git push -u origin <branch>
```

This governs the commands Claude runs. A block presented to the user chains
with that shell's syntax (`;` in Windows PowerShell, `SHELL_REFERENCE.md`).
Chaining changes the number of round trips, never the checks: the pre-flight
runs before the line is written, and the pre-flight hook scans every command in
a chain, not only the first.

**Do not chain across a stop.** Anything the user must see or decide between
two commands is a boundary the chain does not cross: the commit approval, the
tag block, a gate that has not passed, a failed command whose output changes
what comes next. When in doubt, split — a wasted round trip is cheaper than an
action the user did not approve.

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

### 5.4 Subagent model delegation

When spawning a subagent (the Agent tool), use the cheapest model that can
handle the task. Each spawn starts cold with full context re-injection — the
model tier on top of that is the lever you control.

| Tier | Model | Use for |
|---|---|---|
| **Cheap** | Haiku | single-target lookups, grep/glob searches, reading one file, mechanical checks, simple Q&A |
| **Standard** | Sonnet | multi-step research, code implementation, refactoring, code review, test writing |
| **Expensive** | Opus / Fable | complex architecture, deep root-cause debugging, security analysis — only when the main session is already approved above the Sonnet ceiling |

**Rules:**
- Never spawn a subagent on a more expensive model than the main session is
  approved for. If the session is on Sonnet, subagents are Sonnet or Haiku.
- Default to Haiku for any task that is essentially "find X and report back."
  The Explore agent type is already read-only — pairing it with Haiku is the
  cheapest delegation available.
- Use Sonnet for subagents that write code, review code, or need multi-step
  reasoning across files.
- Escalate to the main session's model only when the subagent's task is the
  kind that justified the main session's model in the first place.

### 5.5 MCP server and connector awareness

**Active** MCP servers (full tool definitions in context) cost thousands of
tokens per request. **Deferred** ones (name-only) cost little: report them as a
count, never by name. **Never name a server whose `mcp__<server>__` prefix is
not literally in your context.** Flag an active server the work never touches,
once. The session-start check, how the user disables servers, and the
after-`/mcp` re-check are in `SESSION_START.md`, "MCP check".

### 5.6 Phase transitions → fresh session

A long session resends its entire history on every request, so a fresh start is
often the largest saving available. Offer a handoff at any of these points.
**Each is an observable event, not a judgment call** — "work shifted phase" was
the old trigger, and a model biased toward continuing never once decided that it
had:

1. **A release sequence finished.** The tracker reads ✅ or ➖ N/A across all six
   gates. The work shipped; nothing in the history is load-bearing any more.
2. **The user opens work unrelated to the current tracker** — a different
   feature, a different area of the repo — while no release is mid-flight.
3. **The conversation was compacted.** History is now both expensive enough to
   matter and lossy enough that a written handoff beats scrolling it.

State the observation and the reason in one line. Do not phrase it as an
open-ended question, which is easy to drop:

> This session is carrying [N] turns and the release is done — a fresh one would
> be cheaper. Want a handoff summary?

**Handoff format** (also used by Section 5.9):

```
## Handoff: [task name]
**Goal:** one sentence
**Current state:** what's done, what's verified
**Gate status:** the tracker, with current state
**Mode:** manual / semi-autonomous — what *this* session ran in. The next session
asks again at its start (Operating modes)
**Key files:** path:line — why it matters
**Decisions made:** constraints the next session must respect
**Shell environment:** [user's shell from session start, step 2]
**Next step:** the single concrete next action
```

Keep it under ~30 lines. The point is to replace a long history with a cheap
restart. Include the gate tracker so the next session knows where to resume, and
the shell environment so it doesn't have to re-ask.

### 5.7 Token impact estimate

**Two triggers, both firm:**

1. **The session-end checkpoint** (Section 8). Include the estimate every time
   that checkpoint runs — it already has a reliable trigger, this section did
   not.
2. **On request** — "how did we do?", "what did that cost?".

**The only skip condition is the one Section 1 already uses for gates: the
session modified no tracked file.** An exploratory or advisory session has no
token story worth telling. "This felt like a small task" is *not* a skip
condition — that judgment call is precisely what kept this section from ever
firing.

You can't see billing data, so be clear it's approximate. Build it from what you
can observe:

- **Per-request overhead**: MCP tool definitions, skills, rules on every request
- **Conversation growth**: each turn resends the whole history
- **Context loaded**: files read, their approximate sizes, unused reads
- **Model multiplier**: if part of the session ran above Sonnet ceiling

Present as a header and at most 3 lines. Include the MCP line only when
connections changed since the session-start MCP check. Otherwise that check
already said it:

```
Token impact (rough estimate):
✅ Saved ~40k — read only 2 relevant files instead of exploring the package
⚠️ ~30k/turn overhead — 5 connected MCP servers, none used this session
Biggest win next time: disable unused connectors
```

Never let the report become longer than the savings it describes.

### 5.8 Git command presentation

**Fires whenever git write operations are needed**: any gate, handoffs,
troubleshooting. **Before composing any command block, load
`SHELL_REFERENCE.md`** (`cd` formats per shell, the one-block rule, remote
verification, forks, the Termux clone flow, the 403 rationale, examples). Do
not build a block from memory of this summary.

**In semi-autonomous mode Claude runs the commands** (Operating modes), and the
table below is only the fallback shape for an operation that fails. Say the
cost trade once, when the user opts in: executed git resends the conversation
on every round trip, where a pasted block costs nothing.

**In manual mode, direction depends on the environment** (`SESSION_START.md`,
step 0). The deciding question is whether Claude's working tree and the
user's terminal are the same clone:

| Environment | Git operations |
|---|---|
| **Local** | Same clone — **present** the commands for the user to run. A block costs zero tool-call tokens |
| **Remote container** | A throwaway container the user's terminal never sees — **Claude executes** git directly, after approval (Section 1). A block handed over commits nothing |
| **Termux** | Present, and the repo may not be on the device at all — clone flow in `SHELL_REFERENCE.md` |

**Tag pushes and ref deletions are the exceptions: they always go to the user,
in both modes and every environment, remote containers included.** Creating a tag (`git tag`,
`git push origin v<X.Y.Z>`) and deleting any ref, whether a branch
(`git push origin --delete <branch>`) or a tag
(`git push origin :refs/tags/v<X.Y.Z>`), is presented as a block. Never run
either through a tool call or a GitHub MCP tool. Re-pushing a tag is a delete
plus a create, so both halves go to the user. Claude's credentials are
routinely denied on exactly these while branch pushes succeed, and a denied tag
push strands a merged, bumped default branch with no release. No mode lifts
this, because the denial comes from the remote. On a `403`, do not retry,
re-route, or act on a different ref.

🚀 SHIP stays ⏳ until the tag is confirmed on the remote
(`git ls-remote --tags origin v<X.Y.Z>`; a branch deletion by
`git ls-remote --heads origin <branch>` returning nothing) **and** it points at
the merged commit. A tag pushed early still exists, on the wrong commit
(`SHIP_REFERENCE.md`).

**The gates are identical either way.** Presenting a command is performing it
(Section 1): the pre-flight runs, and the tracker goes in the same message,
above the block.

**Forks: `origin` is the fork, and nothing targets upstream.** Every push, PR,
merge, release and tag block goes to the fork. The user does anything upstream
on GitHub directly. Every `gh` write passes `--repo <fork>`, because a bare
`gh pr create` in a fork opens on the parent. Rules: `SHELL_REFERENCE.md`,
"Forks".

### 5.9 Usage limit handoff

**Trigger on any of these. All three are things you can actually observe:**

- The system prompt or a system message mentions overage, rate limits, or a
  usage cap being approached
- The user says they are running low, near a limit, or about to be cut off
- The conversation has been compacted (also a Section 5.6 trigger)

**Do not gate this on a numeric token budget.** Earlier versions watched for a
context budget below ~2M. On Claude Code for web that figure starts at 15M every
session and effectively never falls, so the check never fired once. A visible
number that is genuinely low still counts — but it is not the condition, and its
absence is not a reason to stay quiet.

> ⚠️ **Heads up — this session looks close to a limit.** If it cuts off mid-task
> you lose the working context. Want a handoff summary now, so you can resume in
> a fresh session without losing progress?

Use the handoff format in Section 5.6 — it carries the gate tracker and the
shell environment, which is exactly what a resumed session would otherwise have
to rediscover.

Don't nag. Once offered, drop it unless the user asks.

---

## 6. Session start

When this skill loads, **read `SESSION_START.md` from this skill's base
directory** and follow it in order:
- the self-check
- **the version check** against the latest upstream tag. If this copy is
  behind, the loud bracketed warning goes first, then an explicit "continue or
  update first?", and `⚠️ outdated` rides on every later tracker
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
