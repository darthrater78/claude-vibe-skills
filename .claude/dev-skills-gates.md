# Dev Skills gate state
Track: release sequence (v2.28.0)
Mode: manual
Version: 2.28.0
Updated: 2026-09-19

Env: remote container | Branch: claude/cost-optimization-review-1oesyw | Default: master

Release sequence for v2.28.0 — BLOCKED at Gate 3 by its own new rule:

🔢 VERSION    ✅ 2.28.0 across VERSION, SKILL.md frontmatter, the banner in
              SESSION_START.md, and README; v2.27.0 tagged at dc1bbea.
              MINOR — behavior-tightening, same call as 2.24.0's version guard
🔨 BUILD      ✅ validate.sh green including the 2.27.0 ceilings. Hook verified
              against all three states: the exact 2.26.0 tracker text now
              denies `git tag`, a "0 open" row allows it, a work commit with an
              open Medium is unaffected
🔒 SECURITY   🚫 2 open — release track blocked until each is fixed, waived by
              the user with a reason, or withdrawn (GATE_REFERENCE.md →
              SECURITY_GATE.md)
              📝 Medium, OPEN: shellcheck unavailable in this container, so
              scripts/validate.sh, build-skill.sh and gate-preflight.sh are
              unlinted. bash -n clean on all three; that is not the same check
              📝 Medium, OPEN: Dependabot alerts and security updates are
              repository settings, and no tool in this session can read
              GET /repos/.../dependabot/alerts to confirm their state.
              Settings → Code security. Claude cannot flip a repo setting
              ✅ fixed 2026-09-19: no .github/dependabot.yml → added
              (github-actions, weekly, grouped)
📄 DOCS       ✅ CHANGELOG 2.28.0; README shortcut table and size table;
              hooks/README.md documents the new check
📦 RELEASE    ⬜ blocked by SECURITY — PR #52 must not merge while 2 are open.
              When it unblocks, THIS FILE ships inside that PR (Gate 5 step 3),
              gates 1–5 ✅ and SHIP ⏳ — not a bookkeeping PR afterwards
🚀 SHIP       ⬜ blocked by SECURITY. The post-tag ✅ line folds into the next
              release's PR, not its own (SHIP_REFERENCE.md step 7)

Why this is the correct state, not a problem to route around: 2.28.0 is the
release that made an open finding of any severity block the release track. Both
findings above are real, neither is fixable from this session, and marking
SECURITY ✅ to let its own release through would be the precise failure the
release exists to stop. They are the user's to fix or waive.

This commit's own gates (work-commit track — commits and pushes stay allowed
with findings open, which is how a finding gets recorded at all):
🔒 SECURITY   ✅ 0 open for the commit itself — no Critical or High anywhere;
              Markdown, two Bash scripts and one YAML config
🔢 🔨 📄       ✅ covered by the release rows above
📦 🚀          ⬜ not attempted
