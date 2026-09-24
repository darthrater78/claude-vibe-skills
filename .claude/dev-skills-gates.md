# Dev Skills gate state
Track: release sequence
Mode: semi-autonomous (approved 2026-09-24) — commits and the tag still require the user's approval
Hook enforcement: not active — live-test copy removed; installed skill is v2.36.1 until 2.37.0 ships (instructions still apply)
Origin: darthrater78/claude-vibe-skills (not a fork)
Standards: at-rest ➖ stores nothing · login ➖ none · Apprise ➖ not Docker · compose ➖ not Docker · main-page links ✅
Version: 2.37.0
Updated: 2026-09-24

Previous: v2.36.1 SHIP done — PR #64, tag at 90d8107, release run ok, asset dev-skills.skill verified

🔢 VERSION    ✅ all refs at 2.37.0
  VERSION, SKILL.md, banner, release-notes link, README (x3); v2.36.1 tagged on remote
🔨 BUILD      ✅ build-skill.sh + validate.sh pass, 145/145 check tests, live test passed
  live A10/A12: unlabeled + root temp mount denied; correct run allowed, file
  owned 1000:1000, sweep found it, removed (0 left); found+fixed compose -p bypass
  skill repo, no Docker/.exe/.apk signal
  live (dev-skills-e2e): hooks registered via CLAUDE_PLUGIN_ROOT, marker written,
  cd+commit denied, 127.0.0.1 run denied, restart+/tmp run denied (A9),
  B5 prompts reached the user, D1 fired
  live test found 3 gaps, fixed + tested: cd/git -C ignored; ~/$HOME paths missed
  by B5; D1 misread an option label containing a comma
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
  fixed: Medium header fallback matched Write/Edit content → now only Bash git/gh/docker
  and GitHub MCP tools; 8 fallback tests added (Edit/Write/quoted payload pass through)
  stdlib only, no deps; Dependabot 0 open; re-scanned after A9 and the live fixes
  fixed: Low shared temp dir → per-user, symlink/owner refused
  fixed: Medium no type hints (enforce.py, test-checks.py) → added
  fixed: Low open() without encoding → added
📄 DOCS       ✅ CHANGELOG 2.37.0, README (enforcement, manual mode, what's new, sizes), ENFORCEMENT.md, hooks/README.md
📦 RELEASE    ✅ PR #65 open, commit 246ea9e approved, CHANGELOG 2.37.0 notes approved
🚀 SHIP       ⏳
