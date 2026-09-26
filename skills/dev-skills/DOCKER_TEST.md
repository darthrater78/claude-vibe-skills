# Docker Test Runs — Gate 2 🔨

Loaded on demand by the dev-skills skill, **before Claude starts a test
container or hands the user a `docker run`/`docker compose up` for testing**
(Gate 2, `GATE_REFERENCE.md`, "Test artifact before merge"). A project with no
Docker build signal never needs it.

It holds the per-run test credentials, LAN-only publishing, temp-mount and
restart rules, the login echo, and teardown. The enforcement checks hold the
container side of it (`ENFORCEMENT.md`, A1, A2, A9, A10, A12).

---

**Docker test runs get fresh credentials, every run.** Each time a container
is started for testing — by Claude, or in a run command handed to the user —
generate a new username and password for that run and show them to the user
in the same message as the run command:

```bash
TEST_USER="test-$(LC_ALL=C tr -dc 'a-km-z2-9' </dev/urandom | head -c4)"
TEST_PASS="$(LC_ALL=C tr -dc 'A-HJ-NP-Za-km-z2-9' </dev/urandom | head -c12)"
# the address the host actually uses on the LAN, not the first of `hostname -I`,
# which can be a Docker bridge (172.17.0.1). macOS: ipconfig getifaddr en0
HOST_IP="$(ip -4 route get 1.1.1.1 | sed -n 's/.* src \([0-9.]*\).*/\1/p')"
case "$HOST_IP" in 10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*) ;; *) echo "not a private LAN IP: $HOST_IP" >&2; false ;; esac \
  && ! ip -4 -o addr show | grep -E 'docker0|br-|veth' | grep -qwF "$HOST_IP" \
  && docker run -d --rm --name <app>-test --label dev-skills.test="$CLAUDE_CODE_SESSION_ID" -p "$HOST_IP:8080:8080" \
  -e <APP_USER_VAR>="$TEST_USER" -e <APP_PASS_VAR>="$TEST_PASS" <image> \
  && sleep 3 && docker port <app>-test \
  && curl -fsS -o /dev/null "http://$HOST_IP:8080/" && echo "reachable at http://$HOST_IP:8080"
```

