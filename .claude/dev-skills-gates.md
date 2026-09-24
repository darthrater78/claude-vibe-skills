# Dev Skills gate state
Track: release sequence
Mode: semi-autonomous (approved 2026-09-24) — commits and the tag still require the user's approval
Origin: darthrater78/claude-vibe-skills (not a fork)
Standards: at-rest ➖ stores nothing · login ➖ none · Apprise ➖ not Docker · compose ➖ not Docker · main-page links ✅
Version: 2.39.0
Updated: 2026-09-24

Previous: v2.38.0 SHIP done — PR #66 merged as 40eb11d, tag at 40eb11d, release run ok

Task: Windows hook gaps (py launcher, settings path match, PowerShell tool) + B5 prompt friction in semi-autonomous mode

🔢 VERSION    ✅ all refs at 2.39.0
  VERSION, SKILL.md, banner, release-notes link, README (x3); v2.38.0 tagged on remote
🔨 BUILD      ✅ build-skill.sh + validate.sh pass, 189/189 check tests
  real SKILL.md hook run in bash: py-only PATH → checks run; no Python → git/gh blocked exit 2
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
  fixed Medium: PowerShell/Windows forms bypassed A4/B5 (iex, pwsh -c/-EncodedCommand, cmd /c,
    git.exe, Set-Content/Out-File/Copy-Item/[IO.File]) — regression tests fail on old code
  fixed Low: leaving semi-auto + passing gates in one edit hid the gate rows from the prompt
  fixed Low: Start-Process/saps (+ -WorkingDirectory via git -C, no cd leak); here-strings
  fixed Low: heredoc bodies read as commands; now data unless a shell reads them (guard tests)
  Dependabot 0 open
📄 DOCS       ✅ CHANGELOG 2.39.0, README what's new, ENFORCEMENT.md (A4, B5, Python)
📦 RELEASE    ⏳ commit + CHANGELOG 2.39.0 notes approved 2026-09-24; PR to open from fix/windows-hooks
🚀 SHIP       ⏳ plan: CI green → merge (no --delete-branch) → user tags v2.39.0 → release.yml publishes
