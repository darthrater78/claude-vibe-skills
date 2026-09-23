# Dev Skills gate state
Track: release sequence (v2.31.0)
Mode: semi-autonomous (approved 2026-09-22) — commits and the tag still
      require the user's approval
Origin: darthrater78/claude-vibe-skills (not a fork)
Version: 2.31.0
Updated: 2026-09-22

Env: local, native Linux | Shell: Linux bash | Branch: feature/skill-md-trim | Default: master
Model: Opus 5.5, user approved staying for this task

Prior release: v2.30.0 SHIP ✅ — tag on 3a0d0ea (PR #56 merge commit);
release run 35801474080 ok; notes present; asset byte-identical to
committed bundle (sha256 e62855e1…). Folded in from the 2.30.0 ⏳ row.

🔢 VERSION    ✅ 2.31.0 in VERSION, SKILL.md, banner, release URL, README x2
              MINOR, user's call over the PATCH signal. v2.30.0 tagged on remote
🔨 BUILD      ✅ build-skill.sh + validate.sh green 10/10, tree stable
              bundle reproducible; handoff n/a — no Docker/.exe/.apk signal
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
              shellcheck 0.11.0: 0 findings (scripts/*.sh, hook)
              validate.sh addition reads repo files only; no eval, no network
              Hook untouched. Deps: none (github-actions only)
              Quality: 0 open. Rule audit: 53 manifest phrases present; 403
              removed sentences scored, 51 hand-reviewed, 3 restored
              Note (not a finding, for the user): hook requires VERSION BUILD
              DOCS RELEASE on any gh pr merge; prose lets a bookkeeping merge
              mark only RELEASE/SHIP N/A. Hook is stricter (fails closed)
📄 DOCS       ✅ CHANGELOG 2.31.0; README full pass (14 stale claims fixed)
              AUTO_MODE SHIP-record contradiction fixed; validate clean
📦 RELEASE    ✅ PR to master — this file ships inside it; notes = CHANGELOG 2.31.0
🚀 SHIP       ⏳ merge, CI on merge commit, then USER pushes tag v2.31.0
