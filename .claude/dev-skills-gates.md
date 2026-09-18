# Dev Skills gate state
Track: release sequence
Version: 2.25.0
Updated: 2026-09-18

Env: local | Branch: master | Default: master

🔢 VERSION    ✅ 2.25.0 — validate.sh confirms all refs agree; v2.24.0 tag
              confirmed on remote at bc37ae3
🔨 BUILD      ✅ build-skill.sh + validate.sh passed; handoff n/a (no
              Docker/.exe/.apk signal in this repo)
🔒 SECURITY   ✅ 0 Critical, 0 High — hook's new awk block-parser reviewed
              (no eval/exec/network/secrets, fixed gate names only, fails
              closed); bug reproduced and fix confirmed, no regression
📄 DOCS       ✅ CHANGELOG 2.25.0 entry; README/CONTRIBUTING/hooks-README
              updated; validate.sh clean
📦 RELEASE    ✅ PR #46 merged (c3a49f7); merge state + CI on merge commit
              confirmed before the tag was handed over
🚀 SHIP       ✅ tag v2.25.0 confirmed on c3a49f7 (matches merge commit
              exactly); "Publish release" workflow succeeded; release
              asset content verified identical to local rebuild via
              decompress + diff (raw zip bytes differ — writestr()
              stamps build time into the zip, expected, not a defect);
              release notes auto-extracted from CHANGELOG and correct
