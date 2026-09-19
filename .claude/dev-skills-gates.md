# Dev Skills gate state
Track: work commit (tracker bookkeeping — no version bump, no artifact, no tag)
Mode: manual
Version: 2.27.0
Updated: 2026-09-19

Env: remote container | Branch: claude/cost-optimization-review-1oesyw | Default: master

Release sequence for v2.27.0 — CLOSED, all six gates passed:

🔢 VERSION    ✅ 2.27.0 across VERSION, SKILL.md frontmatter, banner, README;
              v2.26.0 was tagged at a55504f. MINOR: one perf, no breaking
              change. The banner now lives in SESSION_START.md; validate.sh
              greps skills/dev-skills/*.md and follows it there
🔨 BUILD      ✅ validate.sh green, including the new per-file size ceilings.
              Ceiling enforcement tested end to end: appended 4KB to SKILL.md,
              got "FAIL: SKILL.md is 65KB, over its 64KB ceiling", restored
🔒 SECURITY   ✅ 0 Critical, 0 High — Markdown plus two Bash scripts, no
              dependency, network or credential surface added. bash -n clean
              on both; hooks/gate-preflight.sh unmodified
              📝 Medium, open: shellcheck unavailable in this container, so
              scripts/validate.sh and build-skill.sh were not linted
              📝 Medium, open, pre-existing (2 releases old): no
              .github/dependabot.yml — nothing keeps the SHA-pinned
              actions/checkout current
📄 DOCS       ✅ CHANGELOG 2.27.0; README size table rebuilt to 21 rows and
              the second tiering rule added; all cross-references repointed
📦 RELEASE    ✅ PR #51 merged as dc1bbea; validate.yml run 59 green on the
              merge commit itself
🚀 SHIP       ✅ tag v2.27.0 confirmed on remote at dc1bbea, matching master
              HEAD and the merge commit exactly; "Publish release" run 18
              succeeded; release notes auto-extracted, correct; asset
              dev-skills.skill attached and verified by download — all 21
              entries byte-identical to master's source

Split verification (v2.27.0): every workflow-template line diffed against the
pre-split tree — 0 missing. For the gate split, the only 20 changed lines are
the deliberate ones: the self-check list, the version banner and release URL,
the repointed cross-references, and one renamed heading.

📝 Noted for the next release — the bundle is not a reproducible build.
scripts/build-skill.sh uses zipfile.writestr, which stamps each entry with the
build time, so two builds of identical content produce different archive
bytes. The released asset hashed b45182c3… where master's committed copy
hashes 3d31c5f9…, with all 21 entries identical. A sha256 comparison of the
archive therefore proves nothing; compare entries, as 🚀 above did. The
v2.26.0 tracker's "sha256 matches the API digest" line could not have been
accurate as written. Fixable with a fixed date_time in the ZipInfo.

This commit's own gates (work-commit track):
🔒 SECURITY   ✅ tracker text only
🔢 🔨 📄       ➖ N/A — no version bump, no build, no doc claims changed
📦 🚀          ➖ N/A — no version/artifact/tag involved, bookkeeping only
