## Handoff: cost-discipline efficiency pass (target 2.30.0)

**Goal:** Cut tool-call round trips (especially single git commands) and trim
routine output, without losing information the user needs.

**Current state:** Analysis only — no skill files edited. v2.29.0 is shipped
(tag on d6b5265, PR #54). Local `.claude/dev-skills-gates.md` has an
uncommitted SHIP ✅ update for 2.29.0 (gitignored, fine to leave).

**Gate status (for 2.30.0):**
```
🔢 VERSION    ⬜
🔨 BUILD      ⬜
🔒 SECURITY   ⬜
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜
```

**Mode:** none chosen — the skill was not loaded this session. The next session asks.

**Diagnosis — where the turns go:**
- The "chain a step's commands" rule exists only in `AUTO_MODE.md` "Round trips"
  (~L207–235), which is loaded only in semi-autonomous mode. Session start, the
  gates, the session-end checkpoint and manual-mode remote containers never see it.
- `SKILL.md` §5.1 "Batch tool calls" (~L679) covers parallel tool calls only,
  not `&&`-chaining of shell commands.
- `SESSION_START.md` steps 0–7 prescribe ~8–10 separate calls: upstream
  `ls-remote` (L44), `git remote -v` (L211), `gh repo view` + `gh api user`
  (L229–230), `git fetch`, `git remote show origin` (L286), workflow listing,
  `ls-remote --tags` + `git log -- VERSION` (L339–340).
- `SKILL.md` §8 session-end checkpoint: `git status`, `git diff`,
  `ls-remote --tags`, `docker ps` and the tracker read are separate steps (4–5 calls).
- Verbosity: the full 9-line banner and the 6-line tracker are shown with every
  command block. The token estimate has no length cap.

**Proposed changes:**
1. Move the chaining rule into `SKILL.md` §5.1 so it applies in every mode.
   Keep the "don't chain across a stop" boundary (commit approval, tag block,
   a failed gate). `AUTO_MODE.md` points to §5.1 instead of holding its own copy.
2. New `skills/dev-skills/scripts/session-probe.sh`: one read-only call that
   prints `key=value` lines (repo root, origin, fork status, default branch,
   ahead/behind, workflows, untagged versions, upstream skill version, whether
   `gh` is installed). `SESSION_START.md` steps read their answers from its
   output. About 10 calls → 1.
3. A matching evidence probe for the §8 checkpoint and the AUTO_MODE
   checkpoint 2 report: status, diff stat, untagged versions, test containers,
   PR/CI state. 4–5 calls → 1.
4. Shorter output:
   - Full tracker only at session start, on a gate change, on "status", and in
     handoffs. Otherwise one line: `🔢✅ 🔨✅ 🔒⏳ 📄⬜ 📦⬜ 🚀⬜`.
   - Banner shows only rows that need attention (⚠️/❌/🚨); fold the all-clear
     rows into one line like `Checks: ✅ origin, CI, releases, skill version`.
   - Token estimate capped at 3 lines; drop the MCP line when nothing changed
     since session start.

**Decisions made / constraints:**
- Priority if split: #1 and #2 save the most turns.
- Self-governance: skill edits go through all six gates. Bump the version in
  SKILL.md frontmatter, the SESSION_START banner and the release-notes URL, and
  repackage `skills/dev-skills.skill` via `scripts/build-skill.sh`.
- Probe scripts must be read-only and must not hide failures (print an explicit
  `key=ERROR` rather than skipping a key).
- Open question to verify first: does `hooks/gate-preflight.sh` check every
  git command in a chained line (`a && b && c`), or only the first? If only the
  first, a chain could get past it. Fix the hook before relying on chaining.

**Key files:**
- `skills/dev-skills/SKILL.md` — §5.1 (~L667), §5.7 (~L795), §8 (~L940)
- `skills/dev-skills/AUTO_MODE.md` — Round trips (~L207)
- `skills/dev-skills/SESSION_START.md` — steps 1–7 (~L199–380), banner (~L395)
- `hooks/gate-preflight.sh` — how it parses chained commands
- `scripts/validate.sh`, `scripts/build-skill.sh` — packaging and validation

**Shell environment:** bash, local Linux (Debian 13)

**Next step:** Read `hooks/gate-preflight.sh` to confirm how it handles chained
git commands, then start 2.30.0 at the VERSION gate with change #1.
