# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [2.14.0] — 2026-09-07

### Changed
- **Extracted gate execution detail and the session-start procedure into `GATE_REFERENCE.md`**, loaded on demand. `SKILL.md` is loaded on every request, and it had grown to ~13,200 tokens — larger than all three reference files combined, inverting the tiered-loading design the skill is built on. Nearly half of it was content needed at one specific moment: gate recipes consulted when a gate runs, and a session-start procedure consulted once
- `SKILL.md` is now ~7,600 tokens per turn, down from ~13,200 (**-42%**), and below where it stood before the 2.12.0/2.13.0 additions. What remains is trigger logic that must fire unprompted: commit discipline, the pre-flight, the two tracks, gate state and re-derivation, the hook contract, shortcut detection, always-on security awareness, and cost discipline
- Section 2 gains a compact gate summary table (what each gate is *for*) and an explicit instruction to load `GATE_REFERENCE.md` before running, passing, or marking ➖ N/A on any gate — the summary is not a substitute for the pass criteria
- Section 6 is now a pointer to the session-start procedure in `GATE_REFERENCE.md`
- Cost discipline (Section 5) deliberately stays in `SKILL.md`. Gates have a hard trigger that forces the reference read; cost advice has none, so moving it behind a load would mean it silently stops applying

### Added
- `.github/workflows/release.yml` — publishes the GitHub release on tag push. Verifies the tag matches `VERSION`, builds `dev-skills.skill` from the tagged source rather than trusting the committed copy, extracts release notes from the matching `CHANGELOG.md` entry, publishes with the artifact attached, then verifies the asset actually landed — README download links point at it, so a release without it is a ship failure. Uses the runner's preinstalled `gh` rather than a third-party action, so the release path adds no supply-chain surface
- `scripts/validate.sh` verifies the README size table against actual file sizes (2KB tolerance) and requires a row per skill file. The table had drifted to roughly half the real figures — `SKILL.md` documented as ~31KB while actually 61KB — and two prior releases incremented the stale numbers instead of measuring them. Since `SKILL.md` is billed on every request, an understated figure hides a real cost
- `GATE_REFERENCE.md` added to the session-start self-check and the validator's required-files list
- `scripts/validate.sh` also verifies each bundled file matches its source, so a stale archive cannot ship old rules under a current version number

### Fixed
- Cross-references to "Section 6, step 0/1/2" now point at `GATE_REFERENCE.md`, across `SKILL.md`, `SHELL_REFERENCE.md`, and `hooks/README.md`
- The validator's banner check follows the session banner into `GATE_REFERENCE.md`

## [2.13.0] — 2026-09-07

### Added
- `hooks/gate-preflight.sh` — a `PreToolUse` hook that blocks git write operations whose required gates are not ✅ or ➖ N/A, reading `.claude/dev-skills-gates.md` for state. Covers Bash git/gh commands and GitHub MCP write tools; required gates scale with the operation (commit/push → Security; PR creation → Version/Build/Security/Docs; tag, merge, release → those plus Release). Read-only git is never blocked
- `hooks/settings.example.json` and `hooks/README.md` — install instructions, coverage table, and failure modes. Project-scoped by default; requires `jq` or `python3` and fails closed without one, per the skill's own fail-closed principle
- Gate pre-flight hook section in SKILL.md Section 2: a hook denial means a gate has not run, and the response is to run it. Explicitly forbids marking a gate ✅ that did not run, clearing a block with a false ➖ N/A, disabling the hook, or routing the operation through an unwatched path to evade a denial

### Changed
- **Presented commands go in one block** (Section 5.7). The whole sequence — `cd` through push — is a single fenced block the user copies once, with no prose interleaved between commands. Five separate blocks is five chances to miss one or run them out of order. Split only when the user must stop and inspect something first (a conflict, a build, a PR number), and say what to check
- `SHELL_REFERENCE.md` leads with the one-block rule

### Notes
- The hook covers what Claude executes, not commands presented for the user to paste or git the user runs directly. It is strongest on remote container sessions and weakest on local ones, where presenting is the default — the Section 1 rule that presenting a command counts as performing it covers the remainder

## [2.12.0] — 2026-09-07

