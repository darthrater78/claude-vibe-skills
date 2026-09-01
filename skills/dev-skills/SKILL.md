---
name: dev-skills
version: 2.7.1
description: >
  Development discipline: commit approval, versioned builds, security scanning,
  cost control, and a strict gate workflow that never advances silently. Trigger
  on: "dev mode", "dev skills", "start coding", "build", "ship it", "push",
  "release", "commit", "done", "just push it", "skip the version", "audit",
  "security review", "scan this", "check my code", or any attempt to bypass a
  gate.
---

# Dev Skills

This skill is the contract for every coding session. It is always active. Gates
cannot be skipped, commits cannot happen without approval, and security scans
run after every build — not eventually, not later, now.

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

**Before ANY git write operation (commit, push, PR, merge, tag, release):**
1. **Check the gate tracker.** If any gate applies to this session's work and
   has not passed, stop and surface the blocking gate. This is not optional —
   even if the user says "commit", "merge", or "push", check the gates FIRST.
   The gates exist precisely for the moments when you're moving fast and want
   to skip them.
2. If building an app: confirm a test build has been created and verified working.
3. Run `git status` and `git diff` to show what will be committed.
4. Draft a commit message and show it.
5. Wait for explicit approval before executing.

**When do gates apply?** Any session that has produced code changes, version
bumps, builds, or is heading toward a release. If the session modified source
files and will commit them, the gates apply. The only exception is trivial
non-code changes (typo in a comment, updating a gitignore) where no build or
release is involved — and even then, commit approval is still required.

---

## 2. The six gates

**MANDATORY PRE-FLIGHT:** Before running `git commit`, `git push`, `gh pr create`,
`gh pr merge`, `git tag`, or `gh release create`, STOP and check:
1. Do these gates apply to this session? (Did you modify source files, version
   files, or build artifacts? If yes → gates apply.)
2. What is the current gate state? Show the tracker.
3. Are all required gates passed? If not → surface the blocking gate and do NOT
   proceed with the git operation.

This pre-flight is the enforcement mechanism. It fires on every git write
operation, every time, with no exceptions. The user saying "commit" or "merge"
does not bypass it — it triggers it.

Every session that produces a build, release, or push moves through these gates
in order. A gate cannot be silently skipped. If the user tries to jump ahead,
show the gate tracker and surface the blocking gate.

```
🔢 VERSION  →  🔨 BUILD  →  🔒 SECURITY  →  📄 DOCS  →  📦 RELEASE  →  🚀 SHIP
```

Gate indicators:
- ✅ PASSED
- 🚫 BLOCKED — hard stop
- ⏳ IN PROGRESS
- ⬜ PENDING
- ➖ N/A — gate does not apply to this project

**Marking a gate N/A:** Some gates don't apply to every project (e.g. no build
step for a docs-only or config repo). When a gate genuinely doesn't apply:
1. State why it doesn't apply (e.g. "no build step — this is a skill/config repo")
2. Mark it ➖ N/A on the tracker
3. Move to the next gate

A gate can only be N/A for structural reasons (the project has no build system,
no compiled artifacts, no app UI). "We'll do it later" or "it's not important
this time" is not N/A — that's a skip attempt, and skips are blocked.

### Gate 1 — Version 🔢

No build starts until versioning is resolved.

**Check ALL of these:**
1. Find every version-carrying file in the project: `package.json`, `pyproject.toml`,
   `Cargo.toml`, `VERSION`, `setup.cfg`, `build.gradle`, `pom.xml`, manifest files,
   `Info.plist`, `AndroidManifest.xml`, `.csproj`, `AssemblyInfo.cs`, etc.
2. **Search source code for hardcoded version strings.** Grep the project for the
   current version number (e.g. `1.0.0`, `v1.0.0`). Check XAML, HTML, UI templates,
   "About" dialogs, splash screens, window titles, headers, footers, constants, and
   config files. Every instance must be updated — not just the manifest files.
   A missed version string in the app's UI is a gate failure.
3. Every version reference must show the same version and it must be bumped from
   the previous release.
4. Version must follow semver (MAJOR.MINOR.PATCH).
5. **Repository link is mandatory.** Every project that has an app manifest
   (`package.json`, `pyproject.toml`, `Cargo.toml`, etc.) must include the
   `repository` / `homepage` / `[project.urls]` field pointing to the GitHub repo
   it belongs to. If missing, add it before passing this gate.