**Windows host (Docker Desktop).** There is no `ip` command, so read the LAN
IP with `Find-NetRoute`. From Git Bash (Claude's Bash tool on Windows):

```bash
TEST_USER="test-$(LC_ALL=C tr -dc 'a-km-z2-9' </dev/urandom | head -c4)"
TEST_PASS="$(LC_ALL=C tr -dc 'A-HJ-NP-Za-km-z2-9' </dev/urandom | head -c12)"
HOST_IP=$(powershell.exe -NoProfile -Command "(Find-NetRoute -RemoteIPAddress 1.1.1.1)[0].IPAddress" | tr -d '\r')
case "$HOST_IP" in 10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[01].*) ;; *) echo "not a private LAN IP: $HOST_IP" >&2; false ;; esac \
  && docker run -d --rm --name <app>-test --label dev-skills.test="$CLAUDE_CODE_SESSION_ID" -p "$HOST_IP:8080:8080" \
  -e <APP_USER_VAR>="$TEST_USER" -e <APP_PASS_VAR>="$TEST_PASS" <image> \
  && sleep 3 && docker port <app>-test \
  && curl -fsS -o /dev/null "http://$HOST_IP:8080/" && echo "reachable at http://$HOST_IP:8080"
```

From PowerShell (a block handed to a PowerShell user, or Claude's PowerShell
tool):

```powershell
$HOST_IP = (Find-NetRoute -RemoteIPAddress 1.1.1.1)[0].IPAddress
$TEST_USER = "test-" + -join ((50..57) + (97..107) + (109..122) | Get-Random -Count 4 | ForEach-Object { [char]$_ })
$TEST_PASS = -join ((50..57) + (65..72) + (74..78) + (80..90) + (97..107) + (109..122) | Get-Random -Count 12 | ForEach-Object { [char]$_ })
docker run -d --rm --name <app>-test --label dev-skills.test="$env:CLAUDE_CODE_SESSION_ID" -p "$($HOST_IP):8080:8080" `
  -e <APP_USER_VAR>="$TEST_USER" -e <APP_PASS_VAR>="$TEST_PASS" <image>
if ($?) { Start-Sleep 3; docker port <app>-test; curl.exe -fsS -o NUL "http://$($HOST_IP):8080/" }
if ($?) { "reachable at http://$($HOST_IP):8080" } else { "❌ STOPPED" }
```

`Find-NetRoute` returns the address Windows uses for its default route, the
same one the checks compare against (A1), so a Hyper-V or WSL virtual adapter
can't be picked by mistake. Temp-folder mounts and `--user` don't apply on
Windows (A9, A10 are Linux-host rules), but `--rm`, no restart policy and the
label do.

> 🔑 **Test login for this run**: throwaway, reachable on your network,
> and gone when the container is removed.
> URL: http://192.168.1.50:8080 · User: `test-k3xm` · Password: `Hq7vT2mWz9Ka`

- **Simple on purpose:** letters and digits only, with look-alikes (`0 O 1 l
  I`) left out, so they can be read off the screen and typed.
- **Passed to the variables the app actually reads for its login.** Find them
  in the Dockerfile `ENV`, the compose file, `.env.example`, or the docs; never
  guess a name. For compose, set them on the command line
  (`TEST_USER=… TEST_PASS=… docker compose up -d`) for a compose file that
  interpolates them. A compose file with credentials written into it is a
  Gate 3 finding (hardcoded secret), not something to work around.
- **Reachable on the network, always.** The user tests from other machines
  and devices, so a loopback-only container is useless to them.
  - **Never use `-p 127.0.0.1:…`**, and never hand over a `127.0.0.1` or
    `localhost` URL.
  - **Read the host's LAN IP from the default route** (`ip -4 route get
    1.1.1.1`, its `src`). Never guess it, and never take the first field of
    `hostname -I`: its order isn't fixed, and on a Docker host it lists
    bridge addresses (`172.17.0.1`, `172.18.0.1`, …) that pass the private-IP
    check but can't be reached from another machine. Reject an IP that
    belongs to `docker0`, a `br-*` bridge or a `veth`.
  - **Publish on that IP only** (`-p "$HOST_IP:8080:8080"`; for compose,
    `ports: - "${HOST_IP}:8080:8080"` with `HOST_IP` set on the command line).
  - **The app inside the container listens on `0.0.0.0`**, not `127.0.0.1`.
    An app bound to loopback inside the container is unreachable however the
    port is published. Set its host/bind variable (`HOST=0.0.0.0`,
    `--host 0.0.0.0`, …) from the Dockerfile, the compose file or the docs.
  - **A compose file that pins `127.0.0.1:` in `ports:`** is overridden for
    the test run with `${HOST_IP}`, and flagged to the user, never used as is.
  - **Read the binding back before handing over the URL.** `docker port
    <name>` (or `docker compose port <service> <port>`) must show the LAN IP.
    If it shows `127.0.0.1`, `localhost` or `0.0.0.0`, the run is wrong: fix
    it and restart. Then **check that the app answers** on
    `http://<LAN IP>:<port>`.
  - **The URL handed over is the one that `curl` just reached**, copied from
    that command's output, never retyped. A message that shows `127.0.0.1`,
    `localhost` or a bridge IP as the test URL is a Gate 2 failure, not a
    typo.
  - **On a remote container, where no LAN exists**, say so instead of showing
    a loopback URL.
- **Mounts are never root's in temp.** A bind mount under a temp folder is
  created first with `mkdir -p` and used by a container running as you
  (`--user "$(id -u):$(id -g)"`, or `PUID`/`PGID`). A container that has to
  run as root mounts from outside temp (`/opt/docker/<name>-test/`). Label
  every test container (`--label dev-skills.test=…`, or compose
  `-p dev-skills-test-<name>`) so leftovers are found (`ENFORCEMENT.md`,
  A10 and A12).
- **Gone when it stops.** Test containers run with `--rm` and **no restart
  policy**, and never bind-mount from a temp folder (`/tmp`, Claude's
  `/tmp/claude-*` scratchpad) with one. A reboot wipes `/tmp`, Docker
  restarts the container, and it recreates the mount as root, breaking Claude
  Code's temp directory for every later session (`ENFORCEMENT.md`, A9).
- **LAN only, never the internet.** A bare `-p 8080:8080` publishes on every
  interface, and Docker's published ports bypass host firewalls such as ufw.
  So bind to the LAN IP, and **if that IP is not private** (outside
  `10/8`, `172.16/12` and `192.168/16`, for example on a VPS), **stop and ask**
  rather than publish. Never set up a port-forward, tunnel or public bind.
  With the random single-run credentials and the teardown below, that is
  exposure enough for a test.
- **Never** written to a file in the repo, baked into the image (`ENV`/`ARG`),
  reused across runs or sessions, or the project's real credentials.
  Displaying them is the point: they die with the container.
- **An app with no login** needs none: say so, and record `test creds n/a (no
  login)`.

**Echo the login every time the test container changes, as the last thing in
the message.** Testing is iterative: fix, rebuild, restart, re-check. A login
shown once scrolls out of sight after the first round. So the 🔑 block above is
repeated, in full (URL, user and password), at the **bottom** of every message
in which the test container was started, rebuilt, restarted or recreated, or
in which the user is asked to try it again. That includes a rebuild after a
one-line fix. The bottom of the message is where the user's eye lands, so
nothing goes below it. A pointer such as "same login as before" or "see
above" does not count. When the credentials changed with the new container,
say so on the block's first line (`🔑 **New test login, the previous one no
longer works**`). If the current credentials are no longer in context, for
example after compaction, never reconstruct them from memory. Recreate the
container with fresh ones and show those.

**Tear it down once its purpose is served.** A container started here — or for
Gate 2's "prove a never-run release step" check (`GATE_REFERENCE.md`), or for
any other Gate 2 testing — is a running resource, not a fire-and-forget check. Stop and remove
it after the commit it verified is submitted, or immediately if the user
declines to try it: `docker stop <name>` (or `docker compose down` for a
compose stack), then `docker rm <name>` if it wasn't started with `--rm`.
Before the session ends (`SKILL.md` Section 8) or this gate closes, `docker ps` to
confirm nothing test-related is still running. Its credentials go with it.
