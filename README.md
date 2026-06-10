# claude-vibe-skills

Three Claude Code skills: a cost-discipline mode, a gate-based release workflow enforcer, and a security guardrail — working together to keep vibe coding sessions cheap, safe, and properly shipped.

## Skills

| Skill | File | Description |
|---|---|---|
| `cost-saver` | [`cost-saver.skill`](skills/cost-saver.skill) | Cost-discipline mode — bounds output, gates model to Sonnet 4.6, trims MCP overhead |
| `vibe-coding-workflow` | [`vibe-coding-workflow.skill`](skills/vibe-coding-workflow.skill) | Gate-based release workflow enforcer |
| `vibe-secure-vibe-coding` | [`vibe-secure-vibe-coding.skill`](skills/vibe-secure-vibe-coding.skill) | Security & Python best-practice guardrail |

`vibe-coding-workflow` and `vibe-secure-vibe-coding` are **linked**: the workflow automatically invokes the security skill at Gate 3 after every successful build.

---

## Download

Download both `.skill` files from the [latest release](../../releases/latest) and install them (see below).

| File | Direct download |
|---|---|
| `cost-saver.skill` | [Download](../../releases/latest/download/cost-saver.skill) |
| `vibe-coding-workflow.skill` | [Download](../../releases/latest/download/vibe-coding-workflow.skill) |
| `vibe-secure-vibe-coding.skill` | [Download](../../releases/latest/download/vibe-secure-vibe-coding.skill) |

---

## Using with Claude Desktop (claude.ai chat)

Skills are natively supported in the **Claude Desktop app** (Windows and macOS). The Desktop app runs an embedded skills plugin that automatically loads `.skill` files and makes them available in every conversation.

### Install

1. Download `vibe-coding-workflow.skill` and `vibe-secure-vibe-coding.skill` from the [latest release](../../releases/latest)
2. Open Claude Desktop
3. Click **Customize** in the sidebar
4. Click **Import skill** and select each `.skill` file
5. Confirm both skills appear as enabled

After importing, **fully close and restart Claude Desktop** before the skills will be available. Claude runs in the system tray after the window is closed — make sure to quit it from the taskbar/system tray icon too, not just close the window. Once restarted, skills activate automatically based on their trigger phrases — you don't invoke them manually. Just talk to Claude normally and they load when relevant (e.g. mention "vibe coding" or "audit my project").

> **Both skills must be installed together.** `vibe-coding-workflow` calls `vibe-secure-vibe-coding` by name at Gate 3 — installing only one will cause Gate 3 to fail.

### How it works

Skills are ZIP archives containing a `SKILL.md` with a name, trigger description, and instructions. Claude Desktop reads the trigger description and loads the skill into context whenever the conversation matches. The skill then guides Claude's behavior for that session.

---

## Using with Claude Code (local CLI)

**Claude Code** is the terminal CLI (`claude`) that runs in your local environment. It shares the same skills registry as Claude Desktop — skills you install in the Desktop app are automatically available in Claude Code sessions too.

### Install

Install both `.skill` files via Claude Desktop as described above. They will immediately be available in all Claude Code sessions on the same machine.

### How it works in Claude Code

In Claude Code, skills appear in the system context at session start. When your conversation matches a skill's trigger, Claude loads it and follows the instructions. You'll see the skill name referenced in tool call outputs (e.g. `Launching skill: vibe-coding-workflow`).

Skills work the same way in Claude Code as in Desktop chat — the only difference is your working directory is your local codebase, so the workflow and security gates operate on real files and git state.

### Using a skill directly from a file

In Claude Code you can also reference a `.skill` file directly without installing it:

```bash
claude "@path/to/vibe-coding-workflow.skill build and release this project"
```

This loads the skill for that session only, without permanently installing it.

---

## Ad hoc use — drop into any chat or code session

You don't need to install a skill to use it. In both **Claude Desktop chat** and **Claude Code**, you can drop a `.skill` file directly into the session and it loads immediately for that conversation only.

### Claude Desktop — drag into chat

Drag one or both `.skill` files into the chat input box, then type your prompt alongside them:

```
[drag vibe-coding-workflow.skill]  [drag vibe-secure-vibe-coding.skill]
build and release this project
```

Claude reads the skill files as context and follows their instructions for the rest of the session. Nothing is permanently installed — the skills only apply to that conversation.

### Claude Code — @ reference in your prompt

Use the `@` file syntax to reference a `.skill` file inline:

```bash
claude "@./vibe-coding-workflow.skill @./vibe-secure-vibe-coding.skill build and release this project"
```

Or interactively, type `@` followed by the file path in the Claude Code prompt:

```
> @/path/to/vibe-coding-workflow.skill let's ship this
```

Again, session-only — nothing is installed.

### When to use ad hoc vs installed

