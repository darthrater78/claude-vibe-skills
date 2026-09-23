# Dev Skills gate state
Track: release sequence
Mode: semi-autonomous (approved 2026-09-23) — commits and the tag still require the user's approval
Origin: darthrater78/claude-vibe-skills (not a fork)
Standards: at-rest ➖ stores nothing · login ➖ none · Apprise ➖ not Docker · compose ➖ not Docker · main-page links ✅
Version: 2.36.1
Updated: 2026-09-23
Skill: ⚠️ outdated (session loaded v2.34.0, latest v2.36.0)

Previous: v2.36.0 SHIP ✅ — tag at fbd4532, release run ✅, asset dev-skills.skill verified

🔢 VERSION    ✅ all refs at 2.36.1
  VERSION, SKILL.md, banner, release-notes link, README (x2 + footer); v2.36.0 tagged on remote
🔨 BUILD      ✅ build-skill.sh + validate.sh
  skill repo, no Docker/.exe/.apk signal; bundle rebuilt at 2.36.1; all checks passed
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
  prose-only; reviewed exposure of test creds: bind to private LAN IP only (Docker bypasses ufw), stop if not RFC1918; Dependabot 0 open
📄 DOCS       ✅ CHANGELOG 2.36.1, README Gate 2 text + what's-new
📦 RELEASE    ✅ commit + notes approved 2026-09-23; PR pending
🚀 SHIP       ⏳ merge, then tag v2.36.1 (user), release run, verify asset
