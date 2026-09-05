# Shell Command Reference

This file is loaded on demand by the dev-skills skill when git commands need to
be formatted for the user's shell environment (Section 5.7). It contains the
`cd` format table, shell-specific syntax rules, Termux clone flow, and example
command blocks for each supported shell.

---

## `cd` format by shell

| Shell | `cd` format |
|---|---|
| Windows PowerShell | `cd "C:\Users\steve\Desktop\git\project-name"` |
| Linux PowerShell (pwsh) | `cd "/home/user/projects/project-name"` |
| Git Bash (Windows) | `cd "/c/Users/steve/Desktop/git/project-name"` |
| Termux (Android) | `cd ~/storage/shared/projects/project-name` |
| macOS Terminal | `cd ~/projects/project-name` |
| Linux Terminal | `cd ~/projects/project-name` |
| WSL | `cd /mnt/c/Users/steve/Desktop/git/project-name` |

Use the actual project path from the current working directory. For Git Bash,
convert Windows paths (`C:\foo\bar`) to Unix-style (`/c/foo/bar`). For WSL,
convert to `/mnt/c/...` form.

---

## Shell-specific syntax

- **Multi-line strings:** PowerShell uses here-strings (`@'...'@`), Bash/Termux/
  macOS/Linux use heredocs or `$'...'`, Git Bash follows Bash rules
- **Variable expansion:** PowerShell uses `$var`, Bash uses `$var` or `${var}` —
  but quoting rules differ
- **Command chaining:** PowerShell uses `;` (no `&&`), Bash/Git Bash/Termux use
  `&&`
- **Line continuation:** PowerShell uses backtick (`` ` ``), Bash uses backslash
  (`\`)
- **Path separators:** PowerShell and Windows use `\`, everything else uses `/`
- **Termux quirks:** limited PATH, may need `pkg install` for tools like `gh`,
  smaller screen so keep commands concise

---

## Termux clone flow

On Termux (Android), the repo may not exist locally. When the user's shell is
Termux, every command block must account for this:
- **First time (repo not yet cloned):** start with `git clone <url>` then `cd`
  into the cloned directory. Use the repo URL stored at session start (Section 6,
  step 1).
- **Subsequent commands (repo already cloned):** start with `cd` then
  `git fetch origin && git pull origin <branch>` to sync before any work.

---

## Example output (Windows PowerShell)

```powershell
cd "C:\Users\steve\Desktop\git\claude-vibe-skills"
git checkout -b release/v2.10.0
git add -A
git commit -m @'
v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
'@
git push -u origin release/v2.10.0
```

## Example output (Git Bash)

```bash
cd "/c/Users/steve/Desktop/git/claude-vibe-skills"
git checkout -b release/v2.10.0
git add -A
git commit -m "v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push -u origin release/v2.10.0
```

## Example output (Termux — first time, repo not yet cloned)

```bash
cd ~/storage/shared/projects
git clone https://github.com/owner/repo.git
cd repo
git fetch origin && git pull origin main
git checkout -b release/v2.10.0
git add -A
git commit -m "v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push -u origin release/v2.10.0
```

## Example output (Termux — repo already cloned)

```bash
cd ~/storage/shared/projects/repo
git fetch origin && git pull origin main
git checkout -b release/v2.10.0
git add -A
git commit -m "v2.10.0 — git repo detection and branch enforcement

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
git push -u origin release/v2.10.0
```
