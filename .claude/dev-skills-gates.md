# Dev Skills gate state
Track: release sequence
Version: 2.15.0
Updated: 2026-09-08

🔢 VERSION    ✅ all refs at 2.15.0; prev version v2.14.0 tagged on remote
🔨 BUILD      ✅ scripts/validate.sh green; bundle rebuilt; both workflows parse;
                 default-branch guard tested both ways (accepts master, rejects unmerged)
🔒 SECURITY   ✅ 0 Critical, 0 High, 0 Medium, 0 Low — re-scanned incl. CI changes
📄 DOCS       ✅ CHANGELOG 2.15.0 (Fixed/Security/Added/Changed); README updated
📦 RELEASE    ⏳ awaiting commit approval
🚀 SHIP       ⬜ tag push goes to the user (403 rule)

Follow-up agreed: retro-tag v2.13.0 (fa8e359) and v2.12.0 (c0e9e6d) — both
verified on master, so both pass the new default-branch guard.
