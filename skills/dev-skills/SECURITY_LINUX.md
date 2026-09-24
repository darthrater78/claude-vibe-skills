# Security Pattern Reference — Linux

Loaded alongside `SECURITY_REFERENCE.md` during Gate 3 and audit mode when
project environment detection (`WORKFLOW_REFERENCE.md`, Step 1) matches
Linux (including Docker/container projects). Contains Linux-only security
patterns — cross-platform and language-general patterns are in
`SECURITY_REFERENCE.md`.

---

## Rules — flag on sight during any coding session

**Linux-specific:**
- SUID/SGID: never set SUID casually — prefer Linux capabilities (`setcap`)
- Containers: never run as root, never `--privileged`, drop all caps and add back selectively,
  never mount Docker socket, pin base image digests not tags, use `--read-only` root filesystem
- **Host networking needs the user's explicit permission, every time.** Never
  write, run or present `network_mode: host`, `--network host` or `--net=host`
  (compose, `docker run`, Dockerfile docs, CI) without the user's own "yes" for
  that container, in both modes. It removes network isolation, and it publishes
  every port the app opens on every host interface, bypassing both the LAN-IP
  binding (`GATE_REFERENCE.md`, Gate 2) and host firewalls. Offer the published
  port (`-p <LAN IP>:<port>:<port>`) first, and say why host mode is needed if
  it really is (mDNS/SSDP discovery, DHCP). Record the approval and its reason
  on the tracker. An unapproved host-network line found in existing code is a
  High finding (`SECURITY_GATE.md`)
- Symlink/TOCTOU: use `mkstemp()`/`NamedTemporaryFile()`, not predictable temp paths;
  `O_NOFOLLOW` to refuse symlinks
- Systemd: add `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`,
  `CapabilityBoundingSet`; flag units running as root without hardening
- SSH keys: `0600` private / `0644` public, never commit to git, prefer Ed25519,
  avoid agent forwarding on untrusted hosts (use `ProxyJump`)
- Cron: absolute paths only, scripts not world-writable, no credentials in crontab
- SELinux/AppArmor: never `setenforce 0` or disable profiles as a fix — diagnose the policy
- Package repos: verify GPG fingerprints, reject unsigned repos, pin third-party packages

---

## Linux — SUID vs capabilities

```bash
# bad — full root privileges to anyone who runs it
chmod u+s /usr/local/bin/myapp

# good — only the specific capability needed
sudo setcap cap_net_bind_service=+ep /usr/local/bin/myapp
```

---

## Linux — Docker/container security

```dockerfile
# bad
FROM python:latest
# runs as root by default, unpinned tag

# good
FROM python:3.12-slim@sha256:abcd1234...
RUN useradd -r -s /bin/false appuser
USER appuser
COPY --chown=appuser:appuser . /app
```

---

## Linux — symlink/TOCTOU races

```python
# bad — predictable, race-prone
path = f"/tmp/myapp_{user_id}.txt"
if os.path.exists(path):
    with open(path) as f:
        data = f.read()

# good — atomic, unpredictable
import tempfile
with tempfile.NamedTemporaryFile(prefix="myapp_", delete=False) as f:
    f.write(data)
    safe_path = f.name
```

---

## Linux — systemd hardening

```ini
[Service]
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/lib/myapp
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
User=myapp
Group=myapp
```

---

## Linux — cron job security

```bash
# bad — relative path, world-writable script, credential in crontab
* * * * * backup.sh --password=hunter2

# good — absolute path, restricted script
* * * * * /usr/local/bin/backup.sh --config /etc/backup/config.env
# config.env is 0600 owned by the cron user
```