6. **Release notes link is mandatory.** Every app that displays a repository link
   (in an "About" dialog, settings screen, footer, help menu, etc.) must also
   include a link to the current version's release notes. Use the pattern
   `https://github.com/<owner>/<repo>/releases/tag/v<VERSION>` — the version in
   the URL must match the version being built. If the app already shows a repo
   link but has no release notes link, add one before passing this gate.

7. **Previous version tags must exist.** Run `git tag -l` and verify that prior
   released versions have corresponding git tags. If the previous version (the one
   being bumped from) has no tag, flag it:

   > ⚠️ **Missing tag for previous version:** v1.2.2 was released but has no git tag.
   > This should be fixed (retroactively tag the merge commit) before or alongside
   > this release.

   Missing tags for older versions should be noted but don't hard-block — fix them
   if the merge commits are identifiable, flag them otherwise.

If any check fails:

> 🚫 **VERSION GATE BLOCKED**
> Issues found:
> - [specific issue, e.g. "package.json version is 1.0.0 but VERSION file says 1.0.1"]
> - [e.g. "MainWindow.xaml still shows v1.0.0 in the title bar"]
> - [e.g. "package.json missing repository field"]
> - [e.g. "About dialog has repo link but no release notes link"]
> - [e.g. "v1.2.2 has no git tag — needs retroactive tagging"]
>
> Current version: [version or "none found"]
> What version should this build be? (patch / minor / major)

Update ALL version files, add missing repo links and release notes links before marking passed.

### Gate 2 — Build 🔨

Run the project's build command only after Gate 1 is ✅. If the build fails,
fix and rebuild — do not advance.

**A test build is mandatory before any commit.** When building an app, create a
test/dev version and verify it runs correctly before staging or committing anything.
This means:
1. Build the project (dev/test mode where applicable)
2. Launch or preview the app — confirm it starts, the golden path works, and
   no regressions are visible
3. Only after the test build is verified working does this gate pass

If the app cannot be tested locally (e.g. requires external infrastructure),
say so explicitly rather than skipping — the user decides whether to proceed.

**Projects with no build step** (config repos, skill repos, documentation-only
repos, pure script collections): mark this gate ➖ N/A with an explanation:

> ➖ **BUILD GATE N/A** — this is a [skill/config/docs] repo with no build system.

Do not silently skip — always show the N/A status on the tracker.

> ✅ **BUILD GATE PASSED** — test build verified working
> Output: [artifact path]

### Gate 3 — Security & Quality 🔒

**Mandatory after every successful build. Not optional. Not "later."**

This gate has two steps that must both pass: a security scan and a quality review.

**Before scanning, load both reference files from this skill's base directory**
(shown when the skill loaded, e.g. "Base directory for this skill: ..."):
1. Read `SECURITY_REFERENCE.md` in the skill's base directory — bad/good code
   examples for every security pattern.
2. Read `QUALITY_REFERENCE.md` in the skill's base directory — bad/good code
   examples for structure and performance anti-patterns.
Use these examples to pattern-match against the code being reviewed.

#### Step 1 — Security scan

Run a full scan of all source files. Check for every pattern category in
Sections 4.1–4.3 and the full rule checklists in `SECURITY_REFERENCE.md` (loaded
above). Also run the project's native audit tool (`npm audit`,
`pip audit`, `cargo audit`, etc.) if available.

**Hard stops (must fix before proceeding):**
- 🚨 Critical: hardcoded secrets, SQL injection, `shell=True` with user input,
  disabled TLS, `pickle` on untrusted data, RCE vectors
- ⚠️ High: path traversal, missing auth, `debug=True` in prod, weak crypto for
  passwords, `random` for tokens, no input validation on endpoints

**Show and let user decide:**
- 📝 Medium: bare `except`, no type hints, mutable defaults, `assert` for validation,
  logging sensitive data, unpinned deps
- 💡 Low: missing `encoding=` on `open()`, string paths, missing static analysis in CI

Security step passes at zero Critical and zero High:

> ✅ **Security scan passed** — 0 Critical, 0 High
> Medium: N (shown above, user accepted) | Low: N

#### Step 2 — Quality review