| | Ad hoc (drop in) | Installed |
|---|---|---|
| Persists across sessions | No | Yes |
| Auto-triggers from phrases | No — must be in the prompt | Yes |
| Requires install step | No | Yes |
| Good for | Trying a skill, one-off use, sharing with a teammate | Daily use, automatic enforcement |

---

## Using without Claude Desktop (browser claude.ai)

Skills are not natively supported in the **browser version** of claude.ai. As a workaround, you can paste the skill content directly into your conversation:

1. Download the `.skill` file
2. Open it as a ZIP archive (rename to `.zip` or use any zip tool)
3. Copy the contents of `SKILL.md`
4. Paste it at the start of your Claude conversation with a note like:

   > "Please follow these instructions for this session: [paste SKILL.md content]"

This gives Claude the same instructions for that session, though it won't persist across conversations and won't auto-trigger — you'll need to paste it each time.

---

## `cost-saver`

Cost-discipline mode. Keeps sessions cheap without losing quality by targeting the five biggest cost drivers: session length, model choice, effort level, output length, and context bloat.

### Triggers

Claude loads this skill automatically when you:

- Mention cost, token usage, or expensive sessions
- Say "keep it cheap", "save tokens", or similar
- Ask to disable or trim MCP servers, connectors, or unused tools
- Ask for a handoff summary to start a fresh session
- Ask which model or effort level a task needs
- Invoke `/cost-saver`

### What it does

**Bounds its own output.** Leads with the answer, skips preamble and recaps, shows diffs instead of whole files, reads only the files a task requires.

**Model gating — Sonnet 4.6 ceiling.** At session start, checks the active model. If it's above Sonnet (Opus, Fable), immediately flags it:

> "This session is running on [model], which exceeds the Sonnet 4.6 cost ceiling. Run `/model sonnet` to switch down, or tell me you want to stay on [model] for this task."

Won't proceed with substantial work until you respond. Can also write `"model": "sonnet"` to `~/.claude/settings.json` so every new session defaults to Sonnet.

**Phase-transition handoffs.** When work shifts phase (explore → implement → test → done), offers a fresh-session prompt:

> "Good point to start a fresh session — this one's carrying N messages of history. Want a handoff summary?"

If yes, produces a structured summary under 30 lines (goal / state / key files / decisions / next step) designed to replace the long history with a cheap restart.

**MCP overhead reporting.** Distinguishes between:
- **Active tools** (full schemas loaded): expensive — often thousands of tokens per server per request. Named and flagged for removal.
- **Deferred tools** (name-only, loaded on demand): low overhead — reported as a count only, no action needed.

For active servers not used in the current work, tells you exactly how to remove them (`claude mcp remove`, `disabledMcpjsonServers` in settings, Desktop UI toggle, or `claude --strict-mcp-config` for a zero-MCP session).

**Effort fit.** Recommends `/effort high` or `xhigh` only for architecture, root-cause debugging, or security review. Flags medium as sufficient for routine edits.

**End-of-task token estimate.** When a task wraps up, closes with 3–5 lines: per-request overhead × turns, files read vs. used, model multiplier, and the single highest-impact change for next time.

```
Token impact (rough estimate):
✅ Saved ~40k — read only 2 relevant files instead of exploring the package
✅ Saved ~25k/turn — session restarted at the implement phase
⚠️ ~30k/turn overhead — 5 connected MCP servers, none used this session
Biggest win next time: disable unused connectors (would cut ~60% of this session's tokens)
```

---

## `vibe-coding-workflow`

Enforces a mandatory 5-gate release process for every vibe coding session. Gates must be cleared in order — none can be silently skipped.

```
🔢 VERSION  →  🔨 BUILD  →  🔒 SECURITY  →  📦 RELEASE  →  🚀 PUSH
```

### Triggers

Claude loads this skill automatically when you:

- Mention "vibe coding" or start a new coding session
- Ask to build, compile, package, or bundle
- Ask to push, deploy, release, or publish
- Say "ship it", "done", or "ready to merge"
- Try to skip a step ("just push it", "skip the version bump", "we can do security later")

### The five gates

#### Gate 1 — Version 🔢

No build starts until a version is decided and written to the version file (`package.json`, `pyproject.toml`, `Cargo.toml`, `VERSION`, etc.). Must follow semver (`MAJOR.MINOR.PATCH`).

If no version is set:
```
🚫 VERSION GATE BLOCKED
No version has been set for this build. What version should this be?
  Patch bump (bug fixes):      x.x.N+1
  Minor bump (new features):   x.N+1.0
  Major bump (breaking):       N+1.0.0
Current version: [shown]
```

#### Gate 2 — Build 🔨

Runs the project's build command after version is confirmed. Build failure stops everything — no gate advances until the build is clean.

#### Gate 3 — Security 🔒

After every successful build, `vibe-secure-vibe-coding` is invoked automatically for a full project audit. This gate is mandatory — it cannot be deferred.

- **Critical and High findings** are fixed immediately before proceeding
- **Medium and Low findings** are surfaced for the user to decide on

