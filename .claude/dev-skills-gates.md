# Dev Skills gate state
Track: release sequence
Mode: manual
Version: 2.26.0
Updated: 2026-09-19 (rev 2)

Env: remote container | Branch: claude/skill-automatic-mode-i371w2 | Default: master

🔢 VERSION    ✅ 2.26.0 — validate.sh confirms VERSION, SKILL.md frontmatter,
              session banner and README agree; v2.25.0 confirmed tagged on
              remote. MINOR: one feat (semi-autonomous mode), no breaking change
🔨 BUILD      ✅ build-skill.sh rebuilt the bundle, validate.sh green
              (bundle byte-matches source, version 2.26.0); handoff n/a
              (no Docker/.exe/.apk signal in this repo)
🔒 SECURITY   ✅ 0 Critical, 0 High — docs-only diff (markdown + VERSION +
              rebuilt bundle), no code, no deps, no secrets. Policy review
              of the new mode: see CHANGELOG 2.26.0. Rev 2 tightens it —
              the tag push and ref deletions stay with the user in both
              modes; the tag block now carries a full action report
📄 DOCS       ✅ CHANGELOG 2.26.0 entry; README modes section (two
              checkpoints) + Remote Control section, size table, shortcut
              table, what's-new; hooks/README coverage note
📦 RELEASE    ⬜ branch pushed; PR not opened (not requested)
🚀 SHIP       ⬜
