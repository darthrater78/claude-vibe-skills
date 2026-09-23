#!/usr/bin/env bash
# dev-skills gate pre-flight — PreToolUse hook
#
# Blocks git write operations when the gates the operation requires have not
# passed. This is the deterministic half of gate enforcement: SKILL.md asks
# Claude to check the gates, this makes the check unskippable for anything
# Claude executes itself.
#
# Source of truth is .claude/dev-skills-gates.md (SKILL.md Section 2). A gate
# counts as satisfied when its ROW -- the line naming the gate, plus any
# continuation lines below it up to the next gate or a blank line -- carries
# ✅ (passed) or ➖ (N/A). Checking only the first line missed a status or
# annotation that wrapped past it, which blocked real work over formatting,
# not over missing work -- see gate_block() below.
#
# Install: see hooks/README.md
# Bypass:  DEV_SKILLS_GATE_HOOK=off
#
# Fails closed. Per SKILL.md Section 4, when something unexpected happens we
# deny rather than allow.

set -uo pipefail

STATE_REL=".claude/dev-skills-gates.md"

# --- output helpers -----------------------------------------------------------

# deny <reason>
deny() {
  # Emit the JSON by hand so the hook has no dependency on jq for output.
  local reason="$1"
  reason="${reason//\\/\\\\}"
  reason="${reason//\"/\\\"}"
  reason="${reason//$'\n'/\\n}"
  reason="${reason//$'\t'/\\t}"
  reason="${reason//$'\r'/}"
  # Strip any remaining raw control character — it would make the JSON invalid.
  # Real newlines and tabs became two-character escapes above, so this is safe.
  reason="$(printf '%s' "$reason" | tr -d '\000-\037')"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
  exit 0
}

# No opinion — the tool call proceeds through the normal permission flow.
allow() { exit 0; }

[ "${DEV_SKILLS_GATE_HOOK:-on}" = "off" ] && allow

# --- read hook input ----------------------------------------------------------

INPUT="$(cat)"
[ -z "$INPUT" ] && allow

# Extract a top-level or nested field. jq preferred, python3 as fallback.
json_get() {
  local path="$1"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$INPUT" | jq -r "$path // empty" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$INPUT" | python3 -c '
import json,sys
path=sys.argv[1].lstrip(".").split(".")
try:
    cur=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for k in path:
    if isinstance(cur,dict) and k in cur:
        cur=cur[k]
    else:
        sys.exit(0)
if cur is not None:
    sys.stdout.write(cur if isinstance(cur,str) else json.dumps(cur))
' "$path" 2>/dev/null
  else
    printf '__NOPARSER__'
  fi
}

TOOL_NAME="$(json_get '.tool_name')"
if [ "$TOOL_NAME" = "__NOPARSER__" ]; then
  deny "dev-skills gate hook cannot run: neither jq nor python3 is available to parse the hook payload. This hook fails closed, so git write operations are blocked until one is installed. Install jq (or python3), or set DEV_SKILLS_GATE_HOOK=off to disable gate enforcement."
fi
[ -z "$TOOL_NAME" ] && allow

# --- classify the operation ---------------------------------------------------
# OP_LABEL: what to call it in the denial message
# REQUIRED: gates that must be ✅ or ➖ before it may proceed

OP_LABEL=""
REQUIRED=""
IS_MERGE=""

