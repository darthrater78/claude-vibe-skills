# Dev Skills gate state
Track: release sequence
Version: 2.25.0
Updated: 2026-09-18

Env: local | Branch: feature/dev-skills-2.25.0 | Default: master

🔢 VERSION    ✅ 2.25.0 — validate.sh confirms all refs agree; v2.24.0 tag
              confirmed on remote at bc37ae3
🔨 BUILD      ✅ build-skill.sh + validate.sh passed; handoff n/a (no
              Docker/.exe/.apk signal in this repo)
🔒 SECURITY   ✅ 0 Critical, 0 High — only code change is the hook's new
              awk block-parser (no eval/exec/network/secrets, fixed gate
              names only, fails closed); reproduced the reported bug and
              confirmed the fix, no regression on the genuine-denial case
📄 DOCS       ✅ CHANGELOG 2.25.0 entry; README/CONTRIBUTING/hooks-README
              all updated; validate.sh clean
📦 RELEASE    ⬜
🚀 SHIP       ⬜
