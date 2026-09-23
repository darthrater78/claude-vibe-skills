# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [2.30.0] — 2026-09-22

**Fewer round trips and shorter routine output, in every mode.** Every tool call
resends the whole conversation, and the skill was spending them one command at
a time: about ten separate reads at session start, four or five at the
session-end checkpoint. The rule for chaining commands lived only in
`AUTO_MODE.md`, which manual sessions never load.

### Added
- **One-call session-start probe (`SESSION_START.md`, top of "Session
  start").** A single read-only Bash block answers the self-check, the version
  check, the environment signals and steps 1, 1a, 4, 6 and 7 as `key=value`
  lines. Every key always prints. A failed command prints `key=ERROR <message>`
  instead of being skipped, and pipelines run under `pipefail`, so a failure
  mid-pipe is never hidden. Credentials embedded in the `origin` URL are
  stripped before printing, so a token never reaches the transcript.
  The probe moves to the repo root itself, so it answers correctly from any
  subdirectory. It passes the `origin` URL to `gh repo view` explicitly, so a
  fork resolves to the fork and not to its parent.
- **One-call session-end evidence (`SKILL.md` §8).** Status, diff, unmerged
  commits, the current version's tag, the state file and test containers are
  read together, `;`-separated so one failure does not hide the rest.

### Changed
- **The chaining rule moved to `SKILL.md` §5.1 and applies in every mode.**
  `&&` a step's commands, and do not chain across a stop (commit approval, the
  tag block, an unpassed gate, a failure that changes what comes next).
  `AUTO_MODE.md` now points to it instead of holding its own copy. The
  pre-flight hook already scans every command in a chain, so chaining does not
  get past it.
- **Compact tracker.** The full six rows show at session start, on a gate
  change, on "status" and in handoffs. Otherwise the tracker is one line
  (`🔢✅ 🔨✅ 🔒⏳ 📄⬜ 📦⬜ 🚀⬜ · track · mode`). Blocking gates are still named
  in full, and the pre-tag report is never compacted.
- **Banner folds all-clear rows** into one `Checks: ✅ …` line. Only rows that
  need attention print on their own.
- **Token impact estimate capped** at a header and three lines. The MCP line
  appears only when connections changed since session start.
- **`scripts/validate.sh` checks the probe against the self-check.** Both
  name the reference files that must exist, written separately, so validation
  fails if they drift. It also drops an unused variable that shellcheck
  flagged (SC2034).
- **Session-start ordering stated once.** The probe is the first action, the
  version check is the first thing reported, and step 0 is the first decision.
  Before, the version check and step 0 each claimed "before anything else".
- README size table: `SKILL.md` ~53KB (was ~51KB), `SESSION_START.md` ~28KB
  (was ~25KB).

### Fixed
- **`scripts/validate.sh` could fail at random with "missing from
  dev-skills.skill".** Under `set -o pipefail` it piped `unzip -l` straight
  into `grep -q`. When grep exited on its first match, unzip took SIGPIPE and
  the pipeline reported a bundled file as missing. The listing is now read
  once and grepped from a variable.

## [2.29.0] — 2026-09-22

**You choose the operating mode at the start of every session, and forks
always target the fork.** Two gaps closed. The manual vs semi-autonomous
choice was documented but never enforced: session start wrote `Mode: manual`
and the banner mentioned "say auto mode" as a hint, so nobody was ever asked
and every session silently ran manual. Forks had no handling at all. A clone
whose `origin` was the upstream repo went unnoticed, and in a fork `gh pr
create` defaults its base to the *parent* repo, so a bare PR command opened
upstream.

