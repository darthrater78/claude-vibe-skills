# Update Reference

Loaded by the dev-skills skill **only when the version check finds this copy
behind the latest release** (`SESSION_START.md`, version check), before the
update choice is offered. Section numbers point at `SKILL.md`.

---

## Updating the skill — the install always comes whole from the release

The source is the latest tag's release asset,
`https://github.com/darthrater78/claude-vibe-skills/releases/download/v<latest>/dev-skills.skill`,
pinned to the version the check found, never `latest/` (which can move
between the check and the download) and never individual files patched from
the repo. The `.skill` file is a zip with the skill files at its root. Every
install **replaces the whole directory**: stale files from the old version
must not survive. It refuses any target whose last path component is not
`dev-skills`, so a wrong or empty `D` can never delete anything else. It **checks the `version:` line in the downloaded
`SKILL.md` before touching the installed copy**, so a failed download or
wrong asset leaves the old install in place (fail closed).

Where the skill is installed decides what can be offered. Read it from
this skill's base directory:

| Base directory | Installed by | Offer |
|---|---|---|
| `~/.claude/skills/dev-skills` | the user, by hand | 1, 2, 3 |
| `<repo>/.claude/skills/dev-skills` | the project | 1, 2, 3. The install changes tracked files, so it is a commit and goes through commit approval (`SKILL.md` Section 1) |
| a path containing `/skills/synced/` | claude.ai sync (web, Desktop, CLI) | re-upload only: **Customize → Skills** on claude.ai. A local overwrite is replaced by the next sync. Option 1 becomes downloading the `.skill` file into the working directory for the user to upload |
| anything else (plugin, unknown) | unknown | 2 and 3, and name the path |

In a **remote container**, `~/.claude` dies with the container, so option 1
only lasts for this session: say so. A synced or project install is the
durable fix there.

**Option 1, Claude installs it** (bash; run it as one call after the user
picks it, with `D` set to this skill's base directory and `V` to the latest
version without the `v`):

```bash
V=2.19.0 D="$HOME/.claude/skills/dev-skills"; t=$(mktemp -d) \
  && case "$D" in */dev-skills) ;; *) echo "refusing: $D is not a dev-skills dir" >&2; false ;; esac \
  && curl -fsSL -o "$t/dev-skills.skill" "https://github.com/darthrater78/claude-vibe-skills/releases/download/v$V/dev-skills.skill" \
  && unzip -q "$t/dev-skills.skill" -d "$t/new" \
  && grep -qx "version: $V" "$t/new/SKILL.md" \
  && rm -rf "$D" && mkdir -p "$(dirname "$D")" && mv "$t/new" "$D" \
  && grep -m1 '^version:' "$D/SKILL.md"; rm -rf "$t"
```

On a Windows host, run the PowerShell block below through the shell tool
instead. Report the installed version from the last line, not from the
command's exit status.

**Option 2, the user installs it:** one block for the user's shell (step 2;
ask it now if it has not been asked). The block carries no `cd`. For bash,
zsh, Git Bash, WSL, macOS and Termux, use the block above. For Windows
PowerShell and pwsh:

```powershell
$V='2.19.0'; $D="$HOME\.claude\skills\dev-skills"; $t=Join-Path ([IO.Path]::GetTempPath()) "dev-skills-$V"; Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue; New-Item -ItemType Directory $t | Out-Null; Invoke-WebRequest -UseBasicParsing "https://github.com/darthrater78/claude-vibe-skills/releases/download/v$V/dev-skills.skill" -OutFile "$t\dev-skills.zip"; Expand-Archive "$t\dev-skills.zip" "$t\new"; if ((Split-Path $D -Leaf) -eq 'dev-skills' -and (Select-String -Path "$t\new\SKILL.md" -Pattern "^version: $V$" -Quiet)) { Remove-Item -Recurse -Force $D -ErrorAction SilentlyContinue; Move-Item "$t\new" $D; Select-String -Path "$D\SKILL.md" -Pattern '^version:' | Select-Object -First 1 } else { Write-Error "Downloaded file is not v$V; nothing was changed." }; Remove-Item -Recurse -Force $t -ErrorAction SilentlyContinue
```

(`Expand-Archive` only accepts a `.zip` name, hence the rename.) For a
project install, set `D` to the project's `.claude/skills/dev-skills`.

**After either option, the running session still has the old version
loaded.** Say so, and offer the choice: start a new session to load the new
version (a handoff summary, `SKILL.md` §5.6, if work is in flight), or carry
on here with the `⚠️ outdated` marker as for option 3.
