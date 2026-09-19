# Dev Skills gate state
Track: release sequence (v2.28.0)
Mode: manual
Version: 2.28.0
Updated: 2026-09-19

Env: remote container | Branch: claude/cost-optimization-review-1oesyw | Default: master

Release sequence for v2.28.0 — BLOCKED at Gate 3, 1 finding open:

🔢 VERSION    ✅ 2.28.0 across VERSION, SKILL.md frontmatter, the banner in
              SESSION_START.md, and README; v2.27.0 tagged on the remote at
              dc1bbea. MINOR — behavior-tightening, same call as 2.24.0
🔨 BUILD      ✅ validate.sh green. Bundle verified reproducible: two builds
              one second apart produced identical sha256. Hook verified on 5
              paths — release op with an open finding DENY, with 0 open
              ALLOW, work commit with an open finding ALLOW, missing cwd DENY,
              un-enterable cwd DENY
              handoff n/a — no Docker/.exe/.apk artifact in this repo
🔒 SECURITY   🚫 1 open — release track blocked (SECURITY_GATE.md)
              📝 Medium, OPEN, needs the repo owner: Dependabot alerts and
              security updates are repository settings. Verified unverifiable
              from here — no MCP tool exposes the endpoint and `git credential
              fill` yields nothing, so the session holds no token to query
              GET /repos/.../dependabot/alerts. Enablement steps to hand
              over: SECURITY_GATE.md, "Enabling Dependabot alerts". Impact is
              NOT negligible as first assessed — the dependency graph covers
              GitHub Actions, so the two pinned actions/checkout refs are real
              advisory surface despite there being no package manifests
              ✅ fixed: no .github/dependabot.yml → added (github-actions,
              weekly, grouped); only ecosystem, no package manifests exist
              ✅ fixed: shellcheck unavailable → installed and run. 3 findings,
              all fixed. SC2164 was a real fail-open path in gate-preflight.sh:
              an unchecked cd left it reading the wrong state file. Now denies
              ✅ fixed: bundle was not a reproducible build — zipfile stamped
              build time, so v2.27.0's asset and its committed copy hashed
              differently with all 21 entries identical. Entry metadata pinned
              to the zip epoch; archive comparison is now a real check
              Scan on this diff: 0 Critical, 0 High. Secrets scan clean (two
              matches are the skill's own documentation of what a Critical
              looks like). No eval, no piped-curl, no destructive commands in
              changed shell. File modes correct. shellcheck 0.9.0: 0 findings
              across all three scripts
📄 DOCS       ✅ CHANGELOG 2.28.0 complete; README shortcut and size tables;
              hooks/README.md documents the new check; 0 broken anchors; every
              file the README names exists
📦 RELEASE    ⬜ blocked by SECURITY. PR #52 exists but opened as bookkeeping
              and is now mis-titled; retitle as the 2.28.0 release PR. When
              SECURITY clears, THIS FILE ships inside that PR (Gate 5 step 3)
              with gates 1–5 ✅ and SHIP ⏳
🚀 SHIP       ⬜ blocked by SECURITY. Post-tag ✅ folds into the next release's
              PR, not its own (SHIP_REFERENCE.md step 7)

The one open finding is not fixable from this session and is not Claude's to
waive. It is the user's: fix it in repo settings, or waive it with a reason.
