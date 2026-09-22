# Dev Skills gate state
Track: work commit (release v2.29.0 paused — Dependabot finding open)
Mode: semi-autonomous (approved 2026-09-22) — commits and the tag still
      require the user's approval
Origin: darthrater78/claude-vibe-skills (not a fork)
Version: 2.29.0
Updated: 2026-09-22

Env: local, native Linux | Shell: Linux bash | Branch: feature/session-start-mode-and-fork | Default: master

Prior release: v2.28.0 SHIP ✅ — tag on 6e4919f (PR #52 merge commit),
release asset dev-skills.skill present. Folded in from the 2.28.0 ⏳ row.

🔢 VERSION    ✅ 2.29.0 in VERSION, SKILL.md, banner, README
              MINOR (feat). v2.28.0 tagged on remote at 6e4919f
🔨 BUILD      ✅ build-skill.sh + validate.sh green, tree stable
              handoff n/a — no Docker/.exe/.apk signal in this repo
              Hook: 52-case matrix pass (master's hook fails 28)
              Re-run after cost pass: validate green, tree stable, matrix 52/52
🔒 SECURITY   ✅ 1 open — 0 Critical, 0 High, 1 Medium (blocks release)
              📝 open: Dependabot alerts DISABLED — verified this session,
              GET .../dependabot/alerts → 403 "disabled". The 2.28.0 waiver
              was granted as "unverified either way"; verification changed
              its context, so it re-opened. Needs the user: enable, or re-waive
              ✅ fixed: hook bypasses — git -C/-c, chained gh --repo, GH_REPO=,
              git tag long options, git push +:ref
              Code scan: no secrets, no eval, no piped-curl, no rm -rf.
              shellcheck 0.11.0: 0 findings (hook, validate.sh, build-skill.sh)
              Deps: no package manifests; github-actions only (dependabot.yml)
              Cost pass is prose-only (no hooks/scripts touched), nothing to scan
              Quality: 0 open — fork checks extracted to functions (nesting ≤3)
📄 DOCS       ✅ CHANGELOG 2.29.0; README modes/forks/hook table; hooks/README;
              stale "Claude pushes the tag" claims removed; validate clean
              Cost pass: SKILL.md 66→51KB, SESSION_START 30→25KB; README
              size table + CHANGELOG "Changed" updated; no rule phrase lost
📦 RELEASE    ⬜
🚀 SHIP       ⬜
