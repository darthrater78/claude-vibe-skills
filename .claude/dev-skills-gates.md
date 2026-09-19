# Dev Skills gate state
Track: release sequence (v2.28.0)
Mode: manual
Version: 2.28.0
Updated: 2026-09-19

Env: remote container | Branch: claude/cost-optimization-review-1oesyw | Default: master

Release sequence for v2.28.0 — Gates 1-5 passed, awaiting merge + tag:

🔢 VERSION    ✅ 2.28.0 across VERSION, SKILL.md frontmatter, the banner in
              SESSION_START.md, and README; v2.27.0 tagged on the remote at
              dc1bbea. MINOR — behavior-tightening, same call as 2.24.0
🔨 BUILD      ✅ validate.sh green. Bundle verified reproducible: two builds
              one second apart produced identical sha256. Hook verified on 5
              paths — release op with an open finding DENY, with 0 open
              ALLOW, work commit with an open finding ALLOW, missing cwd DENY,
              un-enterable cwd DENY
              handoff n/a — no Docker/.exe/.apk artifact in this repo
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
              🔕 waived 2026-09-19 by user: Dependabot alerts/security updates
              are a repo setting, not a skill defect. The deliverable is the
              skill and the enablement instructions it now ships
              (SECURITY_GATE.md, "Enabling Dependabot alerts"); this repo's own
              setting is the owner's to flip and does not gate shipping them.
              Unverified from this session either way — no credential reaches
              GET /repos/.../dependabot/alerts. Re-opens if the finding's
              context changes
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
📦 RELEASE    ✅ PR #52 — retitled from its bookkeeping origin to the 2.28.0
              release PR, out of draft. This file ships inside it (Gate 5
              step 3), not as a bookkeeping PR afterwards
🚀 SHIP       ⏳ plan: merge #52, confirm CI green on the merge commit, verify
              VERSION reads 2.28.0 in it, then the USER pushes the tag
              (credential carve-out, both modes). Release workflow publishes;
              Claude verifies tag/release/assets. The post-tag ✅ line folds
              into the next release's PR (SHIP_REFERENCE.md step 7)

⏳ is the honest state here, not a gap: the tag does not exist yet, so no
commit preceding it can claim it does.