case "$TOOL_NAME" in
  Bash)
    CMD="$(json_get '.tool_input.command')"
    [ -z "$CMD" ] && allow
    # Strip quoting so `git commit -m "..."` and friends match predictably.
    SCAN="$(printf '%s' "$CMD" | tr '\n' ' ')"
    # `git -C <dir> push` and `git -c k=v commit` are the same operations;
    # without this they slipped past every pattern below.
    SCAN="$(printf '%s' "$SCAN" | sed -E 's/git([[:space:]]+-[cC][[:space:]]*[^[:space:]]+)+/git/g')"

    # Tag pushes and ref deletions are the user's to run, in BOTH modes
    # (SKILL.md Section 5.8). No gate state makes them Claude's, so this is
    # checked before the gate file is even read. Listing tags stays allowed.
    # `git tag` with no argument, or only listing/verifying/local-delete
    # flags, reads. Any other argument creates a tag. Allowlisted, so an option
    # nobody thought of (--annotate, --sign, --force) fails closed.
    tag_creates=""
    while IFS= read -r seg; do
      [ -z "$seg" ] && continue
      args="$(printf '%s' "$seg" | sed -E 's/^git[[:space:]]+tag[[:space:]]*//')"
      [ -z "$args" ] && continue
      printf '%s' " $args" | grep -qE '[[:space:]](-l|--list|-d|--delete|-v|--verify|--contains|--no-contains|--points-at|--merged|--no-merged|-n[0-9]*|--column|-i|--ignore-case)([[:space:]=]|$)' && continue
      printf '%s' " $args" | grep -qE '[[:space:]](--sort|--format)[=[:space:]]' && continue
      tag_creates=1
    done <<< "$(printf '%s' "$SCAN" | grep -oE 'git[[:space:]]+tag([[:space:]]+[^;&|]*)?')"

    if [ -n "$tag_creates" ] \
       || printf '%s' "$SCAN" | grep -qE 'git[[:space:]]+push[[:space:]].*(--tags|--follow-tags|--mirror|--delete|[[:space:]]-d([[:space:]]|$)|[[:space:]]\+?:[^[:space:]]|refs/tags/|[[:space:]]v[0-9]+\.[0-9]+)' \
       || printf '%s' "$SCAN" | grep -qE 'gh[[:space:]]+pr[[:space:]]+merge[[:space:]].*(--delete-branch|[[:space:]]-d([[:space:]]|$))' \
       || printf '%s' "$SCAN" | grep -qE 'gh[[:space:]]+api[[:space:]].*(-X|--method)[[:space:]]*DELETE.*git/refs' \
       || printf '%s' "$SCAN" | grep -qE 'gh[[:space:]]+api[[:space:]].*git/refs.*(-X|--method)[[:space:]]*DELETE'; then
      deny "🚫 USER-ONLY REF OPERATION

Blocked: creating or pushing a tag, or deleting a ref (branch or tag)

Per SKILL.md Section 5.8 these are the user's to run in BOTH manual and semi-autonomous mode. Claude's credentials are routinely denied on exactly these ref operations, and a failed tag push strands a merged default branch with no release behind it. No gate state changes this.

Present the command as a block for the user to run from their own clone, with the tracker (and, in semi-autonomous mode, the full pre-tag report) above it. Then confirm the result yourself with git ls-remote. Do not retry through another path."
    fi

    # Tag creation and tag pushes were denied above, so the release track here
    # is the merge, the publish, and a direct push to the default branch.
    if printf '%s' "$SCAN" | grep -qE '(^|[;&|(]|&&|\|\|)[[:space:]]*(gh[[:space:]]+release[[:space:]]+create|gh[[:space:]]+pr[[:space:]]+merge)' \
       || printf '%s' "$SCAN" | grep -qE 'git[[:space:]]+push[[:space:]]+origin[[:space:]]+(main|master)([[:space:]]|$)'; then
      OP_LABEL="a release operation (merge / publish)"
      REQUIRED="VERSION BUILD SECURITY DOCS RELEASE"
      printf '%s' "$SCAN" | grep -qE 'gh[[:space:]]+pr[[:space:]]+merge|git[[:space:]]+push[[:space:]]+origin[[:space:]]+(main|master)([[:space:]]|$)' && IS_MERGE=1
    elif printf '%s' "$SCAN" | grep -qE 'gh[[:space:]]+pr[[:space:]]+create'; then
      OP_LABEL="opening a pull request (Gate 5)"
      REQUIRED="VERSION BUILD SECURITY DOCS"
    elif printf '%s' "$SCAN" | grep -qE '(^|[;&|(]|&&|\|\|)[[:space:]]*git[[:space:]]+(commit|push)([[:space:]]|$)'; then
      OP_LABEL="a work commit / push"
      REQUIRED="SECURITY"
    else
      allow
    fi
    ;;
  mcp__github__merge_pull_request)
    OP_LABEL="merging a pull request (Gate 6)"
    REQUIRED="VERSION BUILD SECURITY DOCS RELEASE"
    IS_MERGE=1
    ;;
  mcp__github__create_pull_request)
    OP_LABEL="opening a pull request (Gate 5)"
    REQUIRED="VERSION BUILD SECURITY DOCS"
    ;;
  mcp__github__create_tag|mcp__github__delete_branch|mcp__github__delete_tag|mcp__github__delete_ref)
    deny "🚫 USER-ONLY REF OPERATION