### Added
- Durable gate state (Section 2): gate status is written to `.claude/dev-skills-gates.md` at session start and after every transition, read before every git write operation. Conversation history gets compacted; a tracker rebuilt from memory is rebuilt optimistically
- Gate re-derivation table (Section 2): when the state file is missing or stale, each gate is rebuilt from evidence (version files, build artifacts, current diff, changelog, open PRs, remote tags). Unproven is ⬜ pending, never "probably passed"
- Two tracks (Section 2): work commit (security + commit approval) versus release sequence (all six gates), so the pre-flight checklist is always answerable rather than being dropped
- Execution environment detection (Section 6, step 0): local, remote container, or Termux — determines whether Claude's working tree and the user's terminal are the same clone
- Remote container support: repo arrives pre-cloned (no clone step), shell question skipped, gate state file committed to the branch rather than gitignored, `gh`-to-GitHub-MCP command mapping table, and a session-end warning that uncommitted container work is destroyed rather than merely pending
- `SHELL_REFERENCE.md`: remote container section explaining why command formatting does not apply there
- Shortcut detection rows for "just give me the commands" and "don't worry about the gates this time"

### Changed
- **Presenting a git command now counts as performing it** (Section 1). The pre-flight fired only on tool calls, while Section 5.7 directed sessions to present commands instead of executing them — so in the intended happy path the enforcement trigger never fired. It now fires on the emitted block, with the tracker required in the same message
- **Section 5.7 default is now environment-dependent.** Local sessions present commands (same clone, cheaper). Remote containers execute directly — the user's terminal is a different machine with a different clone, so a presented block commits nothing and the container's work is lost when it is reclaimed
- **Gates apply by default to any session that modified a tracked file** (Section 1). Removed the "trivial non-code changes" exemption, which was a self-granted judgment call and the easiest path to a skipped gate. Gates now leave the workflow only via an explicit ➖ N/A for a structural reason
- **User-driven operations credit only the mechanical git step** (Section 2). Gates 1–4 describe the state of the code, not of git; a commit existing is not evidence that anything was scanned, built, or documented
- Session start writes the initial gate state file; Section 7 status reads it rather than reconstructing from memory
- Session banner shows the detected environment and which side runs git

### Fixed
- Shortcut detection pointed at "Section 9" for the session-end checkpoint, which is Section 8 (Section 9 is audit mode) — a session winding down followed the pointer into the wrong procedure

## [2.11.0] — 2026-09-05

### Added
- CI release workflow awareness: Gate 2 defers release builds to CI when a tag-triggered workflow exists, Gate 6 adds a CI-driven ship path (secrets check, tag push, CI monitoring, failure recovery), manual path preserved as fallback
- Session start CI workflow detection: scans `.github/workflows/` for release and build check workflows, suggests creating them for buildable projects without CI
- Session banner now shows CI release status line

## [2.10.2] — 2026-09-05

### Added
- Android APK signing verification in Gate 6 — debug-signed APKs are now a hard ship failure
- APK signing added to Section 4.2 dangerous patterns category list
- SECURITY_REFERENCE.md: APK signing rules, `.gitignore` enforcement for keystores, bad/good code examples (Gradle signing configs, `apksigner` verification, `key.properties` pattern)
- `.gitignore`: Android keystore and signing file patterns (`*.keystore`, `*.jks`, `*.pk8`, `*.pem`, `key.properties`, `signing.properties`)

## [2.10.1] — 2026-09-05

### Added
- User-driven operations (Section 2): if the user commits, pushes, creates a PR, or merges outside of Claude, the gates detect what's already done and continue from the next incomplete step
- MIT LICENSE file
- CONTRIBUTING.md with gate workflow summary and validation instructions
- GitHub issue templates (bug report, feature request) and PR template with gate checklist
- CI workflow (`.github/workflows/validate.yml`) — checks version consistency on push and PR
- Version consistency validation script (`scripts/validate.sh`)
- CHANGELOG.md (this file) — version history extracted from README, following Keep a Changelog format
- Shell command reference file (`SHELL_REFERENCE.md`) — cd formats, shell syntax, Termux flow, and examples
- Gate 6 post-merge cleanup: local branch deletion and `git remote prune origin`

