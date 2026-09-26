# Project Standards Reference

Loaded by the dev-skills skill **when a project or feature that a project
standard applies to is being designed** (`SKILL.md` §10), and by Gates 1, 3
and 4 when they check one. `SKILL.md` §10 lists them; this file holds each
rule in full and how to build it. Section numbers point at `SKILL.md`.

---

## The standards in full

1. **Encryption at rest is always considered.** The security section of every
   project (design notes, README "Security", Gate 3 output) states what is
   stored (database, config, uploads, tokens, backups), whether each is
   encrypted at rest, how, and where the key lives. "Not needed, because …" is
   an answer. Silence is not.
2. **Login means TOTP, 30-day trust, and a rescue path, offered.** Any project
   with user authentication gets all three offered: **TOTP 2FA**, a **"trust
   this device for 30 days"** option, and an **unlock / rescue feature** for a
   locked-out user. The user decides. Record which were accepted or declined.
3. **The main page links to GitHub and the latest release notes, without
   exception.** The README's top section, and the app's main page or screen
   when it has a UI, links to the GitHub repo and to the release notes for the
   current version (`GATE_REFERENCE.md`, Gate 1, checks 5–6). Gate 1 blocks
   without both.
4. **Docker projects offer Apprise notifications.** When the project ships as
   a Docker container, offer notifications through
   [Apprise](https://github.com/caronc/apprise): an `APPRISE_URLS` setting
   (env var or settings page, treated as a secret and never logged), the
   events worth sending (errors, updates, security events such as lockouts
   and new-device logins), and a "send test notification" action. The user
   decides. Record it.
5. **Docker projects document a compose quickstart.** The README's install
   section is a copy-paste quickstart, in this order:
   - **A one-line directory setup** that creates every host directory the
     compose file mounts and `cd`s into it.
   - **The compose block, with its explanations as `#` comments at the
     bottom of the YAML**, below the last setting, never inline or above it.
     There is one comment line per setting worth explaining (ports, env vars,
     each mount). The settings read clean, and the notes travel with the file.
   - **The filename, stated outright:** save it as `compose.yaml`. Then the
     start command.

   **Every volume is a bind mount under `/opt/docker/<container-name>/`**
   (the user's convention, and the example path). Never a named volume.
   **Never `network_mode: host` without the user's explicit permission** for
   that container, recorded with its reason; use `ports:` instead
   (`SECURITY_LINUX.md`). **The
   image tag is pinned to the current version**, never `latest`. Gate 1 treats
   it as a version reference, so a release that bumps the version bumps the
   compose file too (`GATE_REFERENCE.md`, Gate 1, check 2). Gate 4 checks the
   quickstart.


## Login: TOTP, 30-day trust, and a rescue path

- **TOTP 2FA:** RFC 6238, with the secrets encrypted at rest.
- **"Trust this device for 30 days":** a signed, `HttpOnly`/`Secure` cookie or
  token with a 30-day hard expiry, revoked on a password or 2FA change, with
  trusted devices listed and revocable.
- **Unlock / rescue:** single-use hashed recovery codes, plus an admin or CLI
  unlock that is logged.

All three are offered. The user decides, and the tracker's `Standards:` row
records which were accepted or declined.

## Docker compose quickstart — example

The order is the one in item 5 above: the directory setup, the
compose block with its notes as `#` comments at the bottom, then the filename
and the start command.

```bash
mkdir -p /opt/docker/myapp/{config,data} && cd /opt/docker/myapp
```

```yaml
services:
  myapp:
    image: ghcr.io/owner/myapp:1.4.2
    container_name: myapp
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - /opt/docker/myapp/config:/config
      - /opt/docker/myapp/data:/data

# image: pinned to this release (1.4.2), updated with every release
# ports: 8080 is the web UI. Change the left side for a different host port
# /opt/docker/myapp/config: settings, kept across upgrades
# /opt/docker/myapp/data: the database and uploads. Back this directory up
```

Save it as **`compose.yaml`** in `/opt/docker/myapp`, then run
`docker compose up -d`.
