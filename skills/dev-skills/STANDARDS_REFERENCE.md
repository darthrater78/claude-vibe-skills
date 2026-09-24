# Project Standards Reference

Loaded by the dev-skills skill **when a project or feature that a project
standard applies to is being designed** (`SKILL.md` §10), and by Gates 1, 3
and 4 when they check one. The rules themselves are in `SKILL.md` §10; this
file holds how to build them. Section numbers point at `SKILL.md`.

---

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

The order is the one in `SKILL.md` §10, item 5: the directory setup, the
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