### Changed
- Expanded .gitignore to cover OS artifacts (`.DS_Store`, `Thumbs.db`) and editor/IDE files (`.idea/`, `.vscode/`)
- SKILL.md Section 5.7 now loads shell examples on demand from `SHELL_REFERENCE.md` instead of carrying them inline (~80 lines moved out, reducing per-turn token cost)
- Self-check at session start now verifies `SHELL_REFERENCE.md` alongside the other reference files
- README version history replaced with link to CHANGELOG.md
- README "What's inside" table updated with `SHELL_REFERENCE.md` entry

### Removed
- Hardcoded `darthrater78/scripts` direct-push exception from Gate 5 — branch-based workflow now applies uniformly to all repos

## [2.10.0] — 2026-09-05

### Added
- Git repo detection at session start: detects git repos, offers to sync with origin before starting work, and warns if on the default branch
- Branch-based workflow enforcement: all work on feature/fix/release branches; committing directly to main/master is blocked
- Session-end checkpoint flags unmerged branches
- Self-governance rule: skill's own rules apply when editing the skill itself
- Shell environment detection at session start
- Remote URL verification at session start
- Sync-before-work offer at session start

### Changed
- Prose tightened: Gate 6 reduced ~20%, redundant phrasing trimmed throughout
- Cost discipline subsections renumbered: Git command presentation is now 5.7, Usage limit handoff is now 5.8

## [2.9.0] — 2026-09-05

### Changed
- Git command presentation (5.7) now defaults to presenting commands for manual execution to save tool-call token overhead
- Gates 1, 5, and 6 reference the manual command pattern

### Added
- Android APK artifact requirement in Gate 6: Android projects must include a properly named APK as a release asset

## [2.8.0] — 2026-09-04

### Added
- Git command presentation (Section 5.7): asks the user's shell environment and adapts all presented git/gh commands to that shell
- Usage limit handoff (Section 5.8): proactively offers a handoff summary when nearing usage cap

## [2.7.3] — 2026-09-03

### Added
- Android platform security checks: exported components, manifest hardening, WebView RCE, Intent validation, secure storage, network security config, certificate pinning, logging hygiene, ProGuard/R8
- Android quality patterns: main thread blocking, lifecycle leaks, RecyclerView best practices, overdraw reduction

## [2.7.2] — 2026-09-03

### Added
- Gate 3 quality review catches container dependency drift: Dockerfiles hardcoding packages instead of installing from dependency files

## [2.7.1] — 2026-09-01

### Changed
- Gate 6 (Ship) now actively scans for artifact evidence instead of passively assuming "no artifacts"

## [2.7.0] — 2026-08-31

### Changed
- Replaced automated version update check with a static releases link

### Added
- Cost discipline (Section 5.1): tool call batching, grep-before-read, git diff over full reads, minimize agent spawns, text over screenshots

## [2.5.0] — 2026-08-31

### Changed
- Removed `alwaysApply: true` — activates via trigger phrases or `/dev-skills` instead

### Added
- Gate 5 prerequisite checks: GitHub remote must exist, default branch must be pushed, `gh` CLI must be authenticated
- Session-start MCP check shows specific disable commands per active server

## [2.4.0] — 2026-08-31

### Added
- Version field in SKILL.md frontmatter — session start banner shows which version is loaded
- MCP server check at session start

## [2.3.2] — 2026-08-30

### Added
- Gate 4 (Docs) internal consistency check: cross-checks README descriptions against SKILL.md source of truth

## [2.3.1] — 2026-08-30

### Changed
- Gate 6 (Ship) enforces distributable artifact rebuild before release creation and verifies release assets

## [2.3.0] — 2026-08-30

### Changed
- Gate 5/6 restructured: Release (PR prep) and Ship (merge+tag+publish with mandatory post-verification)
- Performance trim: moved ~104 lines of detailed security/quality rules to on-demand reference files

### Added
- Hook output is never commit approval — explicit guard
- Auto mode cannot override commit discipline
- N/A gate mechanism for structurally inapplicable gates
- Session-end checkpoint catches uncommitted changes and untagged versions
- Self-check at session start verifies reference files exist
- Reference files include full rule checklists alongside code examples

## [2.2.0] — 2026-08-28

### Added
- Gate 1 requires a release notes link alongside the repository link in apps that display one

### Fixed
- Prevent hook output from being treated as commit approval

## [2.1.0] — 2026-08-28

### Added
- Gate pre-flight enforcement on every git write operation
- Source-code version string scanning (XAML, HTML, UI templates, About dialogs)