Scan the changed code for every quality pattern in `QUALITY_REFERENCE.md` (loaded
above) and the checklist below:

**Structure issues (flag and fix):**
- Deep nesting (>3 levels) — flatten with early returns
- God functions (>~40 lines or multiple responsibilities) — split
- Circular dependencies — restructure
- Hidden side effects in getters or utility functions — rename or separate
- Copy-pasted logic that should be shared — extract

**Performance issues (flag and fix):**
- N+1 queries — batch with IN/ANY or joins
- Wrong data structures (lists for lookups instead of sets/dicts)
- String concatenation in loops — use join/builders
- Recomputation in loops (regex, config, API calls) — compute once
- Allocations in hot paths — move constants to module level
- Loading everything when a subset is needed — SELECT specific columns, paginate
- Blocking I/O on async event loops — use async alternatives
- Unbounded caches — use lru_cache with maxsize
- Missing database indexes on queried columns
- Event listeners never cleaned up — add teardown

Report quality findings separately from security:

> **Quality review — changed code:**
> ⚠️ `app.py:45` — N+1 query inside loop (fetches orders per user)
>    Fix: batch with `WHERE user_id = ANY(%s)`
> ⚠️ `utils.py:120` — function is 80 lines with 5 responsibilities
>    Fix: split into validate_input, transform_data, save_result
> ✅ No deep nesting issues
> ✅ No circular dependencies

Quality issues don't hard-block the gate (they're not security vulnerabilities),
but they must be surfaced and the user must acknowledge them. Fix what's
reasonable within the current scope — flag the rest as known technical debt.

#### Gate 3 combined output

Both steps must complete before the gate passes:

> ✅ **SECURITY & QUALITY GATE PASSED**
> Security: 0 Critical, 0 High | Medium: N | Low: N
> Quality: N structure issues, N performance issues (shown above, user accepted)

If the user says "skip security" or "we can do security later":

> 🚫 **SECURITY GATE BLOCKED**
> Security scan is mandatory after every build. Running now.

Then run it. Do not ask again.

### Gate 4 — Docs 📄

After security passes, check:
1. **Version history / changelog** — the README or CHANGELOG must have an entry for
   this version with the date and a summary of changes. Mandatory for every release.
2. **New or changed features** — if the session added, removed, or changed any
   user-facing behavior (new flags, commands, changed defaults, removed features),
   the README usage/feature docs must reflect it.
3. **Removed features** — scan the README for references to anything removed in this
   session. Stale descriptions of removed features are a hard stop.
4. **Architecture / dependency docs** — if the project documents external calls,
   timeout tables, architecture, or dependencies, verify they still match the code.
5. **Internal consistency** — if the README describes how the project works (gate
   names, workflows, install steps, feature summaries, diagrams), cross-check every
   description against the actual source of truth (SKILL.md, code, config). Renamed
   concepts, restructured workflows, and changed terminology must be reflected
   everywhere — not just in the changelog. Read the full README and flag any
   description that no longer matches.

Show what was checked:

> ✅ **DOCS GATE PASSED**
> - Version history: v1.2.3 entry added with date and changes
> - New features: [list any docs updated]
> - Removed features: [list any stale refs cleaned up, or "none"]
> - Architecture/tables: [updated / no changes needed]
> - Internal consistency: [README descriptions match source of truth, or list fixes]

If documentation is missing or stale:

> 🚫 **DOCS GATE BLOCKED**
> The following documentation issues must be resolved:
> - [specific issue, e.g. "README still references feature X which was removed"]
> - [specific issue, e.g. "README calls Gate 6 'Push' but it was renamed to 'Ship'"]
> - [specific issue, e.g. "No version history entry for v1.2.3"]
>
> Fixing now...

Fix any issues found. Rebuild if doc fixes affected source files.

### Gate 5 — Release 📦

This gate prepares the release: branch, commit, PR, and release notes draft.
Execution (merge, tag, publish) happens in Gate 6.

**Steps:**
1. Create a feature branch if not on one (`release/vX.Y.Z`, `feature/desc`, `fix/desc`)
2. **Get commit approval** (per Section 1 above) — show what's staged, get explicit yes
3. Commit to the feature branch
4. Push the branch and create a PR against the default branch
5. Draft release notes and show the PR + notes to the user:

   > 📝 **PR created — review before shipping:**
   >
   > **v1.2.3**
   > - [change 1 from this session]
   > - [change 2 from this session]
   >
   > PR: [url]
   >
   > Do these accurately describe what's in this build? Reply "yes" to ship,
   > or tell me what to change.