Blocked: $TOOL_NAME

Tag creation and ref deletion are the user's to run in both modes (SKILL.md Section 5.8). Present the equivalent git command as a block for the user instead."
    ;;
  mcp__github__push_files|mcp__github__create_or_update_file|mcp__github__delete_file)
    OP_LABEL="a work commit / push"
    REQUIRED="SECURITY"
    ;;
  *)
    allow
    ;;
esac

# --- locate the gate state file -----------------------------------------------

CWD="$(json_get '.cwd')"
# A cd that fails here would leave the hook resolving ROOT from whatever
# directory it happens to be in, and so reading the wrong gate state file --
# or none. This hook fails closed, so that is a denial, not a shrug. Note the
# fix SC2164 suggests (`|| exit`) would exit 0, which here means ALLOW.
if [ -n "$CWD" ] && [ -d "$CWD" ]; then
  cd "$CWD" 2>/dev/null || deny "🚫 GATE PRE-FLIGHT — cannot enter the session's working directory.

Blocked: $OP_LABEL
Directory: $CWD

The hook could not cd into the directory the tool call reported, so it cannot locate $STATE_REL and has no evidence any gate has run. Per SKILL.md Section 4, unexpected means deny, not proceed.

Check the directory's permissions, then retry."
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$ROOT" ]; then
  ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
fi
STATE="$ROOT/$STATE_REL"

if [ ! -f "$STATE" ]; then
  deny "🚫 GATE PRE-FLIGHT — no gate state file.

Blocked: $OP_LABEL
Missing: $STATE_REL

The dev-skills gate state file does not exist, so there is no evidence any gate has run. Per SKILL.md Section 2, unknown is never \"passed.\"

Do this before retrying:
1. Re-derive gate state from evidence (SKILL.md Section 2 re-derivation table) — do not assume a gate passed because it feels like it did.
2. Run whichever of these gates is still pending: $REQUIRED
3. Write $STATE_REL with the resulting state.

Do not work around this by editing the state file to say a gate passed when it did not."
fi

# --- operating mode must be chosen ---------------------------------------------
# SKILL.md "Operating modes": every session starts with the mode unchosen and
# the user picks manual or semi-autonomous before any git write. A missing row,
# "unchosen", or anything else is not a default of manual -- it is a question
# nobody asked. Only the first Mode: line counts.

MODE_LINE="$(grep -m1 -E '^Mode:' "$STATE" 2>/dev/null)"
if ! printf '%s' "$MODE_LINE" | grep -qE '^Mode:[[:space:]]*(manual|semi-autonomous)([[:space:]]|$)'; then
  deny "🚫 GATE PRE-FLIGHT — operating mode not chosen.

Blocked: $OP_LABEL
Found: ${MODE_LINE:-no Mode: row in $STATE_REL}

Per SKILL.md \"Operating modes\", the user chooses manual or semi-autonomous at session start, and no git write runs until they have. Ask the mode question (SESSION_START.md, \"Mode choice\"), then write their answer to the Mode: row.

Do not pick the mode yourself, and do not write one the user did not say. A missing row means unchosen, not manual."
fi

# --- forks: every write targets the fork ---------------------------------------
# SKILL.md Section 5.8 / SHELL_REFERENCE.md "Forks". The Origin: row records the fork
# ("Origin: owner/repo (fork of parent/repo)"). In a fork, a bare
# `gh pr create` opens the PR against the PARENT repo, so a gh write must name
# the fork explicitly, and nothing may name any other repo or push to any
# remote other than origin.