### Added
- **Mandatory mode question at session start (`SESSION_START.md`, "Mode
  choice").** Manual vs semi-autonomous is asked every session, neutrally
  (manual listed first, no recommendation), in the same `AskUserQuestion` call
  as the shell, sync and branch questions. Until it is answered, Claude makes
  no edits, runs or presents no git writes, and does not ask "What are we
  building?".
- **`Mode: unchosen` state, and no silent default.** The gate file starts with
  `Mode: unchosen`. A missing row, `unchosen`, or any other value means no
  mode, never manual. A resumed session, or one that finds a committed gate
  file, asks again.
- **Fork check (`SESSION_START.md`, step 1a; `SKILL.md` §5.8; `SHELL_REFERENCE.md` "Forks").**
  `gh repo view` against `origin` decides between four cases. If `origin` is
  the upstream parent of the user's fork, it is repointed with
  `git remote set-url origin <fork>` before any work starts. No `upstream`
  remote is added, and an existing one is never pushed to. Every `gh` write
  carries `--repo <fork>`. Anything upstream, the user does on GitHub
  directly. The result is recorded as an `Origin:` row in the gate file.
- **Hook: mode check.** `gate-preflight.sh` denies every classified git write
  unless the first `Mode:` row reads `manual` or `semi-autonomous`.
- **Hook: fork targeting.** Using the `Origin:` row, the hook denies `gh
  pr`/`gh release` writes whose `--repo`/`-R` names another repo, MCP writes
  with a different `owner`/`repo`, and, in a fork, a `gh` write with no
  `--repo` or a `git push` that doesn't name `origin`.
- **Hook: user-only ref operations.** Tag creation, tag pushes, and every ref
  deletion (`git push --delete`/`-d`/`:<ref>`/`--mirror`, `gh pr merge
  --delete-branch`, `gh api -X DELETE …/git/refs`, MCP tag/delete tools) are
  now denied outright, in both modes. Previously the hook *allowed* `git tag`
  once the gates passed, although SKILL.md §5.8 says Claude never runs it.
  Tag creation is checked against an allowlist of read-only flags (`-l`,
  `--sort`, `--contains`, …), so an unknown option fails closed.

### Changed
- **Cost pass on the always-loaded tier: SKILL.md 66KB → 51KB, SESSION_START.md
  30KB → 25KB.** About 18KB, roughly 4.5k tokens, less context carried by every
  session. No rule was removed and the hook and scripts are untouched. What
  went:
  - text that duplicated an on-demand file (the pre-tag report's contents are
    in `AUTO_MODE.md`, §5.8's mechanics are in `SHELL_REFERENCE.md`, the
    Dependabot enablement is in `SECURITY_GATE.md`, and the MCP disable
    options now live only in `SESSION_START.md`'s MCP check)
  - §6 restating `SESSION_START.md`, which is read right after it
  - narration around rules that were already stated
  - sample output §8 didn't need

### Fixed
- **Contradictions about who pushes the tag in semi-autonomous mode.**
  `SKILL.md` §1 said the mode "lifts the tag-push carve-out", `AUTO_MODE.md`
  said "the tag push and its follow-on actions are Claude's", the session
  banner said auto mode would "run … the tag push", and two README shortcut
  rows said the same. All of them contradicted §5.8 and the Operating modes
  section, which keep the tag push and ref deletions with the user in both
  modes. All now agree.
- **Hook: `git -C <dir>` / `git -c k=v` slipped past every pattern.** The
  classifier matched `git push`/`git commit` literally, so `git -C x push`
  was never inspected. Those options are now normalized away first. The same
  pass found that a chained command with two `gh` calls was only checked on
  its first `--repo`, and that `GH_REPO=` was ignored. All three are fixed,
  covered by a 52-case test matrix that master's hook fails 28 of.
- The Gate 5 remote check (`GATE_REFERENCE.md`) now requires `--repo <fork>`
  on `gh pr create` in a fork.
- The committed gate file's v2.28.0 SHIP row was left ⏳. The tag is
  confirmed on 6e4919f (PR #52 merge commit) with the release asset attached,
  so it is folded into this release as ✅.

## [2.28.0] — 2026-09-19

**Nothing reaches the release track with an open finding.** Severity used to
decide whether a finding could be carried: Critical and High blocked, Medium
and Low were "surfaced for the user to accept" and, in practice, written onto
the tracker and carried. Severity now decides only how urgent the conversation
is. A finding of any severity blocks Gate 5 and Gate 6 until it reaches a
terminal state.

This came out of the skill failing on its own repo. A Medium — no
`.github/dependabot.yml`, so nothing keeping the SHA-pinned `actions/checkout`
current — was recorded at 2.26.0, carried into 2.27.0 marked "open,
pre-existing", and was not put to the user as a decision until after v2.27.0
had been tagged and published. Every gate read ✅ the whole way. Section 4.1
exists to prevent exactly that dependency-drift pattern, and the gate machinery
let it happen anyway, twice.

### Changed
- **Gate 3 finding lifecycle (`GATE_REFERENCE.md`, `SKILL.md` §4.7).** A finding
  leaves the open state in exactly three ways and no others:
  - **fixed** — the code changed and the fix was re-verified against the
    *current* diff
  - **waived** — the user explicitly waived *that specific finding*, with a
    reason and date recorded on the tracker
  - **withdrawn** — the finding was wrong, and why it was wrong is stated

  Anything else is open. "Pre-existing", "unrelated to this change", "only a
  Medium", "we'll get it next release" are not terminal states — they are the
  sentences that carried the finding above across two releases.
- **"Pre-existing" is demoted to a provenance note.** It records where a finding
  came from; it says nothing about what has to happen before the next tag.
  A finding that predates the change is still a finding.
- **Only the user waives, one finding at a time.** Claude never waives its own
  finding, and a blanket "ignore Mediums" or "stop flagging that" is category
  suppression, not a waiver — the skill asks which specific finding instead. A
  waiver covers the finding as it stands and re-opens if its context changes:
  the code is edited, the severity rises, the named dependency gets an advisory.
- **Findings are surfaced when discovered, not in the ship summary.** A finding
  raised after the tag is raised past every point where the user could have
  acted on it.
- **Quality findings follow the same lifecycle.** "Known technical debt" is a
  description, not a terminal state; if it is genuinely accepted, it is a
  waiver and the user records it.
- **Gate 3's pass line and the combined output report `0 open`**, and the
  Dependabot recommendation is now raised as the Medium finding it always was
  rather than an optional suggestion.
- `SKILL.md` §4.7 is the new lifecycle section; the former §4.7 security summary
  is now §4.8.
- **Gate 3 moved into its own `SECURITY_GATE.md` (~12KB)**, leaving
  `GATE_REFERENCE.md` at ~22KB for gates 1, 2, 4 and 5. This was not planned:
  the lifecycle rules pushed `GATE_REFERENCE.md` to 33KB and the per-file
  ceiling added in 2.27.0 failed the build. Its message offers two responses —
  extract a section that has its own load trigger, or raise the ceiling on the
  record — and Gate 3 has the clearest trigger of the five and already pulled
  two further references of its own. Gates 1, 2, 4 and 5 no longer carry it.
  The ceiling working on the release that added it is the intended behavior.

- **The gate state file ships inside the release PR** (`GATE_REFERENCE.md`
  Gate 5 step 3, `SHIP_REFERENCE.md` step 7, `SKILL.md` §2). It is staged with
  the release commit carrying gates 1–5 ✅ and 🚀 SHIP ⏳ — ⏳ being the honest
  state, since the tag does not exist yet and no commit preceding it can claim
  otherwise. The post-tag SHIP ✅ line folds into the next release's PR, under
  the same close-as-you-go rule from 2.25.0 that governs every other section of
  the file: the next sequence's VERSION step is the step that absorbs it.

  **Tracker-only pull requests are now forbidden.** The previous rule said to
  commit the SHIP ✅ record "on its own (a tracker-only commit)", and four
  consecutive releases each trailed one — #45, #47, #50 and #52. The effect was
  that every tagged commit's own state file was wrong: it read SHIP ⬜ for a
  version that had shipped, and the correction landed in a PR merged after the
  fact. Between the tag and the next release the durable record is the tag, the
  GitHub release and the changelog entry, which is what re-derivation reads
  anyway and what actually proves a ship.

### Added
- **The hook enforces it** (`hooks/gate-preflight.sh`). The tracker's SECURITY
  row carries the open count on its **first line** — `✅ 0 open — 0 Critical,
  0 High` — because that is the line the hook reads, per the row-format rule
  from 2.25.0. A ✅ whose first line does not say `0 open` is an illegal state
  and release operations are denied: it asserts the gate passed while the row
  itself still counts findings nobody resolved.

  Scoped to the release track on purpose. Work commits stay possible with
  findings open, because a finding has to be recordable before it can be
  resolved. Verified against all three states: the exact 2.26.0 tracker text
  now denies `git tag`, a `0 open` row allows it, and a work commit with an
  open Medium is unaffected.
- Three shortcut-detection rows (`SKILL.md` §3) for "that finding is
  pre-existing", "ignore the Mediums", and "we'll fix it next release" — each
  routes to the lifecycle rather than to compliance.
- `.github/dependabot.yml` (github-actions, weekly, grouped). This repo has no
  package manifests of any kind, so the actions-only shape
  `WORKFLOW_REFERENCE.md` warns about is correct here; the file says so and
  says to add an entry the moment that stops being true.

- **Dependabot enablement is now a procedure, not a menu path**
  (`SECURITY_GATE.md`, "Enabling Dependabot alerts"). Alerts and security
  updates are repository settings Claude cannot flip, and since this release an
  open finding blocks the release track — so the user needs steps they can
  follow, not "Settings → Code security". The skill now hands over the direct
  `settings/security_analysis` URL, the order the toggles must go in
  (dependency graph first — mandatory on private repos), how to verify from the
  Security tab, and the three cases that make it fail: an org-owned repo whose
  toggle is greyed out and needs an org owner, a private repo with no
  dependency graph, and "we have no dependencies".

  That last one was wrong in this repo's own notes. **The dependency graph
  covers GitHub Actions workflows**, so a repo with no package manifest still
  gets real advisory coverage for the actions it pins. A `.github/workflows/`
  directory is something to watch. Claude must also re-check the endpoint
  rather than marking the finding fixed on an unverified "I turned it on".

### Fixed
- **A fail-open path in the enforcement hook** (`hooks/gate-preflight.sh`),
  found by shellcheck (SC2164). `cd "$CWD" 2>/dev/null` was unchecked, so a
  directory that exists but cannot be entered left the hook resolving `ROOT`
  from wherever it happened to be — reading the wrong gate state file, or
  none, and then evaluating gates against it. The hook's header has always
  said it fails closed; this path did not. It now denies, with the directory
  named. Note the fix SC2164 suggests, `|| exit`, would exit 0 — which in this
  hook means **allow** — so the denial is written explicitly.
- **The bundle is now a reproducible build** (`scripts/build-skill.sh`).
  `zipfile.writestr` stamped every entry with the build time, so two builds of
  identical sources produced different archive bytes: v2.27.0's released asset
  and its own committed copy hashed differently with all 21 entries identical.
  Entry metadata is now fixed at the zip epoch, so comparing a released asset
  against the committed one is a real check rather than a meaningless one. This
  also retires an inaccurate claim — the v2.26.0 tracker recorded that the
  asset's "sha256 matches the API digest", which it could not have.
- **Dead code in `scripts/validate.sh`** (SC2034): `readme_version` was
  assigned and never read. Also a useless `cat` (SC2002). All three scripts now
  pass shellcheck 0.9.0 with zero findings.

### Notes
- Behavior-tightening, released as MINOR in line with 2.24.0's version guard.
  It is worth knowing that a repo carrying open findings will find its next
  release blocked where 2.27.0 would have let it through. That is the point.
- `SKILL.md` is now 63KB against its 64KB ceiling. The lifecycle rule has to be
  resident — it fires unprompted or not at all — but this release spends most
  of the headroom 2.27.0's ceiling allowed, and the next addition to the
  per-turn tier will have to extract something first. Which is what the ceiling
  is for.

## [2.27.0] — 2026-09-19

A cost release. No rule changes, no gate changes, no behavior removed: the
reference set is split so a file loads only the moment it covers, semi-autonomous
mode learns to stop spending round trips it does not need, and
`scripts/validate.sh` gains a per-file size ceiling so the per-turn tier cannot
drift upward unnoticed again.

The problem it fixes is structural, not cosmetic. Tiered loading has always been
this skill's design, but the on-demand tier was two monolithic files. A reference
file is read in full, so `GATE_REFERENCE.md` at 85KB charged every gate for the
session-start procedure, the semi-autonomous execution detail, and the entire
ship path — regardless of which gate was running or whether the session was even
in that mode. `WORKFLOW_REFERENCE.md` at 97KB charged every Docker project for
the Android, Python, Node.js, Windows, Linux, Home Assistant and script
templates. Splitting along the boundaries those files already had costs nothing
and changes nothing about what is enforced.

### Changed
- **`GATE_REFERENCE.md` split four ways, along its existing section
  boundaries.** Same content, same triggers, read in the sizes the moment
  actually needs:
  - `SESSION_START.md` (~25KB) — the session-start procedure, read once, at
    session start, and never again. `SKILL.md` Section 6 now points here.
  - `GATE_REFERENCE.md` (~29KB) — gates 1 through 5.
  - `SHIP_REFERENCE.md` (~22KB) — Gate 6 only. It is the largest of the six and
    fires once, at the end of a release; gates 1–5 have no use for the
    CI-driven path, the manual path, or the wrong-commit tag recovery, and no
    longer pay for them.
  - `AUTO_MODE.md` (~13KB) — semi-autonomous execution, loaded only when the
    user has opted in. In 2.26.0 this rode along in every read of the gate
    reference, including in manual sessions that will never use it.
- **The eight workflow templates are now eight files**
  (`WORKFLOW_DOCKER.md`, `WORKFLOW_WINDOWS.md`, `WORKFLOW_LINUX.md`,
  `WORKFLOW_HOMEASSISTANT.md`, `WORKFLOW_SCRIPTS.md`, `WORKFLOW_ANDROID.md`,
  `WORKFLOW_PYTHON.md`, `WORKFLOW_NODEJS.md`). The templates are mutually
  exclusive and the environment detection that picks one already runs, so a
  project now loads the one it matches instead of all eight.
  `WORKFLOW_REFERENCE.md` keeps everything that applies to *every* template —
  the selection and audit procedures, linting, best practices, dev releases,
  Cosign, Dependabot — and drops from ~97KB to ~40KB. Its Step 1 detection
  table now names files rather than in-page anchors.
- **All cross-references updated** across `SKILL.md`, `SHELL_REFERENCE.md`,
  `WORKFLOW_REFERENCE.md`, `hooks/README.md`, and the split files themselves:
  "session start, step N" now points at `SESSION_START.md`, "Gate 6" at
  `SHIP_REFERENCE.md`, and "Semi-autonomous mode — execution" at `AUTO_MODE.md`.

### Added
- **Round-trip discipline for semi-autonomous mode** (`AUTO_MODE.md`, "Round
  trips"). 2.26.0 named this mode's cost honestly — a chain of executed git
  commands resends the conversation on every call where a pasted block costs
  nothing — and then left it unmanaged. The mode now says how to spend less:
  chain a step's commands into one invocation (`git add -A && git commit -m … &&
  git push -u origin <branch>`) rather than one call each, and gather
  checkpoint 2's evidence (`git log`, `gh pr view`, `gh run list`, the gate
  file) in one call rather than four. With an explicit boundary: **do not chain
  across a stop.** Anything the user must see or decide between two commands —
  the commit approval, the tag block, a failed command whose output changes what
  comes next — is a boundary the chain does not cross. This removes round trips,
  never checks.
- **Batched reads at session start** (`SESSION_START.md`). Steps 1, 4, 5 and 7
  are independent read-only commands; they now chain into one invocation. Steps
  2 and 3 are questions for the user and stay separate. Nothing is skipped — a
  step that is skipped is still a step that was skipped.
- **Per-file size ceilings in `scripts/validate.sh`.** `SKILL.md` is capped at
  64KB, `WORKFLOW_REFERENCE.md` at 44KB, every other skill file at 32KB. The
  failure message names the two legitimate responses: extract a section that has
  its own load trigger, or raise the ceiling in the same commit as the growth
  that needs it.

  This exists because the 2.14.0 extraction was silently undone. That release
  cut `SKILL.md` from ~61KB to 37KB to restore the tiered design; across the ten
  releases since, it accreted back to 62KB at roughly 2.5KB per release, and
  `GATE_REFERENCE.md` doubled from 43KB to 87KB. No single release was wrong. No
  check noticed the trend. A ceiling is not a cap on what the skill may say — it
  is what makes the next addition a decision rather than a drift.
- **`scripts/validate.sh` and `scripts/build-skill.sh` now share one file
  list**, declared once at the top of each. The validator previously repeated
  the same ten filenames in three places, which is how a 21-file bundle would
  have gone wrong.

### Unchanged
No gate, rule, approval, or enforcement behavior changed in this release. The
pre-flight, the six gates, commit approval, the tag and ref-deletion carve-out,
the two tracks, the gate state file, and `hooks/gate-preflight.sh` are all
byte-for-byte as they were in 2.26.0. Three reductions considered for this
release were **rejected** for contradicting deliberate earlier decisions, and are
recorded here so they are not proposed again:
- Moving §2's gate-state mechanics out of `SKILL.md` — 2.14.0 names "gate state
  and re-derivation" as content that deliberately stays in the per-turn tier,
  all three of the gate-file discipline rules landed in 2.25.0 from a real
  postmortem, and `hooks/gate-preflight.sh` cites the re-derivation table's
  location in its deny message.
- De-duplicating the mode contract across §1, §3, §5.8 and §8 — 2.26.0 states
  the ref-write rules in all five places on purpose, and the rationale copies
  are already one or two sentences that defer to `SHELL_REFERENCE.md`.
- Moving §4.1 dependency auditing behind a load — 2.14.0 names "always-on
  security awareness" as staying resident, and 2.16.1 documents three cost
  behaviors that died precisely because their trigger was softer than a gate.

## [2.26.0] — 2026-09-19

Adds an opt-in **semi-autonomous mode**: Claude runs the git commands itself
— commits, pushes, the PR, the merge, watching CI, verification — instead of
handing over command blocks. Two checkpoints survive: commit approval,
unchanged and required for every commit, and the tag, which is still the
user's to push and now arrives with a full report of every action taken
since that approval. The tag push and ref deletions stay with the user in
both modes; a mode cannot grant credentials the remote denies. Manual mode
is untouched and remains the default. Also: native Linux sessions now get
offered Remote Control. No breaking changes.

### Added
- **Semi-autonomous mode (`SKILL.md`, "Operating modes").** Opt-in per session, in
  the user's own words ("auto mode", "semi-autonomous mode", "take it from here").
  It changes who runs most of the commands, not what has to be true before
  they run: Claude executes git in every environment — commits, branch
  pushes, the PR, the merge, watching CI, the post-ship verification, the
  tracker commits — and the between-step confirmations collapse into two
  checkpoints. What it does *not* change is the §5.8 carve-out: the tag push
  and every ref deletion still go to the user, in both modes, because the
  `403` that carve-out exists for comes from the remote and not from this
  skill. A merge in this mode therefore carries no `--delete-branch`.
  Manual mode's behavior is unchanged in every particular.
- **Checkpoint 1 — the commit approval, now carrying the release.** Gate 1's
  version-bump confirmation and Gate 5's release-notes approval fold into it,
  presented together with the diff summary, the bump and its reasoning, the
  gate line, and the full release notes. That approval covers the sequence it
  describes and nothing else — if more commits land or the notes change, it is
  presented again. Work commits get a short form with no version, notes, or
  ship plan, and no second checkpoint, because they never tag.
- **Checkpoint 2 — a full pre-tag report, handed over with the tag block.**
  The user still runs the tag, in this mode as in manual; what changes is that
  the block no longer arrives bare. Claude reports *every* action taken since
  the commit approval:
  commits with SHAs and messages, every push and whether any rewrote history,
  the PR and what happened on it, every CI run with its conclusion, the merge
  commit, each gate with the evidence that passed it, the version guard's
  result, and — the part that matters most — anything that failed, was
  retried, or went differently than what the user approved at the commit. It
  is reconstructed from evidence (`git log`, `gh pr view`, `gh run list`, the
  gate file), not from memory, and a gap that cannot be closed is stated
  rather than omitted. The tag block goes below the report in the same message,
  with the clone path asked for first if it is not known. This replaces Gate
  6's pre-ship "type ship" — it is a longer stop than that one was, not a
  shorter one, because the user is reading an account of work they did not
  watch happen and then running the tag themselves. Afterwards Claude confirms
  the tag on the remote and what it points at rather than taking "done" at face
  value. Formats for both checkpoints are in `GATE_REFERENCE.md`,
  "Semi-autonomous mode — execution".
- **Native Linux local sessions get offered Remote Control, in either mode**
  (`GATE_REFERENCE.md`, session start, step 0). One line, once per session:
  `claude --rc` (or `/rc` in an open session) keeps the terminal session as it
  is while also publishing it to claude.ai/code and the Claude desktop and
  mobile apps, so the same session is reachable from either surface with
  execution still local. The interactive form is offered deliberately —
  `claude remote-control` is server mode and leaves no local prompt, which is
  the opposite of the point. "Native Linux" is checked, not assumed: Termux
  and WSL both report `Linux` from `uname -s`, and neither qualifies. It
  changes nothing about gates, tracks, or the mode.
- **A `Mode:` row in `.claude/dev-skills-gates.md`.** The mode is session
  state, so it lives where session state lives rather than in conversation
  history that compaction can drop. Written at session start as `manual`,
  rewritten when the mode changes, read back with the rest of the file: a
  session that finds no `Mode:` row is manual. Semi-autonomous mode never carries
  into a new session — a handoff summary's `Mode:` line records what the last
  session ran in without opting the next one in.
- **Stop conditions, written down as a table** (`GATE_REFERENCE.md`). A
  failed operation falls back to manual behavior for that operation while the
  session stays semi-autonomous: a blocked gate, a `403` on a push or tag push, a
  `src refspec` failure, CI failing on the PR, a failed release run, a
  Critical or High finding, or any decision with more than one defensible
  answer. The mode is semi-autonomous by design — it removes ceremony, not
  judgment.

### Changed
- **Tag and ref-deletion blocks no longer carry a `cd`, and no longer trigger
  a clone-path question.** The path was the one line in those blocks the user
  could not copy as given — Claude does not know it in a remote container,
  which is exactly where the block is always handed over — so it asked, which
  put a question in front of the one command someone releasing a tag already
  knows how to run. Now the reminder goes in the prose above the block ("run
  this from your local clone of the repo") and the block itself is copyable
  verbatim. With the `cd` gone, nothing in those blocks varies by shell
  either: they are plain single-line `git` commands, so remote container
  sessions that skip the shell question at session start never need to come
  back and ask it. `SHELL_REFERENCE.md`'s section on this is rewritten around
  the new rule, and the general "always start with `cd`" rule for presented
  blocks now names its two exceptions — commands Claude executes itself, and
  these. Blocks on a local session, where Claude knows the real path, are
  unchanged.
- **Section 1 now names both "auto modes" and refuses both.** The existing
  rule covered the Claude Code harness's auto mode; the skill now has one of
  its own, and the bullet distinguishes them and states that neither relaxes
  commit approval. Section 1's step 6 gained the semi-autonomous branch: the
  approval in step 5 is what licenses Claude to execute the sequence it just
  described, and nothing beyond it.
- **Ref-write rules are stated as mode-independent, in all five places that
  describe them.** `SKILL.md` §5.8, `SHELL_REFERENCE.md`, `GATE_REFERENCE.md`
  Gate 6 and session start, and `WORKFLOW_REFERENCE.md`'s dev-release section
  now all say the same thing: creating a tag ref and deleting any ref go to
  the user in every environment and in both modes. A mode describes how much
  ceremony the user wants; it says nothing about what credentials the remote
  will honour, and the `403` comes from the remote. Deleting a release,
  force-pushing, and rewriting history keep their own explicit approval on
  top; re-pushing a tag is a delete plus a create, so both halves go to the
  user.
- **Gate 6's safety checks are explicitly not ceremony.** The merge
  confirmation (state reads `MERGED`, CI green *on the merge commit*) and the
  version guard run in semi-autonomous mode too — the guard as a check Claude
  performs before `git tag` rather than a `grep` chained into a block the
  user pastes. They existed to stop a tag landing on the previous commit, not
  because a human was about to paste something.
- **Pre-release tags follow the same rule** (`WORKFLOW_REFERENCE.md`, "Dev
  releases"): the user pushes them in both modes, with the pre-tag report above
  the block in this one, and either way a `-dev`/`-alpha`/`-beta`/`-rc` tag is
  a release sequence with all six gates, because it still publishes an
  artifact. The only thing it relaxes is the branch.
- **The enforcement hook needs no change and covers more.** In semi-autonomous
  mode the commits, pushes, PR and merge arrive as tool calls
  `hooks/gate-preflight.sh` inspects rather than as blocks the user pastes. The
  tag push and ref deletions stay in the uncovered half in both modes, since
  they are exactly the operations handed to the user's own terminal.
  `hooks/README.md` says so.
- **Session banner and status output name the mode**, alongside the track, so
  it is visible on every tracker display rather than only when it changed.
  Handoff summaries (§5.6/§5.9) carry a `Mode:` line for the same reason.
- **The cost trade is stated once, not repeatedly** (§5.8): a pasted block
  costs nothing while a chain of executed git commands resends the
  conversation each round trip, so semi-autonomous mode buys autonomy with
  tokens. Mention it when the user opts in, then drop it. `SKILL.md` grew
  ~7KB for the mode contract, which is a real per-turn cost and is reflected in the
  README's size table; the execution detail went into `GATE_REFERENCE.md`,
  which loads on demand.

## [2.25.0] — 2026-09-18

Distilled from a postmortem on a real dev-skills session: ten specific
failure modes the gate workflow itself produced, plus new handling for
building Docker in a web container and a pass over release-workflow
efficiency. No breaking changes.

### Added
- **A web/remote container that can't actually build Docker gets a real
  choice, not a silent guess.** Scoped to projects with a Docker build
  signal. Session start now measures `docker info` (daemon reachability)
  instead of `which docker` (binary presence only) — the two look identical
  until something tries to build, which is exactly how this was found: the
  CLI was present, the daemon wasn't. When the daemon isn't reachable in a
  web container, Claude now says so plainly and offers either a work commit
  now (finish Gate 2 later on a machine with a working daemon) or the
  existing CI-only BUILD path. Any Docker container started for Gate 2
  testing — the handoff offer or the new never-run-step check below — must
  be stopped and removed once its purpose is served; Section 8's session-end
  checklist now checks for orphaned test containers as a backstop.
- **Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).**
  `SKILL.md` §1.1 has the type list (`feat`/`fix`/`docs`/`chore`/etc.) and the
  breaking-change (`!`, `BREAKING CHANGE:`) convention. Gate 1 (VERSION) now
  reads the commit types since the last tag as a signal for the bump —
  `feat`→MINOR, `fix`-only→PATCH, any breaking-change marker→MAJOR — and
  confirms with the user rather than asking cold. This is a different axis
  from `CHANGELOG.md`'s Keep a Changelog format, which stays hand-written.
- **The out-of-date-skill warning is now the loudest thing this skill does.**
  A behind copy gets a bracketed, warning-lined block as the literal first
  line of the first message — nothing above it, never folded into the
  banner. If the user continues anyway, a compact `⚠️ outdated` tag now
  stays on every later gate-tracker display for the rest of the session
  instead of disappearing after the first warning.
- **A release-workflow step that's never actually run gets proven before a
  tag depends on it.** New Gate 2 rule: before a tag push is about to
  exercise a release step with no track record in this repo (first registry
  login, first signing step, an ancestor-fallback path), copy it out of
  `release.yml` and dry-run it locally against the built artifact if the
  tooling allows. Keep a short "unproven" note for anything that can't be
  exercised this way and carry it forward release to release until it
  actually runs once for real.
- **Three standing checks when fixing a Critical or High in Gate 3:**
  reproduce the failure before writing the fix and look for sibling paths
  into the same bad state once it's fixed; flag any existing test whose
  assertions encode the insecure behavior as correct (a green test isn't
  proof — one was found treating a locked resource as "no key," not "access
  denied"); confirm every new regression test actually fails with the fix
  reverted before trusting it as coverage.
- **A build/test run only counts as Gate 2 evidence if the tree didn't move
  under it.** `git status --porcelain` and `git rev-parse HEAD` are now
  captured before and after the run; a mismatch means the gate is still
  pending, not a pass to keep. Two ~9-minute suite runs were previously
  thrown away this way in one session with nothing enforcing the check.
- **The release-track rule moved from a one-off gate-file note into
  `SKILL.md` itself.** A merge to the default branch with no version bump,
  artifact, tag, or publish behind it is a work commit, explicitly, with
  RELEASE/SHIP marked ➖ N/A and the reason stated — not release-track by
  default because it touched `main`. When a repo's own convention here is
  genuinely unclear, the skill now asks once at session start with
  `AskUserQuestion` instead of surfacing it as a mid-PR aside.
- **Workflow review checklist gained an item** for a release job re-running a
  check (lint, shellcheck, the full suite) its own gate job already required
  CI to have passed for that exact commit — the redundant-check pattern this
  release found and fixed in two templates (below).

### Fixed
- **`hooks/gate-preflight.sh` read only a gate row's first line**, for both
  the ✅/➖ status check and the BUILD `handoff` annotation check. A status
  symbol or annotation that wrapped onto a continuation line — which happens
  routinely, since gate rows carry explanatory text — read as absent and
  blocked real work over formatting, not missing work. The hook now reads
  the full row (the gate's line plus every continuation line up to the next
  gate or a blank line) for both checks. Reproduced against a synthetic gate
  file: the old `grep | head -1` logic missed a `handoff` annotation on a
  wrapped line; the fixed `gate_block()` awk helper finds it, and still
  correctly denies when the annotation is genuinely absent.
- **Proceeding without acting on the local-artifact-handoff offer now
  counts as declining it**, recorded with the user's own words, instead of
  leaving BUILD waiting on an explicit decline that was never going to come.
- **The SHIP gate's own record can no longer stay uncommitted.** Both the
  CI-driven and manual Gate 6 paths now end with committing and pushing the
  gate-state file's SHIP ✅ update — found happening live in this repo: the
  v2.24.0 record sat uncommitted in the working tree while the release had
  actually shipped.
- **Gate-file rows stay short and stay current.** New `SKILL.md` §2 rules:
  keep a row to a few lines (the long write-up belongs in the commit message
  or `CHANGELOG.md`, which already persist it — not duplicated in the
  tracker), and close or delete a section as part of the VERSION/SHIP step
  that absorbs its work, not a separate cleanup pass. One session's tracker
  went from 399 lines back to 681 in four hours without this.
- **Two release templates (Linux, script-collection) re-ran shellcheck in
  the release job** even though their own gate job already required CI's
  identical check to have passed for that commit — pure re-proof, removed.
- **The Node.js release template was stale**: it said npm didn't support
  OIDC trusted publishing and required an `NPM_TOKEN` secret. npm trusted
  publishing has been GA since July 2025 (verified against npm's current
  docs, not recalled). The template now uses OIDC by default (`id-token:
  write`, no token to manage) with the token approach as an explicit
  fallback for registries or configurations without trusted-publisher
  access.

## [2.24.0] — 2026-09-17

### Added
- **Every release workflow template now verifies the tag matches the version
  declared in the tagged commit, not just that the commit is merged and
  green.** Found when a stable tag pushed before its release PR merged
  landed on the previous version's commit — already on the default branch,
  already CI-green — and passed both existing checks while publishing the
  old code under the new tag. `WORKFLOW_REFERENCE.md` gets the check (with a
  per-ecosystem extractor: `package.json`, `pyproject.toml`, a manifest, a
  `VERSION` file, a `.csproj`, `build.gradle*`) in all eight release
  templates, an exemption note for tag-derived/computed versioning
  (`setuptools-scm`, `git describe`-based `versionName`), and a
  checkout-less API-fetch form for gate jobs that never check out the repo.
  The workflow review checklist and audit's Critical severity list now flag
  a release workflow with no tag/version match check the same way they
  already flag a missing tag-on-default-branch check — it's the same class
  of failure: something gets published that was never the release.
- **Gate 6 no longer hands over the tag-push block on trust that the merge
  landed.** `GATE_REFERENCE.md` now requires confirming the PR state reads
  `MERGED` and that CI passed for that exact commit *before* describing or
  presenting the tag commands — describing the step in words is the
  correct behavior until both hold. The tag block itself now carries a
  version guard chained with `&&` (never a bare `exit`, which would close
  the user's interactive shell instead of just stopping the chain), reusing
  the same extractor the release workflow uses rather than a second
  hand-rolled check that can drift from it. An unqualified "pushed" is
  no longer treated as verified: SHIP confirms the tag's target commit,
  not just that a tag by that name exists on the remote.
- **A recovery runbook for a tag published on the wrong commit**, under
  Gate 6: cancel the run immediately (a warm-cache image build can reach
  its push step in well under a minute), record what already went out
  before cleaning anything up, delete the GitHub release with approval,
  hand the tag deletion to the user (ref writes stay theirs), land the
  real release and re-tag, and note that floating tags self-correct on the
  next build while a registry version already pushed under the wrong tag
  usually can't be deleted with the credentials a session has
  (`delete:packages` is a scope session tokens typically lack).

## [2.23.0] — 2026-09-17

### Fixed
- **`WORKFLOW_REFERENCE.md` claimed Dependabot security updates "need no
  configuration."** False: security updates (advisory-driven PRs) are a
  repository setting — Settings → Code security → Dependabot alerts and
  Dependabot security updates — completely separate from `dependabot.yml`,
  which only controls scheduled version updates. A repo can run a correct
  `dependabot.yml` for months with alerts disabled and get zero CVE coverage
  while its "Bump X" PR queue looks like security maintenance. `SKILL.md`
  §4.1's "Automate the watch" bullet had the same gap — it now names both
  halves and requires Claude to check `GET /repos/{owner}/{repo}/dependabot/alerts`
  and surface a `403` (alerts disabled) as a Gate 3 finding.

### Added
- **`hooks/gate-preflight.sh` now enforces the local-artifact-handoff offer,
  not just the prose in Gate 2.** For a repo with a Docker/.exe/.apk build
  signal (`Dockerfile`, `.csproj`/`.sln`, or an Android Gradle project), the
  hook denies a BUILD gate marked ✅ unless the tracker line also carries a
  `handoff` annotation (`handoff offered, user tried it` /
  `... user declined to try it` / `handoff n/a (remote container / Termux
  session)`). The hook cannot see the conversation where the offer happens,
  only the tracker file, so this closes the gap where a build could be marked
  passed while the mandatory offer from 2.22.0 was silently skipped.
- **"Absence of a verdict is not a verdict."** The re-derivation table's BUILD
  row, and a new paragraph in `SKILL.md` §2, call out that a check list with
  zero runs (not red — *empty*) is ⬜, never a pass. An empty result reads
  like success in a way a failure never does.
- **Gate 2 (BUILD) gets a third state: CI-only.** Previously only ➖ N/A (no
  build system) or a hard block existed, with no way to represent "a real
  build system exists but this environment structurally cannot run it" (no
  SDK, a blocked registry, wrong host OS). CI-only is permitted only when the
  obstacle is stated concretely, the CI verdict covers the exact merged tree,
  and everything checkable locally was checked.
- **Workflow review checklist now verifies SHA pins resolve to their claimed
  tag**, not just that a SHA is present. A pin matching no tag is silently
  broken (the job never runs); a pin matching a *different* tag than its
  comment is a suppressed upgrade, since Dependabot reads the comment, not
  the SHA, to decide what to offer next.
- **Note on driving Dependabot PRs from an agent.** `@dependabot rebase`
  posted via the GitHub API or an MCP tool does not fire — the mention
  arrives with separators inserted and Dependabot's listener never matches
  it, silently. `update_pull_request_branch` ("Update branch") is the
  working equivalent.
- **The `minor-and-patch` Dependabot group's "low risk" comment is corrected**
  to "one review, not one risk class" — a minor library bump can still
  require a major toolchain change (observed: a minor `androidx` bump
  demanding an AGP major bump and a `compileSdk` change). `SKILL.md` §4.1
  gets the same clarification.
- **"Default branch" is now defined as whatever the remote reports, never an
  assumed `main`/`master`.** Both the release-sequence trigger in `SKILL.md`
  §2 and the branch-check step in `GATE_REFERENCE.md` now say to confirm the
  actual default branch (`git remote show origin`, or `gh repo view --json
  defaultBranchRef`) rather than pattern-match a name — some repos use an
  unconventional default, and some have no separate long-lived branch at all.

All findings in this release trace to a single real session (clearing a
Dependabot PR queue on an Android project) rather than being inferred from
reading the skill.

## [2.22.0] — 2026-09-16

### Added
- **Gate 2 (BUILD) now requires a mandatory local-artifact-handoff offer for
  compiled outputs, before the gate passes.** A green smoke test proves the
  code runs; it never proved a human could actually get their hands on the
  build. For Docker images, Windows `.exe`, and Android `.apk`, Claude must
  now offer — every time the build changes, not just once per session — a
  concrete way to try the real artifact: a local folder path for `.exe`/`.apk`
  downloads, or `docker load`/`docker run` instructions for images. The offer
  can be declined per build, but never skipped silently.
  Scope is environment-gated: the full offer (including Docker) applies only
  on a local session with a Linux host shell; a local Windows host gets the
  narrowed `.exe`/`.apk` offer with no Docker instructions; remote container
  (cloud) and Termux (mobile) sessions are unaffected — they already ship
  through the existing CI-driven release path (Gate 6).

## [2.21.1] — 2026-09-16

### Fixed
- **`release.yml`'s "Build artifact" step hand-rolled its own `zip` with a
  hardcoded file list, independent of `scripts/build-skill.sh`.** Adding
  `SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`, `SECURITY_ANDROID.md`, and
  `QUALITY_ANDROID.md` in 2.21.0 updated `build-skill.sh` and `validate.sh`
  but missed this second, independent copy — so the v2.21.0 GitHub release
  published a `dev-skills.skill` missing all four new files (6 of 10, caught
  by post-ship verification, not before). The workflow now calls `bash
  scripts/build-skill.sh` instead of reimplementing it — the exact "CI
  reimplements the build instead of calling the project's own script"
  antipattern this project's own Structure best practices warn against.
  v2.21.0's release asset is superseded by this version; the source at that
  tag was always correct, only the packaging step was broken.

## [2.21.0] — 2026-09-16

### Added
- **Platform-specific security and quality patterns split into their own
  files.** `SECURITY_REFERENCE.md` and `QUALITY_REFERENCE.md` previously
  loaded every Windows, Linux, and Android pattern on every Gate 3 scan and
  audit, regardless of the project's actual platform. Windows, Linux, and
  Android content now lives in `SECURITY_WINDOWS.md`, `SECURITY_LINUX.md`,
  `SECURITY_ANDROID.md`, and `QUALITY_ANDROID.md` — loaded conditionally,
  alongside the (now cross-platform-only) core files, once project
  environment detection (`WORKFLOW_REFERENCE.md` Step 1) identifies the
  platform. A Linux-only project now loads roughly 40% less of
  `SECURITY_REFERENCE.md`'s former content. `SKILL.md`, `GATE_REFERENCE.md`,
  `build-skill.sh`, and `validate.sh` all updated to know about the four new
  files.
- **Release workflows now gate on CI success, not just branch ancestry.**
  Every generated release template (Docker, Windows, Linux, Home Assistant,
  Scripts, Android, Python package, Node.js) previously only checked that the
  tag was on the default branch — which proves the commit was merged, not
  that CI ever ran against it or passed. Each template's `release` job now
  `needs: gate`, a new job that checks both: the existing branch-ancestry
  check, and a new poll of `ci.yml`'s run status for the exact commit SHA
  (waiting up to 30 minutes for an in-flight run, since tagging right after
  pushing is normal). A tag on a commit whose CI went red no longer publishes
  the same way a green one does.
- **`WORKFLOW_REFERENCE.md` gains a "Workflow linting" section** with a
  ready-to-use `lint-workflows.yml` template (`actionlint` over
  `.github/workflows/**`, binary pinned by version and verified by published
  checksum since it isn't a GitHub Action). Offered alongside Dependabot
  whenever a workflow is created or audited — it's what lets a CI build
  check safely exclude `.github/workflows/**` from its own trigger paths.
- **Script-injection guidance added to Template best practices.** Templates
  and the workflow audit checklist now flag `${{ github.ref_name }}` (or any
  branch name, PR title, or other attacker-influenceable value) interpolated
  directly into a `run:` script instead of passed through `env:`.
- **Reliability notes:** `branches: ['**']` instead of a bare `push:` on CI
  triggers (a bare `push:` also matches the tag push that fires the release
  workflow, running the suite twice), `paths-ignore` for docs-only changes
  paired with a `workflow_dispatch` escape hatch for the release gate's edge
  case, and `DEBIAN_FRONTEND=noninteractive` around `apt-get install` on
  `ubuntu-latest` jobs.
- **Docker workflow gains a floating-tag safety note** — how to guard a
  hand-rolled `:dev`/`:latest`-style tag against ever moving backward
  (compare against every existing tag of its own kind, not just the commit
  being built), for projects that add a prerelease channel beyond this
  template's default `docker/metadata-action` semver tagging.
- **Workflow audit checklist** updated to flag all of the above during
  `audit my workflows`.

## [2.20.0] — 2026-09-16

### Added
- **Session start now checks the skill's own currency.** `GATE_REFERENCE.md`
  gains a mandatory version check, run every session before anything else:
  the installed `SKILL.md` version is compared against the latest tag on
  `darthrater78/claude-vibe-skills`, read directly via `git ls-remote`
  (never a cached clone, never a number from memory). An outdated copy stops
  the session with a warning above the banner and an explicit
  "continue on the outdated copy, or update first?" — the session does not
  proceed to "What are we building?" until that's answered. A network-check
  failure (offline, sandboxed) is a single skip notice, not a hard block.
  `SKILL.md` Section 6 and the session banner reference the new check.

## [2.19.0] — 2026-09-16

### Added
- **Dependency currency and CVE freedom is now a stated requirement.**
  `SKILL.md` Section 4.1 opens with it: every dependency must be a current
  release with no known CVEs, direct and transitive. Previously the section
  only listed things to "check" when adopting a package, with no statement of
  what the check had to conclude.
- **Dependencies are audited for the life of the project, not only when added.**
  Section 4.1 splits into "when adding a package" and "for the life of the
  project". The manifest is re-audited on every security gate — the pinned
  version stands still while advisories accumulate against it, which is how a
  project that passed its gates still meets a wall of Dependabot PRs.
- **"Never write a version number from memory."** A model pins the version it
  saw in training, which is months or years stale the day it is written, so a
  brand-new project is born outdated. Section 4.1 and `SECURITY_REFERENCE.md`
  now require looking the current release up, with the one-line command per
  ecosystem (`npm view`, `pip index versions`, `cargo search`, `go list
  -m -versions`, `dotnet package search`).
- **Gate 3 audits the dependency tree as a mandatory step.**
  `GATE_REFERENCE.md` gains an audit-tool table covering Node, Python, Rust,
  Go, .NET, Java and `osv-scanner`, a required finding format (advisory ID,
  package, installed version, fixed version), and an explicit rule that a
  missing audit tool is reported rather than passed in silence.
- **`SECURITY_REFERENCE.md` dependency section**, replacing "Python — pinned
  dependencies": pinned / current / CVE-free as three separate properties with
  worked bad-and-good examples, the audit command per ecosystem, and how to fix
  a transitive advisory by moving the parent forward rather than pinning the
  child behind the resolver's back.
- **Dependabot recommendation covers package ecosystems.**
  `WORKFLOW_REFERENCE.md`'s config template previously watched only
  `github-actions`, so a repo could follow it exactly and still have nothing
  watching its application packages. It now carries a second `updates:` entry
  with grouped minor/patch bumps, ungrouped majors, and a note that security
  PRs only arrive for ecosystems that have an entry.

### Changed
- **A Critical or High advisory in any dependency is a Gate 3 hard stop**,
  alongside hardcoded secrets and SQL injection. Dependency risk was previously
  representable only as 📝 Medium "unpinned deps", so a pinned-but-vulnerable
  package passed the security gate clean. Where no upstream fix exists, the gate
  does not pass silently — the advisory and the options are surfaced for the
  user to decide on the record.
- **The security scan reports code and dependency findings separately**, so a
  clean scan of hand-written code can no longer stand in for an unaudited
  manifest.
- Medium severity now also covers dependencies carrying a Medium/Low advisory,
  and dependencies several majors behind current with no advisory yet.

## [2.18.0] — 2026-09-11

### Added
- **`WORKFLOW_REFERENCE.md`.** New on-demand reference for GitHub Actions
  workflows, loaded when a CI workflow is missing (Gate 6 detection) or the
  user asks for workflow help. Two procedures:
  - **Workflow audit (Section 9.1)** — a severity-graded review of existing
    `.github/workflows/*.yml` against a 14-item checklist, plus CI/local-dev
    drift detection.
  - **Guided workflow creation (Section 9.2)** — detects the project's
    environment, asks every configuration question in one turn, and
    generates a template the user reviews before anything is written.
  - Eight environment templates (each with CI + release workflow): Docker,
    Windows, Android, Linux, Home Assistant, scripts, Python, and Node.js —
    all with SHA-pinned actions, least-privilege `permissions:`,
    `persist-credentials: false`, concurrency groups, and timeouts.
  - Pre-release/dev builds (`v1.0.0-dev.1` tags from feature branches),
    optional Cosign image signing, and a Dependabot config template for
    keeping pinned action SHAs current.
- New trigger phrases in `SKILL.md`'s frontmatter: "create a workflow",
  "set up CI", "add GitHub Actions", "add CI/CD", "audit my workflows",
  "review my CI".

## [2.17.0] — 2026-09-10

### Added
- **Subagent model delegation (Section 5.4).** New cost-discipline rule: when
  spawning subagents via the Agent tool, use the cheapest model tier that fits
  the task — Haiku for lookups and searches, Sonnet for code work and review,
  Opus/Fable only when the main session is already approved above the Sonnet
  ceiling. Includes a tier table and four rules, the hardest being that a
  subagent can never run on a more expensive model than the main session is
  approved for.

### Changed
- Existing sections 5.4–5.8 renumbered to 5.5–5.9. All ~25 cross-references
  across SKILL.md, GATE_REFERENCE.md, and SHELL_REFERENCE.md updated.

## [2.16.1] — 2026-09-08

### Fixed
- **Three cost-discipline behaviors were unreachable and had never fired once.**
  Sections 5.5, 5.6 and 5.8 were each written as an *offer* gated on a condition
  the model could not observe, so in practice none of them ever ran. Reported by
  a user who had never seen any of the three.
  - **§5.5 phase transitions** triggered on "when work shifts phase" — a pure
    judgment call, which loses every time to the system prompt's bias toward
    continuing without stopping. Replaced with three observable events: a
    release sequence reaching ✅/➖ across all six gates, the user opening work
    unrelated to the current tracker with no release in flight, or the
    conversation having been compacted. The offer is now a one-line statement of
    the observation and its reason, not an open question that is easy to drop.
  - **§5.6 token estimate** triggered on "when a task wraps up" and then handed
    back an escape hatch — *"Skip for trivial exchanges."* Re-anchored to the
    session-end checkpoint (§8), which already has a firm trigger, and added
    there as step 6. The only skip condition is now the one §1 already uses for
    gates: the session modified no tracked file. "This felt like a small task"
    is explicitly not a skip condition.
  - **§5.8 usage-limit handoff** watched for a context budget below ~2M. On
    Claude Code for web that figure starts at 15M every session and effectively
    never falls, so the check was structurally dead. Re-anchored to signals that
    do occur: an explicit system notice about overage or rate limits, the user
    saying they are low, or a compacted conversation. A visible low number still
    counts, but its absence is no longer a reason to stay silent.
- **The session banner's release-notes link pointed at the previous version.**
  `GATE_REFERENCE.md` hardcoded the v2.16.0 release URL, which Gate 1 requires to
  track the current version.

### Changed
- **The handoff format is defined once.** §5.5 and §5.8 carried near-identical
  copies; §5.8's was the better of the two (it included gate status and shell
  environment). The richer version is now canonical in §5.5 and referenced from
  §5.8.
- **README restructured for readability.** Added a table of contents and a
  "What's new" section; moved "The six gates" from position 10 to position 5,
  ahead of the enforcement mechanics that depend on it; split "Two tracks" into
  its own section; added a worked example of a shortcut interception and a gate
  state file; folded deep rationale into three `<details>` blocks; moved release
  CI internals into a "For maintainers" section. No behavioral claims changed
  except the cost-discipline corrections above.

## [2.16.0] — 2026-09-08

### Added
- **Windows security coverage brought to parity with Linux and Android.** A
  prior Gate 3 pass on a Windows desktop app checked a URL-opening call for
  injection, found none, and marked it safe — missing that the app's
  `requireAdministrator` manifest meant the browser it launched came up
  elevated. The pass was faithful to the reference; the reference had no
  Windows privilege section to check against. The gap was wider than that one
  rule: `SECURITY_REFERENCE.md` advertised eight Windows checks in its
  flag-on-sight list but carried worked examples for only three (PowerShell
  injection, UNC paths, credential storage), so the other five were checks in
  name only — Gate 3 loads that file to pattern-match against. Six new
  sections, each with the bad/good pair the rest of the file uses:
  - **Windows — UAC and process elevation.** `requireAdministrator` hands the
    admin token to *every* process the app launches, so an ordinary "open this
    link" call opens an elevated browser. Covers the `asInvoker` default, the
    `explorer.exe` re-launch that drops back to the shell's integrity level,
    validating the scheme before handing anything to `explorer.exe` (it will
    run a file path or an `.exe` just as readily), and elevating a single
    helper with `Verb = "runas"` instead of the whole app
  - **Windows — DLL search-order hijacking.** `SetDllDirectory("")` plus
    absolute loads; `DefaultDllImportSearchPaths` for P/Invoke
  - **Windows — registry security.** `HKLM` keys with default ACLs as a
    code-execution path into an elevated process, and validating values read
    back before acting on them
  - **Windows — service configuration.** The unquoted `binPath=` privilege
    escalation, and virtual accounts over `LocalSystem`
  - **Windows — code signing and execution policy.** Signing with a timestamp
    rather than reaching for `Set-ExecutionPolicy Bypass`, and verifying a
    signature before shipping
  - **Windows — reserved names and path limits.** Device names with or without
    an extension, trailing dots and spaces stripped by Win32, case-insensitive
    path comparison
- **New flag-on-sight rule: elevation.** The Windows rule list in
  `SECURITY_REFERENCE.md` had no entry for the app manifest at all. It now
  leads with one, so the check fires as code is written and not only when
  Gate 3 runs. The services rule also gained the `binPath=` quoting
  requirement
- `SKILL.md` §4.2 now names UAC elevation in the Windows category list, which
  previously ran PowerShell → UNC → DLL → registry → services → signing →
  reserved names with the privilege model missing from the middle
- **`scripts/build-skill.sh`.** `validate.sh` compares the `.skill` bundle
  against its source, but nothing in the repo rebuilt that bundle and
  `CONTRIBUTING.md` never mentioned it — so a contributor who followed the
  documented workflow could not get a green run no matter how correct their
  changes were. The script rebuilds the bundle deterministically with LF entries
  at the archive root, and CONTRIBUTING now names it as step one of validation
- **Git Bash spawn stalls are now a documented, non-blocking condition.**
  `SHELL_REFERENCE.md` gains "Git Bash stalls on spawn-heavy scripts". Git Bash
  emulates `fork()` rather than calling it, and `validate.sh` spawns a few
  hundred subprocesses across its per-file loops — enough that the script
  stalls partway through, with no error and no exit, at a position that moves
  between runs. Every command it stalls on runs fine individually, so the
  natural readings are both wrong: it is not a defect in the script, and a
  partial run is not a pass. The section gives the recognition shape (partial
  output, `137`/`124` on kill, non-reproducible position), prescribes running
  the script in split invocations under `timeout`, and requires that the split
  cover every section and be recorded as split in the gate state file. It also
  closes the tempting exit: deferring the check to CI converts a pre-commit
  gate into a post-commit report, which is precisely what Gate 2 exists to
  prevent. WSL is offered as the durable fix, not as a precondition — a split
  run is a complete local verification on its own
- `GATE_REFERENCE.md` Gate 2 now points at that section, so the guidance is
  found from where the stall actually happens rather than only by someone
  already reading the shell reference

### Changed
- **§5.7 moved out of the every-turn path.** `SKILL.md` is resent on every
  request, and §5.7 "Git command presentation" had grown to 6.6KB — the largest
  subsection in the file, and larger than the six gates it supports. Almost all
  of it (the 403 rationale, the one-block rule, the `cd` rule, the never-bare-
  `git push` rule, remote verification) is only needed at the moment a command
  block is written, which is exactly when `SHELL_REFERENCE.md` is loaded
  anyway. What stays in `SKILL.md` is the routing decision, the tag and
  ref-deletion carve-out, and the rule that 🚀 SHIP is not ✅ until the tag is
  confirmed on the remote. `SKILL.md` drops 40KB → 36KB, about 1k tokens off
  every request; `SHELL_REFERENCE.md` grows 5KB → 9KB on demand. No rule was
  removed
- `GATE_REFERENCE.md` step 0 quoted §5.7 by its pre-2.15.2 name ("Tag pushes
  are the one exception") with an unclosed quotation mark. Now quotes the
  current heading

### Fixed
- **A CRLF checkout broke both the build check and the pre-flight hook.** The
  repo had no `.gitattributes`, so `core.autocrlf=true` gave every Windows
  clone a CRLF working tree. Two things broke, and both failed in ways that
  pointed somewhere else:
  - `scripts/validate.sh` compares the `.skill` bundle (always LF) against
    the working tree byte for byte. On Windows all five files reported
    "differs — rebuild the bundle" no matter how freshly the bundle had been
    built, so Gate 2 was unrunnable on the platform most likely to be editing
    the skill, and every green run this repo has had came from a Linux container
  - `hooks/gate-preflight.sh` is invoked directly by `settings.example.json`,
    so a CRLF shebang makes it die with `bad interpreter`. The repo shipped a
    gate-enforcement hook that silently failed to load on Windows

  `GATE_REFERENCE.md` Gate 6 already prescribes the fix for other projects —
  "fix it in the repo, not with a `dos2unix` step" — so the repo now follows
  its own rule with `* text=auto eol=lf`. `validate.sh` keeps its strict
  byte-exact comparison and gains a second pass on the failure path only, to
  say "this is a CRLF checkout" instead of misreporting a current bundle as
  stale

## [2.15.2] — 2026-09-08

### Fixed
- **The 403 ref-write carve-out only named tags.** Section 5.7 routed tag
  pushes to the user because Claude's credentials are commonly denied on
  `refs/tags/*`, but the same denial applies to deleting *any* ref — a branch
  delete (`git push origin --delete <branch>`) gets the identical `403` from a
  token that pushes commits and creates tags without issue. The carve-out is
  now framed as one principle with two faces (creating a tag ref, deleting any
  ref), not a tag-only special case, so a denied branch deletion is recognized
  and handed to the user instead of retried or worked around
- **The tag block asked for a shell it didn't need.** 2.15.1 fixed remote
  sessions skipping the shell question entirely, but still asked for a 7-way
  shell choice before presenting the tag block. Everything in that block below
  `cd` is a plain single-line `git` command — no heredocs, no shell-specific
  syntax — identical in all seven shells. Only the `cd` line varies, and a
  quoted path (`cd "<clone-path>"`) parses the same way regardless of shell.
  Remote sessions now ask only for the clone path
- **`git branch -r` had the same staleness flaw as `git tag -l`.** 2.15.0
  fixed ref-state reads for tags (`git ls-remote --tags origin` instead of the
  local-only `git tag -l`), but the "detect what's already done" step still
  read branches with `git branch -r` — cached remote-tracking refs that go
  stale the moment someone else pushes or deletes a branch. It now reads
  `git ls-remote --heads origin`, matching the tag-side fix
- **Missing troubleshooting entry: `src refspec … does not match any`.** Two
  sessions misread this git error as the credential `403` denial covered by
  the tag-push carve-out. It's unrelated — it means `git tag v1.2.3` was never
  run, or was run from a different directory than the one being pushed from,
  so there's no local tag for `push` to send. `GATE_REFERENCE.md` Gate 6 now
  calls this out explicitly, with the fix (re-run `git tag` from the clone
  path, then push)
- Nit: `SHELL_REFERENCE.md` cited the session-start procedure two different
  ways (`GATE_REFERENCE.md, session start, step 0` vs. `Section 6, step 0`).
  Unified on the first form

## [2.15.1] — 2026-09-08

### Fixed
- **Remote container sessions asked for a shell too late to ever ask at all.**
  Session start skips the shell question on remote containers, on the reasoning
  that Claude runs every git command in the container's own bash. 2.15.0's
  tag-push carve-out broke that reasoning: a remote session that reaches Gate 6
  now *always* hands the user one block to run on their own machine, and that
  block needs their shell's `cd` syntax and a real clone path — neither of which
  was ever collected. The result was a tag block opening with a literal
  `cd <your-repo-path>` placeholder, in the one block a user cannot skip and
  must run by hand. The question is now deferred rather than skipped: remote
  containers ask for shell and clone path at the moment a tag block is due, so
  sessions that never release are still never asked. Found while presenting the
  v2.15.0 tag block — the release that introduced the carve-out

## [2.15.0] — 2026-09-08

### Added
- **Local development workflow detection.** Session start (step 6) now detects
  two distinct workflows instead of one, because different gates depend on
  each. The **local dev workflow** — `scripts/`, `Makefile`, `package.json`
  scripts, `gradlew`, `tox.ini`, `CONTRIBUTING.md` build instructions — is what
  **Gate 2 (BUILD)** runs; it is the only thing that turns "the code should
  work" into "the code was run." The **CI workflow** splits into a build check
  (validates Gate 5's PR) and a release workflow (fired by Gate 6). Each missing
  piece is now surfaced against the gate it breaks, rather than reported as a
  generic absence
- **Drift check between the two.** When a project has both, CI is expected to
  invoke the project's own scripts rather than reimplement the build inline. A
  CI job carrying a hand-rolled copy of the build tests something the developer
  never runs locally, and the two diverge silently until a release breaks
- **A standard CI git flow, with a platform table for Linux, Windows, and
  Android.** Gate 6's CI-driven path previously documented Android signing as
  though it were the general case. The git sequence — merge, checkout, pull,
  tag, push, verify — is now stated as identical on every platform, with a table
  covering what actually differs: runner, release build command, artifact type,
  signing secrets, job shell, and the platform-specific ship failure (debug or
  unstripped on Linux, unsigned or self-signed on Windows, debug-signed on
  Android). Adds the two cross-platform traps that produce a release that looks
  fine and is not — CRLF line endings on Windows runners, and case sensitivity
  differing between Linux and Windows runners

### Fixed
- **`git tag -l` was the wrong command, and it was reading tag state in three
  places.** It lists *local* tags, and a fresh clone — every remote container,
  and any `--no-tags` or shallow checkout — has none, so it returns empty on a
  repo with a hundred tags. Gate 1's previous-version check, Section 2's
  re-derivation table, and Section 8's session-end check all used it, which made
  each of them report every prior version as untagged. A check that fires on
  everything is a check nobody reads, and a genuine missing tag hides in that
  noise. All tag reads now use `git ls-remote --tags origin`, which Gate 6's
  post-ship verification was already using — the detection paths were the
  inconsistent ones. Reading refs is not a write, so this is safe even where tag
  pushes are denied
- **A missing tag for the immediately preceding version now hard-blocks Gate 1.**
  Previously it was advisory ("note but don't hard-block"), so a release that
  never finished Gate 6 could be bumped straight over. That is how this repo
  shipped v2.12.0 and v2.13.0 with no tag and no GitHub release: each one was
  buried a version deeper by the next bump. A gap at the immediately preceding
  version means the default branch carries a version that was never published,
  and the blocked message names the two usual causes — a `403` on the tag push,
  or a session that ended between merge and tag. Older gaps stay advisory
- **Unfinished releases are now detected at session start** (`GATE_REFERENCE.md`
  step 7). Gate 6 has four parts — merge, tag, publish, verify — and a session
  can die between any two of them. The work is then stranded on the default
  branch, and **nothing in a later session went looking for it**: the next
  session starts with all gates ⬜ pending for the version it is about to build
  and never asks about the one before. Section 8's session-end check was the
  only backstop, and it only fires if the session gets to wind down — a
  reclaimed container, a usage limit, or a crash skips it entirely, which is
  exactly when a release is most likely to be half-finished. Session start
  compares released versions against remote tags and surfaces any that never
  shipped, before new work begins. Reported on the banner as a `Releases:` line

### Security
- **`release.yml` now verifies the tag is on the default branch before
  publishing.** `on: push: tags: 'v*'` fires for a tag on *any* commit, so a tag
  placed on an unreviewed branch would have published a real release from
  unreviewed code. The job now resolves the repo's default branch and fails
  unless the tagged commit is an ancestor of it. Verified both ways before
  shipping: it accepts the `master` tip and rejects a commit that exists only on
  an unmerged branch
- **`actions/checkout` pinned to a commit SHA** (`11d5960` = v4.4.0) in both
  workflows. A version tag is mutable and can be repointed at different code;
  a SHA cannot
- **`persist-credentials: false`** on both checkouts. Neither job pushes with
  git — the release job publishes with `GH_TOKEN` — so the credential had no
  reason to sit in `.git/config` while `scripts/validate.sh` runs
- Both workflows gain `concurrency` groups and `timeout-minutes`: the release
  group never cancels in flight (two tag pushes must not race for one release),
  while validate supersedes its own in-flight runs, since only the newest push's
  result matters

### Changed
- **Tag pushes are always handed to the user, in every environment.** The
  credentials Claude runs under are routinely denied on tag refs: a token that
  pushes branch commits all session gets `403` on `git push origin v1.2.3`,
  because creating a `refs/tags/*` ref — and creating a ref that triggers a
  workflow — is a separate permission, commonly withheld even where
  `contents: write` is granted. The blast radius is worse than an ordinary
  denial, since the tag push is what fires the release workflow: a 403 there
  strands a merged, version-bumped default branch with no release behind it.
  This is now a carve-out from §5.7's remote-container rule (where Claude
  otherwise executes git directly), covering tag creation, deletion, and
  re-push. 🚀 SHIP stays ⏳ until the tag is confirmed on the remote with
  `git ls-remote` — never ✅ on the assumption the user ran the block. Gate 6
  carries the block's shape, the sync that must precede the tag so it lands on
  the merged commit, and a GitHub UI fallback for users with no local clone
- **Gate 2 can no longer be satisfied by CI.** "CI will catch it" is explicitly
  rejected: CI runs after the commit this gate exists to protect. A project with
  a build system but no discoverable local build command now blocks the gate and
  asks, rather than passing on ➖ N/A — N/A is for projects with no build system,
  not for builds you could not find
- Gate 6's manual path splits its command block in two, so the tag push is the
  user's regardless of which ship path the project is on, and points at the
  platform table for what a correct artifact looks like
- Gate 1's release-notes link requirement is now met by the skill itself — the
  session-start block shows the versioned
  `releases/tag/v<VERSION>` URL alongside the releases index

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