6. Wait for explicit approval of the PR content and release notes

**Never commit directly to main/master.** Branch protection is enforced.
**Exception:** `darthrater78/scripts` allows direct pushes but PRs are preferred.

> ✅ **RELEASE GATE PASSED** — PR [url] ready, release notes approved
> Pending: merge, tag, and publish (Gate 6)

### Gate 6 — Ship 🚀

This gate executes the release: merge, tag, and publish. It is the single
execution point for all three — they happen here, not in Gate 5.

**Pre-ship summary:** Present everything that will happen and wait for explicit
confirmation. A vague "yeah" or "ok" is not enough — the user must say "ship",
"push", "yes push", or "go ahead."

> **Ready to ship. Please confirm:**
>
> Branch: `release/v1.2.3` → `main`
> PR: [url]
> Tag to create: `v1.2.3`
> Release notes: [first line of approved notes]
> Artifact: [path/size, or "none" for non-app projects]
>
> Type **"ship"** to confirm, or tell me what to adjust.

**Distributable artifacts — active detection required.** Do not assume a project
has no artifacts. Actively scan for evidence:

1. **Check build tooling:** look for PyInstaller specs (`.spec`, `pyinstaller` in
   requirements/scripts), Makefile/build targets, `setup.py` with `entry_points`,
   `cargo build --release`, `go build`, `dotnet publish`, webpack/vite configs,
   `.skill` source directories, or any build script in `scripts/`, `build/`, `Makefile`.
2. **Check README:** look for download links, install instructions referencing
   binaries/executables/packages, or "Download" sections.
3. **Check prior releases:** run `gh release view <previous-tag>` — if prior
   releases had assets attached, this one should too.

If ANY of these indicators exist, artifacts are expected. Build them:
1. Rebuild from the current committed source files
2. Verify the contents match the version being released (check dates, file sizes,
   spot-check content)
3. Include them in the `gh release create` command or upload with `gh release upload`

**A release that should have artifacts but doesn't is a ship failure** — even if
the README has no download links. If prior releases had an EXE/binary/package
and this one doesn't, that's a regression.

If the README has download links (e.g. `../../releases/latest/download/file.ext`),
every linked file must be present as a release asset. A release with broken
download links is a ship failure.

**Execution (all steps, in order):**
```
gh pr merge <number> --merge --delete-branch
git checkout main && git pull origin main
git tag v1.2.3
git push origin v1.2.3
gh release create v1.2.3 <artifacts> --title "v1.2.3" --notes "..."
```

**Post-ship verification (mandatory — the gate does not pass without this):**
After executing, verify that every step actually succeeded:

1. **Tag exists on remote:** run `git ls-remote --tags origin v1.2.3` — must
   return the tag. If not, the tag push failed — fix and retry.
2. **GitHub release exists:** check that the release is visible (via
   `gh release view v1.2.3` or the GitHub API). If not, create it.
3. **PR is merged:** confirm the PR state is "merged", not just "closed."
4. **Release assets:** verify against the artifact detection above. If build
   tooling, README downloads, or prior releases indicated artifacts are expected,
   confirm they are attached. A release missing expected artifacts is incomplete
   — do not pass with "assets: none" when the project builds distributable files.

Only after all verifications pass:

> ✅ **SHIP GATE PASSED** — PR merged, tag v1.2.3 pushed, release published
> Release URL: [url]
> Verified: tag on remote ✅ | release exists ✅ | PR merged ✅ | assets ✅

If any verification fails:

> 🚫 **SHIP GATE BLOCKED — post-ship verification failed**
> - Tag on remote: [✅ or ❌ — details]
> - Release exists: [✅ or ❌ — details]
> - PR merged: [✅ or ❌ — details]
> - Release assets: [✅ or ❌ — details]
>
> Fixing...

Fix the failed step and re-verify. Do not mark the gate passed until all
verifications succeed.

#### Updating an existing release artifact (`--clobber`)

If the artifact is uploaded to an *existing* release (e.g. `gh release upload --clobber`),
the original release notes are now stale. This is a hard stop:

> 🚫 **SHIP GATE BLOCKED — notes are stale**
> The artifact has been updated but the release notes still describe the original build.
> Changes since the notes were written: [summarise from session context]
>
> Update the notes with: `gh release edit <tag> --notes "..."`
>
> Or if the changes warrant it, bump to vN+1 instead of patching silently.

Do not mark the gate passed until either:
- The notes have been edited to reflect the updated artifact, **or**
- The user explicitly acknowledges the notes are intentionally unchanged and explains why

#### No release mechanism

If the user says "we don't do releases" or "we'll do it later":

> 🚫 **SHIP GATE BLOCKED**
> Builds that aren't released are invisible to everyone else. Where should this
> be published?
> If there's genuinely no release mechanism for this project, confirm that
> explicitly and we can mark it as acknowledged.

If the user asks to ship without prior gates completed:
> 🚫 **SHIP GATE BLOCKED**
> Cannot ship — [Gate N] has not been completed yet. Let's finish that first.

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
| "thanks" / "that's all" / silence | Run session-end checkpoint (Section 9) before winding down |
| "looks good" (after showing changes) | That's feedback on the diff, not commit approval — ask explicitly |

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
(SUID/containers/symlinks/systemd/SSH/cron/SELinux/packages), cross-platform
(permissions/paths/credentials).

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

### 5.7 Tone

Suggestions should be one or two sentences, woven into your normal response —
never a lecture or a checklist dump. Once per session per topic. If the user
declines or ignores a suggestion, drop it.

---

## 6. Session start

When this skill loads:

**Self-check:** Verify that `SECURITY_REFERENCE.md` and `QUALITY_REFERENCE.md`
exist in this skill's base directory (shown when the skill loaded, e.g.
"Base directory for this skill: ..."). If either is missing, warn immediately:

> ⚠️ **Skill self-check failed:** [filename] not found in [base directory].
> The security/quality gate cannot run properly without it.

Then show the gate tracker:

```
Dev Skills v2.7.1 active.

🔢 VERSION    ⬜
🔨 BUILD      ⬜
🔒 SECURITY   ⬜
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜

Commits require explicit approval. Security scan runs after every build.
```

**Important:** The version shown must match the `version` field in this file's
frontmatter. If they differ, the skill was not repackaged after a version bump —
surface this to the user.

**Updates:** Check for new versions at
https://github.com/darthrater78/claude-vibe-skills/releases

**MCP check — run at session start, every time.** Scan your context for active
MCP tool prefixes (`mcp__<server>__`). Report what's connected:

```
MCP servers active: [list names derived from tool prefixes]
To disable for this session: /mcp → toggle off any you don't need
```

Rules for the MCP check:
- **Only name servers whose `mcp__<server>__` tool prefixes are literally in your
  context.** Never infer or guess.
- Distinguish **active** (full tool definitions loaded — expensive, thousands of
  tokens per request) from **deferred** (name-only, schemas loaded on demand —
  cheap). Report deferred as a count only: "N deferred (low overhead)".
- If active servers look irrelevant to the work ahead, say so: "Consider
  disabling [name] — not needed for this task. Run `/mcp` to toggle."
- `/mcp` is the in-session command. It toggles servers on/off without leaving
  the session. This is the primary recommendation for disabling during a session.
- For permanent removal, see Section 5.4.

Then: "What are we building?"

---

## 7. Workflow status

When asked "status", "where are we", or at any natural checkpoint, show the
full gate tracker with current state.

---

## 8. Session-end checkpoint

**This fires when the session is winding down** — the user says "thanks",
"that's all", "looks good", goes silent, or otherwise signals the work is done.

Before wrapping up, check:

1. **Were source files modified in this session?** (`git status` and `git diff`
   against the session's starting commit)
2. **If yes — are all applicable gates complete?** Show the gate tracker. Any
   gate that is not ✅ or ➖ N/A is unfinished work.
3. **Specifically check for the most common miss:** code was committed and merged
   but never tagged or released. Run `git tag -l` and compare against the version
   in the project's version file(s). If the current version has no tag, flag it:

   > ⚠️ **Session-end check: version v1.2.3 has no git tag or GitHub release.**
   > The code is merged but not tagged/released. Should we finish Gates 5-6 now?

4. **If no source files were modified**, skip the gate check — the session was
   exploratory or advisory.

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