ORIGIN_LINE="$(grep -m1 -E '^Origin:' "$STATE" 2>/dev/null)"
ORIGIN_SLUG="$(printf '%s' "$ORIGIN_LINE" | sed -nE 's#^Origin:[[:space:]]*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+).*#\1#p')"
IS_FORK=""
printf '%s' "$ORIGIN_LINE" | grep -qiF 'fork of' && IS_FORK=1

fork_deny() {
  deny "🚫 GATE PRE-FLIGHT — fork target check.

Blocked: $OP_LABEL
Origin: ${ORIGIN_LINE:-none recorded}
Problem: $1

Per SKILL.md Section 5.8 and SHELL_REFERENCE.md \"Forks\", every push, PR, merge and release goes to the fork (origin). Nothing in the session targets the upstream repo. The user does anything upstream on GitHub directly. Pass --repo $ORIGIN_SLUG explicitly. If the Origin: row is wrong, re-run SESSION_START.md step 1a instead of editing it to fit."
}

if [ -n "$IS_FORK" ] && [ -z "$ORIGIN_SLUG" ]; then
  fork_deny "the Origin: row says this is a fork but does not name the fork as owner/repo."
fi

# fork_check_bash -- every gh target named in the command is the fork; in a
# fork, every gh pr/release call names one, and every push names origin.
fork_check_bash() {
  local clean targets target calls named
  clean="$(printf '%s' "$SCAN" | tr -d "\"'")"
  if printf '%s' "$clean" | grep -qE 'gh[[:space:]]+(pr|release)[[:space:]]'; then
    # A chain can carry more than one gh call, and GH_REPO= retargets gh the
    # same way --repo does, so every named target is checked.
    targets="$(printf '%s' "$clean" | grep -oE '(^|[[:space:]])(--repo[= ]|-R[= ]?|GH_REPO=)[[:space:]]*[^[:space:]]+' | sed -E 's/^[[:space:]]*(--repo|-R|GH_REPO=)[= ]?[[:space:]]*//; s#^https?://github\.com/##; s#\.git$##')"
    while IFS= read -r target; do
      [ -n "$target" ] && [ "$target" != "$ORIGIN_SLUG" ] \
        && fork_deny "this command targets $target, not $ORIGIN_SLUG."
    done <<< "$targets"
    calls="$(printf '%s' "$clean" | grep -oE 'gh[[:space:]]+(pr|release)[[:space:]]' | wc -l)"
    named="$(printf '%s' "$clean" | grep -oE '(^|[[:space:]])(--repo[= ]|-R[= ]?)[[:space:]]*[^[:space:]]+' | wc -l)"
    [ -n "$IS_FORK" ] && [ "$named" -lt "$calls" ] \
      && ! printf '%s' "$clean" | grep -qE '(^|[[:space:]])GH_REPO=' \
      && fork_deny "a gh pr/release call with no --repo in a fork resolves to the PARENT repo by default."
  fi
  [ -z "$IS_FORK" ] && return 0
  printf '%s' "$clean" | grep -qE 'git[[:space:]]+push([[:space:]]|$)' || return 0
  printf '%s' "$clean" | grep -qE 'git[[:space:]]+push([[:space:]]+-[^[:space:]]+)*[[:space:]]+origin([[:space:]]|$)' \
    || fork_deny "git push must name origin (the fork) explicitly, never another remote or an implicit one."
}

# fork_check_mcp -- an MCP write names the fork as owner/repo.
fork_check_mcp() {
  local owner repo
  owner="$(json_get '.tool_input.owner')"
  repo="$(json_get '.tool_input.repo')"
  [ -n "$owner$repo" ] && [ "$owner/$repo" != "$ORIGIN_SLUG" ] \
    && fork_deny "this call targets $owner/$repo, not $ORIGIN_SLUG."
}

if [ -n "$ORIGIN_SLUG" ]; then
  if [ "$TOOL_NAME" = "Bash" ]; then fork_check_bash; else fork_check_mcp; fi
