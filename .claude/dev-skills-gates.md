# Dev Skills gate state
Track: release sequence
Mode: semi-autonomous (approved 2026-09-24) — commits and the tag still require the user's approval
Hook enforcement: not active — installed skill is v2.36.1 (instructions still apply)
Origin: darthrater78/claude-vibe-skills (not a fork)
Standards: at-rest ➖ stores nothing · login ➖ none · Apprise ➖ not Docker · compose ➖ not Docker · main-page links ✅
Version: 2.38.0
Updated: 2026-09-24

Previous: v2.37.0 SHIP done — PR #65 merged as 8bd6681, tag at 8bd6681, release run ok, asset dev-skills.skill (161223 B) verified

🔢 VERSION    ✅ all refs at 2.38.0
  VERSION, SKILL.md, banner, release-notes link, README (x3); v2.37.0 tagged on remote
🔨 BUILD      ✅ build-skill.sh + validate.sh pass, 145/145 check tests
  every documented lookup run live: nodejs.org (v24.21.0), Adoptium (25), .NET
  releases-index (10.0 lts), endoflife.date (node 26 lts=2026-10-28, ubuntu 26.04)
  session-start ENFORCEMENT.md section extract returns 1790 B
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
  diff: skill docs + file lists and size ceilings in build-skill.sh/validate.sh; no code in checks/
  doc commands: HTTPS read-only lookups, no pipe-to-shell; fixed Low: curl -s → -sf
  moved rules still backed in SKILL.md (tags §5.8, forks §5.8, version check §6); rule phrases guard them
  Dependabot 0 open
📄 DOCS       ✅ CHANGELOG 2.38.0, README (what's new, Gate 3 list, file table + sizes)
📦 RELEASE    ✅ PR #66 open, commit 99892ad approved, CHANGELOG 2.38.0 notes approved
🚀 SHIP       ⏳