Gate passes only when Critical = 0 and High = 0.

#### Gate 4 — Release 📦

Every security-cleared build must be formally published before the session ends. Claude tags the commit and creates a GitHub release (or equivalent) with notes and artifacts. "We'll release later" is blocked.

#### Gate 5 — Push 🚀

Claude will **never push** without an explicit typed confirmation. "yeah" or "ok" is not enough — the user must type something unambiguous like "push" or "confirm push".

### Handling impatience

| What you say | What happens |
|---|---|
| "just push it" | Gates checked, push gate surfaced, confirmation required |
| "skip the version bump" | Hard stop — version is required |
| "we can do security later" | Security gate runs now, in this session |
| "just ship it" | All open gates surfaced in order |
| "done" / "we're done" | Release and push gates checked |

---

## `vibe-secure-vibe-coding`

Security and Python best-practice guardrail. Operates in two modes: **inline review** (as you write code) and **project audit** (full codebase scan).

### Triggers

Claude loads this skill when you:

- Write or review any code
- Add packages or dependencies
- Build APIs, handle user input, store credentials
- Work with databases, files, or network operations
- Say "just make it work", "hardcode it for now", "don't worry about security", "I'll fix it later"
- Say "audit my project", "scan this codebase", "security review", "check my code"

### What it checks

**Security patterns**

| Category | Examples caught |
|---|---|
| Secrets & credentials | Hardcoded API keys, tokens, passwords; `.env` in git |
| Dangerous execution | `eval()`, `exec()`, `shell=True` with user input, `os.system()` |
| Input handling | Missing validation, type/length/format checks |
| Database | SQL string concatenation (use parameterized queries) |
| Network | Disabled TLS verification, SSRF-prone redirects |
| File system | Path traversal, overly permissive file modes |
| Serialization | `pickle`/`marshal` on untrusted data |
| JavaScript | Prototype pollution, `innerHTML` XSS, open redirects |

**Python best practices**

| Pattern | Rule |
|---|---|
| Type hints | Every function signature should be annotated |
| Context managers | `with` for all file/DB/network/lock resources |
| `pathlib` | Use `Path` instead of string concatenation for paths |
| `secrets` module | Use for tokens, nonces, session IDs — not `random` |
| `assert` misuse | Never use `assert` for validation — stripped by `-O` |
| Bare `except` | Always catch specific exception types |
| Logging | Never log passwords, tokens, or PII |
| Hashing | SHA-256+ for integrity; bcrypt/argon2 for passwords — never MD5/SHA1 |
| Mutable defaults | `def f(x=None)` not `def f(x=[])` |
| Pinned deps | Exact versions in `requirements.txt`; run `pip audit` in CI |
| Static analysis | `bandit` in pre-commit or CI |

### Audit mode

Say "audit my project" or "scan this codebase" to trigger a full scan. Output format:

```
Security & Code Quality Audit — <project>
════════════════════════════════════════════════════════════

🚨 CRITICAL  — must fix before any production use
⚠️  HIGH      — fix before shipping
📝 MEDIUM    — fix soon, low exploitation risk
💡 LOW       — best-practice improvements

────────────────────────────────────────────────────────────
🚨 CRITICAL (N)
  <file>:<line>  <issue>
                 Fix: <one-line fix>
...

────────────────────────────────────────────────────────────
Summary
  Files scanned:   N
  Total findings:  N  (Critical: N  High: N  Medium: N  Low: N)
```

### Severity guide

| Severity | Examples |
|---|---|
| 🚨 Critical | Hardcoded secrets, SQL injection, `shell=True` with user input, disabled TLS, `pickle` on untrusted data |
| ⚠️ High | Path traversal, missing auth, `debug=True` in prod, MD5/SHA1 passwords, bare `random` for tokens |
| 📝 Medium | Bare `except`, no type hints, mutable defaults, `assert` for validation, unpinned deps |
| 💡 Low | Missing `encoding=` on `open()`, string path concatenation (non-traversal), missing `bandit` in CI |

### "Just make it work" handling

When asked to skip security, the skill doesn't lecture — it offers the safe version first (usually just as fast), and if the user insists, marks the shortcut visibly:

```python
# SECURITY RISK: hardcoded credentials — move to env var before any real use
# TODO: os.environ['DB_PASSWORD']
DB_PASSWORD = "hunter2"
```

---

## How they work together

```
vibe-coding-workflow
       │
       │  Gate 3 — Security
       └──invokes──► vibe-secure-vibe-coding
                            │
                            └── full project audit
                                fix Critical + High
                                surface Medium + Low
                                return findings report
                            │
       ◄──────────────────────
       │
       │  Gate 3 passes (0 Critical, 0 High)
       └──► Gate 4 — Release
```

`vibe-secure-vibe-coding` also runs independently whenever you're writing code — it doesn't require the workflow to be active.

---

## Version

`v1.2.0`