fi

# --- evaluate the required gates ----------------------------------------------
# A gate is satisfied when its ROW carries ✅ (passed) or ➖ (N/A) -- not just
# its first line. Byte-literal matching via grep -F, so locale settings can't
# break it.

GATE_NAMES='VERSION|BUILD|SECURITY|DOCS|RELEASE|SHIP'

# gate_block <gate> -- print the gate's full row: the line naming it, plus
# every line after it up to (not including) the next gate's line or a blank
# line. A `head -1` here is what let a status symbol or a "handoff"
# annotation wrapped onto a continuation line read as absent.
gate_block() {
  awk -v gate="$1" -v names="$GATE_NAMES" '
    BEGIN {
      start_pat = "(^|[[:space:]])" gate "([[:space:]]|$)"
      any_pat   = "(^|[[:space:]])(" names ")([[:space:]]|$)"
    }
    {
      if (found && ($0 ~ any_pat || NF == 0)) { exit }
      if (!found && $0 ~ start_pat) { found = 1 }
      if (found) print
    }
  ' "$STATE" 2>/dev/null
}

BLOCKING=""
for gate in $REQUIRED; do
  block="$(gate_block "$gate")"
  if [ -z "$block" ]; then
    BLOCKING="$BLOCKING
  - $gate — not present in $STATE_REL (treated as pending)"
    continue
  fi
  if printf '%s' "$block" | grep -qF '✅'; then continue; fi
  if printf '%s' "$block" | grep -qF '➖'; then continue; fi
  status="$(printf '%s' "$block" | head -1 | sed "s/^[[:space:]]*//")"
  BLOCKING="$BLOCKING
  - $status"
done

# --- BUILD gate: local-artifact-handoff annotation ----------------------------
# GATE_REFERENCE.md Gate 2 requires Claude to offer a way to try a compiled
# artifact (Docker image, Windows .exe, Android .apk) by hand before BUILD
# passes -- a conversational step this hook cannot observe directly. What it
# can check, the same way every other gate here is checked, is whether the
# tracker line says it happened. A BUILD line marked ✅ with no "handoff"
# annotation, in a repo that plainly produces one of these artifact types, is
# textual evidence the offer was skipped, not proof it was made.
produces_compiled_artifact() {
  find "$ROOT" -maxdepth 4 \
    \( -path '*/.git' -o -path '*/node_modules' -o -path '*/.venv' -o -path '*/venv' -o -path '*/build' -o -path '*/dist' \) -prune -o \
    \( -iname 'Dockerfile' -o -iname '*.csproj' -o -iname '*.sln' -o -iname 'AndroidManifest.xml' -o -iname 'build.gradle' -o -iname 'build.gradle.kts' \) -print \
    2>/dev/null | head -1 | grep -q .
}

if printf '%s' "$REQUIRED" | grep -qw BUILD; then
  build_block="$(gate_block BUILD)"
  if printf '%s' "$build_block" | grep -qF '✅' \
     && ! printf '%s' "$build_block" | grep -qiF 'handoff' \
     && produces_compiled_artifact; then
    BLOCKING="$BLOCKING
  - BUILD — ✅ but no local-artifact-handoff annotation. This repo has a Docker/.exe/.apk build signal (Dockerfile, .csproj/.sln, or an Android Gradle project). GATE_REFERENCE.md Gate 2 requires handing the user a test artifact before this gate passes. Add \"handoff offered, user tried it\" or \"handoff offered, user declined to try it\" to the BUILD row, then retry."
  fi
fi

# --- merges: a test artifact from the merged commit ---------------------------
# GATE_REFERENCE.md Gate 2, "Test artifact before merge": nothing merges to the
# default branch in an artifact-producing repo until a test artifact built from
# the exact commit being merged exists and was handed to the user -- in every
# environment, remote containers included (they get theirs from CI). A ➖ BUILD
# does not exempt a repo that plainly builds one. Docker repos also record that
# the test run's throwaway credentials were generated and shown.
uses_docker() {
  find "$ROOT" -maxdepth 4 \
    \( -path '*/.git' -o -path '*/node_modules' -o -path '*/.venv' -o -path '*/venv' -o -path '*/build' -o -path '*/dist' \) -prune -o \
    \( -iname 'Dockerfile' -o -iname 'compose.yaml' -o -iname 'compose.yml' -o -iname 'docker-compose.yml' -o -iname 'docker-compose.yaml' \) -print \
    2>/dev/null | head -1 | grep -q .
}

if [ -n "$IS_MERGE" ] && produces_compiled_artifact; then
  build_block="$(gate_block BUILD)"
  if ! printf '%s' "$build_block" | grep -qiF 'test artifact:'; then
    BLOCKING="$BLOCKING
  - BUILD — no test artifact recorded. Nothing merges to the default branch in a repo with a Docker/.exe/.apk build signal until a test artifact built from the exact commit being merged exists and the user has been told where it is (GATE_REFERENCE.md Gate 2, \"Test artifact before merge\"). In a remote container or Termux session it comes from CI: a PR build artifact or a dev pre-release. Add \"test artifact: <path or link> @ <short SHA>\" to the BUILD row once it exists, then retry."
  fi
  if uses_docker && ! printf '%s' "$build_block" | grep -qiF 'test creds'; then
    BLOCKING="$BLOCKING
  - BUILD — no test credentials recorded. Every Docker test run gets a freshly generated throwaway username and password, shown to the user with the run command (GATE_REFERENCE.md Gate 2). Add \"test creds: generated per run, shown to user\" or \"test creds: n/a (no login)\" to the BUILD row, then retry."
  fi
fi

# --- SECURITY gate: no open findings ------------------------------------------
# GATE_REFERENCE.md Gate 3: severity decides urgency, not whether a finding can
# be carried. No finding of any severity may be open when the release track
# runs -- a finding leaves the open state only by being fixed, waived by the
# user with a reason, or withdrawn as wrong.
#
# The SECURITY row's FIRST line carries the open count ("✅ 0 open — ...")
# precisely so this check is line-oriented, per the row-format rule in
# SKILL.md Section 2. A ✅ whose first line does not say "0 open" is an
# illegal state: it asserts the gate passed while the row itself still counts
# findings nobody resolved. That combination is what carried a real Medium
# across two releases of this repo with SECURITY reading ✅ the whole way.
#
# Scoped to the release track. Work commits must stay possible with findings
# open -- that is where a finding gets recorded in the first place.
if printf '%s' "$REQUIRED" | grep -qw RELEASE; then
  sec_first="$(gate_block SECURITY | head -1)"
  if printf '%s' "$sec_first" | grep -qF '✅' \
     && ! printf '%s' "$sec_first" | grep -qE '(^|[^0-9])0[[:space:]]+open'; then
    BLOCKING="$BLOCKING
  - SECURITY — ✅ but the row's first line does not say \"0 open\". Per GATE_REFERENCE.md Gate 3, nothing reaches the release track with an open finding of any severity. Resolve each one: fix it, have the USER waive that specific finding with a reason and date, or withdraw it as wrong. Then set the first line to \"✅ 0 open — 0 Critical, 0 High\". Do not clear this by editing the count while findings are still open, and do not waive your own finding."
  fi
fi

[ -z "$BLOCKING" ] && allow

TRACKER="$(sed 's/^/  /' "$STATE" 2>/dev/null)"

deny "🚫 GATE PRE-FLIGHT BLOCKED

Blocked: $OP_LABEL
Required gates: $REQUIRED

Not yet ✅ or ➖ N/A:$BLOCKING

Current state ($STATE_REL):
$TRACKER

Run the blocking gate(s) per SKILL.md, update $STATE_REL, then retry.

A gate leaves the workflow only two ways: it passes (✅), or it is marked ➖ N/A for a structural reason stated on the tracker — no build system, no compiled artifact, no app UI. \"We'll do it later\" is not N/A. Do not edit the state file to clear a gate you did not run."
