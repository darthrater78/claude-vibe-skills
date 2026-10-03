#!/usr/bin/env python3
"""Tests for skills/dev-skills/checks/enforce.py.

Every "blocks" and "lets through" line in ENFORCEMENT.md has a case here, so a
check cannot get weaker without this failing. Run by scripts/validate.sh and CI.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENFORCE = os.path.join(HERE, "..", "skills", "dev-skills", "checks", "enforce.py")
SKILL_MD = os.path.join(HERE, "..", "skills", "dev-skills", "SKILL.md")

GATES_ALL = """# Dev Skills gate state
Track: release sequence
Mode: manual
Origin: owner/repo (not a fork)

🔢 VERSION    ✅ all refs at 1.2.0
🔨 BUILD      ➖ N/A — no build system
🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High
📄 DOCS       ✅
📦 RELEASE    ✅ PR #5
🚀 SHIP       ⬜
"""
GATES_NONE = """# Dev Skills gate state
Mode: manual
Origin: owner/repo (not a fork)
Previous: v1.1.0 all gates ✅ — VERSION BUILD SECURITY DOCS RELEASE SHIP
Standards: BUILD docs ✅

🔢 VERSION    ⬜
🔨 BUILD      ⬜
🔒 SECURITY   ⬜
  last session: ✅ on an old commit
📄 DOCS       ⬜
📦 RELEASE    ⬜
🚀 SHIP       ⬜
"""
GATES_WORK = GATES_NONE.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ✅ 0 open")
GATES_OPEN_LOW = GATES_NONE.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ⏳ open — 0 Critical, 0 High, 4 Medium, 5 Low")
GATES_OPEN_HIGH = GATES_NONE.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ⏳ open — 0 Critical, 1 High, 2 Medium")
GATES_OPEN_10C = GATES_NONE.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ⏳ open — 10 Critical, 0 High")
GATES_OPEN_ALL = GATES_ALL.replace("🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High", "🔒 SECURITY   ⏳ open — 0 Critical, 0 High, 1 Medium")
GATES_SEMI = GATES_NONE.replace("Mode: manual", "Mode: semi-autonomous (approved 2026-09-24)")
GATES_UNCHOSEN = GATES_ALL.replace("Mode: manual", "Mode: unchosen")
GATES_DECLINED = GATES_NONE.replace("Mode: manual", "Mode: manual\nHook enforcement: declined (2026-09-24)")
GATES_FORK = GATES_ALL.replace("owner/repo (not a fork)", "me/repo (fork of up/repo)")
GATES_WORK_MERGE = """# Dev Skills gate state
Track: work commit
Mode: manual
Origin: owner/repo (not a fork)

🔢 VERSION    ➖ no publishing intent — docs typo
🔨 BUILD      ➖ N/A — no build system
🔒 SECURITY   ✅ 0 open
📄 DOCS       ✅ claims checked
📦 RELEASE    ➖ no publishing intent
🚀 SHIP       ➖ no publishing intent
"""
GATES_HOSTNET = GATES_ALL + "Host network: hass approved 2026-09-24 — mDNS discovery\n"


def lan() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("1.1.1.1", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


LAN = lan()
TMP = tempfile.mkdtemp(prefix="dsk-tmp-")


def repo(gates: str | None, branch: str = "feat/x", compose: str | None = None) -> str:
    d = tempfile.mkdtemp(prefix="dsk-test-")
    os.makedirs(os.path.join(d, ".git", "refs", "remotes", "origin"))
    os.makedirs(os.path.join(d, ".claude"))
    with open(os.path.join(d, ".git", "HEAD"), "w", encoding="utf-8") as fh:
        fh.write(f"ref: refs/heads/{branch}\n")
    with open(os.path.join(d, ".git", "refs", "remotes", "origin", "HEAD"), "w", encoding="utf-8") as fh:
        fh.write("ref: refs/remotes/origin/master\n")
    if gates is not None:
        with open(os.path.join(d, ".dev-skills-gates.md"), "w", encoding="utf-8") as fh:
            fh.write(gates)
    if compose:
        with open(os.path.join(d, "compose.yaml"), "w", encoding="utf-8") as fh:
            fh.write(compose)
    return d


def run(mode: str, payload: dict, env: dict | None = None) -> str:
    e = dict(os.environ)
    e.pop("CLAUDE_PLUGIN_ROOT", None)
    e.pop("CLAUDE_CODE_REMOTE", None)
    e["TMPDIR"] = TMP  # keep the checks' marker and counters out of the real temp folder
    # Windows: Python's stdin/stdout use the ANSI code page, not UTF-8, while Claude
    # Code sends raw UTF-8 JSON (emoji not escaped). Every case runs that way.
    e["PYTHONIOENCODING"] = "cp1252"
    e["PYTHONUTF8"] = "0"
    e.update(env or {})
    p = subprocess.run([sys.executable, ENFORCE, mode], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       capture_output=True, env=e, timeout=20)
    if p.returncode != 0:
        return "error:" + p.stderr.decode("utf-8", "replace")
    out = p.stdout.decode("utf-8").strip()
    if not out:
        return "allow"
    obj = json.loads(out)
    hso = obj.get("hookSpecificOutput", {})
    if hso.get("permissionDecision"):
        return hso["permissionDecision"]
    if obj.get("decision") == "block":
        return "block"
    if hso.get("additionalContext"):
        return "context"
    if obj.get("systemMessage"):
        return "warn"
    return "allow"


def header_fallback(payload: dict) -> str:
    """Run the PreToolUse command from SKILL.md's header with the checks file missing."""
    lines, on, cmd = open(SKILL_MD, encoding="utf-8").read().split("\n"), False, []
    for i, ln in enumerate(lines):
        if ln.startswith("  PreToolUse:"):
            on = True
        elif on and ln.startswith("  PostToolUse:"):
            break
        elif on and ln.strip() == "command: >-":
            for x in lines[i + 1:]:
                if not x.startswith("            "):
                    break
                cmd.append(x.strip())
            break
    empty = tempfile.mkdtemp(prefix="dsk-empty-")
    e = dict(os.environ, CLAUDE_PLUGIN_ROOT=empty)
    p = subprocess.run(["bash", "-c", " ".join(cmd)], input=json.dumps(payload), capture_output=True,
                       text=True, env=e, timeout=20)
    return {0: "allow", 2: "block"}.get(p.returncode, f"error:{p.returncode}:{p.stderr}")


def bash(cmd: str, gates: str | None = GATES_ALL, **kw: str) -> str:
    d = repo(gates, **{k: v for k, v in kw.items() if k in ("branch", "compose")})
    return run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": d, "tool_input": {"command": cmd}})


def pwsh(cmd: str, gates: str | None = GATES_NONE) -> str:
    return run("pre-tool", {"session_id": "t", "tool_name": "PowerShell", "cwd": repo(gates), "tool_input": {"command": cmd}})


ENC = base64.b64encode("git commit -m x".encode("utf-16-le")).decode()


def bash_cd_other(cmd: str, other_gates: str | None = None) -> str:
    """Session in a repo whose gates pass; the command cd's into another repo."""
    here = repo(GATES_WORK)
    other = repo(other_gates)
    return run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": here,
                            "tool_input": {"command": cmd.format(other=other)}})


def bash_docker(cmd: str, build_row: str, gates: str = GATES_ALL) -> str:
    d = repo(gates.replace("🔨 BUILD      ➖ N/A — no build system", build_row))
    with open(os.path.join(d, "Dockerfile"), "w", encoding="utf-8") as fh:
        fh.write("FROM alpine:3.20\n")
    return run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": d, "tool_input": {"command": cmd}})


def bash_alias(cmd: str, config: str, gates: str | None = GATES_NONE) -> str:
    """A git command in a repo whose .git/config defines aliases."""
    d = repo(gates)
    with open(os.path.join(d, ".git", "config"), "w", encoding="utf-8") as fh:
        fh.write(config)
    return run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": d, "tool_input": {"command": cmd}})


def bash_files(cmd: str, files: dict[str, str], gates: str | None = GATES_ALL, branch: str = "feat/x") -> str:
    """A command in a repo whose working tree holds these files."""
    d = repo(gates, branch=branch)
    for rel, body in files.items():
        os.makedirs(os.path.dirname(os.path.join(d, rel)) or d, exist_ok=True)
        with open(os.path.join(d, rel), "w", encoding="utf-8") as fh:
            fh.write(body)
    return run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": d, "tool_input": {"command": cmd}})


def edit(tool: str, inp: dict, gates: str | None = GATES_ALL) -> str:
    d = repo(gates)
    inp = dict(inp)
    inp["file_path"] = os.path.join(d, inp["file_path"])
    return run("pre-tool", {"session_id": "t", "tool_name": tool, "cwd": d, "tool_input": inp})


GOOD_WF = """name: CI
on: [push]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - name: Test
        env:
          REF: ${{ github.ref_name }}
        run: |
          set -euo pipefail
          echo "$REF"
"""
BAD_WF = """name: Legacy
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "${{ github.head_ref }}"
"""

GRADLE_WF = GOOD_WF.replace("      - name: Test\n", """      - uses: actions/setup-java@de7274f081f381c8f8158605e0321c36c376e2e6 # v6.0.1
        with:
          distribution: temurin
          java-version: '17'
          cache: gradle
      - uses: gradle/actions/wrapper-validation@9c971963bec38e04b3d30dcc455b5382be2fdbfb # v6.3.0
      - name: Build with gradlew
        run: ./gradlew assembleDebug
      - name: Test
""")
GATES_APK = GATES_ALL.replace("🔨 BUILD      ➖ N/A — no build system",
    "🔨 BUILD      ✅ assembleDebug\n    handoff: APK offered\n    test artifact: app-debug.apk @ abc1234")
WAIVED_GATES = GATES_ALL.replace("🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High",
    "🔒 SECURITY   ✅ 0 open — 0 Critical, 0 High (fixed H1; waived M1)\n"
    "    🔕 waived 2026-09-26 by user: M1 feature work, scheduled for 1.3.0\n"
    "    open notes (fix or waive): none")

def wf(tool: str, new: str, existing: str | None = None, gates: str | None = GATES_ALL,
       name: str = "ci.yml") -> str:
    """A Write or Edit of .github/workflows/<name>. For Edit, `new` replaces all of `existing`."""
    d = repo(gates)
    path = os.path.join(d, ".github", "workflows", name)
    os.makedirs(os.path.dirname(path))
    if existing is not None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(existing)
    inp = ({"file_path": path, "content": new} if tool == "Write"
           else {"file_path": path, "old_string": existing, "new_string": new})
    return run("pre-tool", {"session_id": "t", "tool_name": tool, "cwd": d, "tool_input": inp})


def stop(msg: str, gates: str | None = GATES_ALL, prompt: str = "p1") -> str:
    d = repo(gates)
    return run("stop", {"session_id": "t-stop", "prompt_id": prompt + d[-6:], "cwd": d,
                        "last_assistant_message": msg, "stop_hook_active": False})


def stop_files(msg: str, files: dict[str, str], gates: str | None = GATES_ALL) -> str:
    """The Stop check on a reply, in a repo whose working tree holds these files."""
    d = repo(gates)
    for rel, body in files.items():
        with open(os.path.join(d, rel), "w", encoding="utf-8") as fh:
            fh.write(body)
    return run("stop", {"session_id": "t-stop", "prompt_id": "pf" + d[-6:], "cwd": d,
                        "last_assistant_message": msg, "stop_hook_active": False})


RUN_OK = """`🔢✅ 🔨➖ 🔒✅ 📄✅ 📦⬜ 🚀⬜ · work commit · manual`

### ▶️ RUN THIS — commit + push · 1 block
```bash
# ════════ ▶️ START: commit + push ════════
git add -A && git commit -m "feat: x" && git push -u origin feat/x \\
  && echo "✅ DONE" || echo "❌ STOPPED"
# ════════ ⏹️ END ════════
```
### ⏹️ END — nothing else to run
No need to reply.
"""

CASES = [
    # --- A1: LAN-only ports
    ("A1 loopback port", lambda: bash("docker run -d -p 127.0.0.1:8080:8080 img"), "deny"),
    ("A1 localhost port", lambda: bash("docker run -d -p localhost:8080:8080 img"), "deny"),
    ("A1 0.0.0.0 port", lambda: bash("docker run -d -p 0.0.0.0:8080:8080 img"), "deny"),
    ("A1 bare port", lambda: bash("docker run -d -p 8080:8080 img"), "deny"),
    ("A1 --publish=bare", lambda: bash("docker run -d --publish=8080:8080 img"), "deny"),
    ("A1 -P all", lambda: bash("docker run -d -P img"), "deny"),
    ("A1 bridge IP", lambda: bash("docker run -d -p 172.17.0.1:8080:8080 img"), "deny"),
    ("A1 public IP", lambda: bash("docker run -d -p 8.8.8.8:8080:8080 img"), "deny"),
    ("A1 behind sudo", lambda: bash("sudo docker run -d -p 127.0.0.1:80:80 img"), "deny"),
    ("A1 LAN IP ok", lambda: bash(f"docker run --label dev-skills.test=t -d -p {LAN}:8080:8080 img"), "allow"),
    ("A1 route recipe ok", lambda: bash('HOST_IP="$(ip -4 route get 1.1.1.1 | sed -n \'s/.* src \\([0-9.]*\\).*/\\1/p\')" '
                                        '&& docker run --label dev-skills.test=t -d -p "$HOST_IP:8080:8080" img'), "allow"),
    ("A1 Windows recipe, Git Bash ok", lambda: bash('HOST_IP=$(powershell.exe -NoProfile -Command '
        '"(Find-NetRoute -RemoteIPAddress 1.1.1.1)[0].IPAddress" | tr -d \'\\r\') '
        '&& docker run --label dev-skills.test=t -d -p "$HOST_IP:8080:8080" img'), "allow"),
    ("A1 Windows recipe, PowerShell ok", lambda: pwsh('$HOST_IP = (Find-NetRoute -RemoteIPAddress 1.1.1.1)[0].IPAddress; '
        'docker run --label dev-skills.test=t -d -p "$($HOST_IP):8080:8080" img'), "allow"),
    ("A1 PowerShell HOST_IP without recipe", lambda: pwsh('docker run --label dev-skills.test=t -d -p "$($HOST_IP):8080:8080" img'), "deny"),
    ("A1 unknown var", lambda: bash('docker run -d -p "$IP:8080:8080" img'), "deny"),
    ("A1 no ports ok", lambda: bash("docker run --label dev-skills.test=t --rm img echo hi"), "allow"),
    ("A1 compose loopback", lambda: bash("docker compose up -d",
                                         compose='services:\n  app:\n    image: a:1\n    ports:\n      - "127.0.0.1:8080:80"\n'), "deny"),
    ("A1 compose bare", lambda: bash("docker compose up -d",
                                     compose='services:\n  app:\n    image: a:1\n    ports:\n      - "8080:80"\n'), "deny"),
    ("A1 compose LAN ok", lambda: bash("docker compose -p dev-skills-test-x up -d",
                                       compose=f'services:\n  app:\n    image: a:1\n    ports:\n      - "{LAN}:8080:80"\n'), "allow"),
    ("A1 compose HOST_IP literal", lambda: bash(f"HOST_IP={LAN} docker compose -p dev-skills-test-x up -d",
                                                compose='services:\n  app:\n    image: a:1\n    ports:\n      - "${HOST_IP}:8080:80"\n'), "allow"),
    ("A1 compose long syntax no host_ip", lambda: bash("docker compose up -d",
                                                       compose='services:\n  app:\n    image: a:1\n    ports:\n      - target: 80\n        published: 8080\n'), "deny"),
    # --- A2: host networking
    ("A2 --network host", lambda: bash(f"docker run -d --name x --network host img"), "deny"),
    ("A2 --net=host", lambda: bash("docker run -d --name x --net=host img"), "deny"),
    ("A2 approved", lambda: bash("docker run --label dev-skills.test=t -d --name hass --network host img", gates=GATES_HOSTNET), "allow"),
    ("A2 compose host", lambda: bash("docker compose up -d",
                                     compose="services:\n  app:\n    image: a:1\n    network_mode: host\n"), "deny"),
    ("A2 compose host approved", lambda: bash("docker compose -p dev-skills-test-x up -d", gates=GATES_HOSTNET,
                                              compose="services:\n  hass:\n    image: a:1\n    network_mode: host\n"), "allow"),
    # --- A9: test containers don't outlive the session
    ("A9 restart + /tmp mount", lambda: bash("docker run -d --restart unless-stopped -v /tmp/claude-1000/x/data:/data img"), "deny"),
    ("A9 --restart= + --mount bind", lambda: bash("docker run -d --restart=always --mount type=bind,source=/tmp/a,target=/d img"), "deny"),
    ("A9 restart + $TMPDIR", lambda: bash("docker run -d --restart on-failure:3 -v $TMPDIR/x:/d img"), "deny"),
    ("A9 --rm + /tmp ok", lambda: bash(f"mkdir -p {TMP}/m1 && docker run --rm -d --user 1000:1000 --label dev-skills.test=t -v {TMP}/m1:/d img"), "allow"),
    ("A9 restart + /opt/docker ok", lambda: bash("docker run --label dev-skills.test=t -d --restart unless-stopped -v /opt/docker/app/data:/data img"), "allow"),
    ("A9 restart + named volume ok", lambda: bash("docker run --label dev-skills.test=t -d --restart unless-stopped -v appdata:/data img"), "allow"),
    ("A9 compose restart + /tmp", lambda: bash("docker compose up -d",
                                               compose="services:\n  app:\n    image: a:1\n    restart: unless-stopped\n    volumes:\n      - /tmp/claude-1000/s/data:/data\n"), "deny"),
    ("A9 compose restart + long /tmp", lambda: bash("docker compose up -d",
                                                    compose="services:\n  app:\n    image: a:1\n    restart: always\n    volumes:\n      - type: bind\n        source: /var/tmp/x\n        target: /d\n"), "deny"),
    ("A9 compose restart no ok", lambda: bash(f"mkdir -p {TMP}/m2 && docker compose -p dev-skills-test-x up -d",
                                              compose=f"services:\n  app:\n    image: a:1\n    user: 1000:1000\n    restart: \"no\"\n    volumes:\n      - {TMP}/m2:/data\n"), "allow"),
    ("A9 compose restart + /opt ok", lambda: bash("docker compose -p dev-skills-test-x up -d",
                                                  compose="services:\n  app:\n    image: a:1\n    restart: unless-stopped\n    volumes:\n      - /opt/docker/app:/data\n"), "allow"),
    # --- A10: temp mounts are never root's
    ("A10 temp mount, not as user", lambda: bash(f"mkdir -p {TMP}/a && docker run --rm --label dev-skills.test=t -v {TMP}/a:/d img"), "deny"),
    ("A10 temp mount missing, no mkdir", lambda: bash(f"docker run --rm --user 1000:1000 --label dev-skills.test=t -v {TMP}/nope-{os.getpid()}:/d img"), "deny"),
    ("A10 temp mount root-owned", lambda: bash("docker run --rm --user 1000:1000 --label dev-skills.test=t -v /tmp:/d img")
     if os.stat("/tmp").st_uid != os.getuid() else "deny", "deny"),
    ("A10 PUID/PGID ok", lambda: bash(f"mkdir -p {TMP}/b && docker run --rm -e PUID=1000 -e PGID=1000 --label dev-skills.test=t -v {TMP}/b:/d img"), "allow"),
    ("A10 --mount missing source ok (docker refuses)", lambda: bash(f"docker run --rm --user 1:1 --label dev-skills.test=t --mount type=bind,source={TMP}/nope2,target=/d img"), "allow"),
    ("A10 root outside temp ok", lambda: bash("docker run --rm --label dev-skills.test=t -v /opt/docker/x-test:/d img"), "allow"),
    ("A10 compose temp not as user", lambda: bash(f"mkdir -p {TMP}/c && docker compose -p dev-skills-test-x up -d",
                                                  compose=f"services:\n  app:\n    image: a:1\n    volumes:\n      - {TMP}/c:/data\n"), "deny"),
    ("A10 compose PUID/PGID ok", lambda: bash(f"mkdir -p {TMP}/d && docker compose -p dev-skills-test-x up -d",
                                              compose=f"services:\n  app:\n    image: a:1\n    environment:\n      - PUID=1000\n      - PGID=1000\n    volumes:\n      - {TMP}/d:/data\n"), "allow"),
    # --- A12: test containers are labeled
    ("A12 unlabeled run", lambda: bash("docker run --rm img echo hi"), "deny"),
    ("A12 labeled run ok", lambda: bash("docker run --rm --label dev-skills.test=t img echo hi"), "allow"),
    ("A12 compose no test project", lambda: bash("docker compose up -d", compose="services:\n  app:\n    image: a:1\n"), "deny"),
    ("A12 compose test project ok", lambda: bash("docker compose -p dev-skills-test-x up -d", compose="services:\n  app:\n    image: a:1\n"), "allow"),
    ("A12 -p before up still checked", lambda: bash("docker compose -p dev-skills-test-x up -d",
                                                     compose='services:\n  app:\n    image: a:1\n    ports:\n      - "127.0.0.1:1:1"\n'), "deny"),
    ("A12 --context before run still checked", lambda: bash("docker --context x run -p 127.0.0.1:1:1 --label dev-skills.test=t img"), "deny"),
    ("A12 docker ps ok", lambda: bash("docker ps -a"), "allow"),
    # --- A4: gates, strict rows, wrappers
    ("A4 commit, gates pending (decoy lines)", lambda: bash("git commit -m 'feat: x'", gates=GATES_NONE), "deny"),
    ("A4 commit, SECURITY ok", lambda: bash("git commit -m 'feat: x'", gates=GATES_WORK), "allow"),
    ("A4 commit, only Medium/Low open ok", lambda: bash("git commit -m 'feat: x'", gates=GATES_OPEN_LOW), "allow"),
    ("A4 push feature branch, only Medium/Low open ok", lambda: bash("git push origin feat/x", gates=GATES_OPEN_LOW), "allow"),
    ("A4 commit, a High open", lambda: bash("git commit -m 'feat: x'", gates=GATES_OPEN_HIGH), "deny"),
    ("A4 commit, 10 Critical is not 0 Critical", lambda: bash("git commit -m 'feat: x'", gates=GATES_OPEN_10C), "deny"),
    ("A4 PR, only Medium/Low open", lambda: bash("gh pr create --fill", gates=GATES_OPEN_ALL), "deny"),
    ("A4 merge, only Medium/Low open", lambda: bash("gh pr merge 5 --merge", gates=GATES_OPEN_ALL), "deny"),
    ("A4 push master, only Medium/Low open", lambda: bash("git push origin master", gates=GATES_OPEN_ALL), "deny"),
    ("A4 bash -c wrapper", lambda: bash("bash -c 'git commit -m x'", gates=GATES_NONE), "deny"),
    ("A4 env prefix", lambda: bash("env A=1 git commit -m x", gates=GATES_NONE), "deny"),
    ("A4 sudo", lambda: bash("sudo git push origin feat/x", gates=GATES_NONE), "deny"),
    ("A4 git -C", lambda: bash("git -C /tmp commit -m x", gates=GATES_NONE), "deny"),
    ("A4 cd into a repo with no gate file", lambda: bash_cd_other("cd {other} && git commit -m x"), "deny"),
    ("A4 git -C into a repo with no gate file", lambda: bash_cd_other("git -C {other} commit -m x"), "deny"),
    ("A4 cd to a variable", lambda: bash('cd "$D" && git commit -m x', gates=GATES_WORK), "deny"),
    ("A4 cd into a passing repo ok", lambda: bash_cd_other("cd {other} && git commit -m x", other_gates=GATES_WORK), "allow"),
    ("A4 subshell", lambda: bash("echo $(git commit -m x)", gates=GATES_NONE), "deny"),
    ("A4 push -u origin master", lambda: bash("git push -u origin master", gates=GATES_WORK), "deny"),
    ("A4 push HEAD:master", lambda: bash("git push origin HEAD:master", gates=GATES_WORK), "deny"),
    ("A4 push feat:master", lambda: bash("git push origin feat:master", gates=GATES_WORK), "deny"),
    ("A4 bare push on master", lambda: bash("git push", gates=GATES_WORK, branch="master"), "deny"),
    ("A4 force push master", lambda: bash("git push --force origin master", gates=GATES_WORK), "deny"),
    ("A4 push feature ok", lambda: bash("git push -u origin feat/x", gates=GATES_WORK), "allow"),
    ("A4 GH_REPO merge", lambda: bash("GH_REPO=owner/repo gh pr merge 5 --merge", gates=GATES_WORK), "deny"),
    ("A4 gh api merge", lambda: bash("gh api -X PUT repos/owner/repo/pulls/5/merge", gates=GATES_WORK), "deny"),
    ("A4 merge all gates ok", lambda: bash("gh pr merge 5 --merge"), "allow"),
    ("A4 work-commit merge ok", lambda: bash("gh pr merge 5 --merge", gates=GATES_WORK_MERGE), "allow"),
    ("A4 work-commit PR ok", lambda: bash("gh pr create --title x --body y", gates=GATES_WORK_MERGE), "allow"),
    ("A4 no-intent ➖ needs work track", lambda: bash("gh pr merge 5 --merge",
        gates=GATES_WORK_MERGE.replace("Track: work commit", "Track: release sequence")), "deny"),
    ("A4 no-intent ➖ not for DOCS", lambda: bash("gh pr merge 5 --merge",
        gates=GATES_WORK_MERGE.replace("📄 DOCS       ✅ claims checked", "📄 DOCS       ➖ no publishing intent")), "deny"),
    ("A4 work track can't create a release", lambda: bash("gh release create v1.2.0", gates=GATES_WORK_MERGE), "deny"),
    ("C2 work track can't hand over a tag", lambda: stop(RUN_OK.replace(
        'git add -A && git commit -m "feat: x" && git push -u origin feat/x', "git tag v1.2.0 && git push origin v1.2.0"),
        gates=GATES_WORK_MERGE), "block"),
    ("A4 pr create needs docs", lambda: bash("gh pr create --title x", gates=GATES_WORK), "deny"),
    ("A4 docker repo: no handoff/artifact/creds", lambda: bash("gh pr merge 5 --merge",
                                                             gates=GATES_ALL.replace("🔨 BUILD      ➖ N/A — no build system", "🔨 BUILD      ✅ built"),
                                                             compose="services:\n  app:\n    image: a:1\n"), "allow"),
    ("A4 Dockerfile repo: BUILD ✅ without handoff", lambda: bash_docker("gh pr merge 5 --merge", "🔨 BUILD      ✅ built"), "deny"),
    ("A4 Dockerfile repo: no test creds", lambda: bash_docker("gh pr merge 5 --merge",
                                                              "🔨 BUILD      ✅ handoff offered · test artifact: img:pr-5 @ abc"), "deny"),
    ("A4 Dockerfile repo: all notes ok", lambda: bash_docker("gh pr merge 5 --merge",
                                                             "🔨 BUILD      ✅ handoff offered · test artifact: img:pr-5 @ abc · test creds: per run"), "allow"),
    ("A4 Dockerfile repo: work merge, no app code changed ok", lambda: bash_docker("gh pr merge 5 --merge",
        "🔨 BUILD      ✅ docs only\n  test artifact: n/a — no app code changed", gates=GATES_WORK_MERGE), "allow"),
    ("A4 Dockerfile repo: work merge still needs the n/a line", lambda: bash_docker("gh pr merge 5 --merge",
        "🔨 BUILD      ✅ docs only", gates=GATES_WORK_MERGE), "deny"),
    ("A4 Dockerfile repo: release can't use no app code changed", lambda: bash_docker("gh pr merge 5 --merge",
        "🔨 BUILD      ✅ docs only\n  handoff offered\n  test artifact: n/a — no app code changed\n  test creds: per run"), "deny"),
    ("A4 Dockerfile repo: n/a line doesn't block a release-track commit", lambda: bash_docker("git commit -m x",
        "🔨 BUILD      ✅ docs only\n  test artifact: n/a — no app code changed"), "allow"),
    ("A4 Dockerfile repo: notes on evidence lines ok", lambda: bash_docker("gh pr merge 5 --merge",
                                                                         "🔨 BUILD      ✅ built; handoff offered, user tried it\n  test artifact: img:pr-5 @ abc\n  test creds: generated per run"), "allow"),
    ("A4 ✅ on an evidence line doesn't pass", lambda: bash("git commit -m x",
                                                            gates=GATES_NONE.replace("Previous:", "Old:").replace("Standards: BUILD docs ✅", "")), "deny"),
    ("A4 open finding blocks release", lambda: bash("gh pr merge 5 --merge",
                                                    gates=GATES_ALL.replace("✅ 0 open", "✅ 1 open")), "deny"),
    ("A4 fork: wrong repo", lambda: bash("gh pr create --repo up/repo --title x", gates=GATES_FORK), "deny"),
    ("A4 fork: no --repo", lambda: bash("gh pr create --title x", gates=GATES_FORK), "deny"),
    ("A4 fork: right repo", lambda: bash("gh pr create --repo me/repo --title x", gates=GATES_FORK), "allow"),
    ("A4 no gate file", lambda: bash("git commit -m x", gates=None), "deny"),
    ("A4 reads ok", lambda: bash("git status && git log --oneline -3 && git diff", gates=GATES_NONE), "allow"),
    ("A4 grep text ok", lambda: bash("grep -n 'git push' README.md", gates=GATES_NONE), "allow"),
    # --- A5: mode
    ("A5 mode unchosen", lambda: bash("git commit -m x", gates=GATES_UNCHOSEN), "deny"),
    # --- A6: user-only refs
    ("A6 git tag", lambda: bash("git tag v1.2.0"), "deny"),
    ("A6 push tag", lambda: bash("git push origin v1.2.0"), "deny"),
    ("A6 push --tags", lambda: bash("git push --tags origin"), "deny"),
    ("A6 delete branch", lambda: bash("git push origin --delete feat/x"), "deny"),
    ("A6 delete :ref", lambda: bash("git push origin :feat/x"), "deny"),
    ("A6 merge --delete-branch", lambda: bash("gh pr merge 5 --merge --delete-branch"), "deny"),
    ("A6 gh api ref create", lambda: bash("gh api -X POST repos/o/r/git/refs -f ref=refs/tags/v1 -f sha=a"), "deny"),
    ("A6 release delete", lambda: bash("gh release delete v1.2.0"), "deny"),
    ("A6 list tags ok", lambda: bash("git tag -l && git ls-remote --tags origin"), "allow"),
    ("A6 local tag delete ok", lambda: bash("git tag -d v0.0.1"), "allow"),
    ("A6 MCP create_tag", lambda: run("pre-tool", {"session_id": "t", "tool_name": "mcp__github__create_tag",
                                                    "cwd": repo(GATES_ALL), "tool_input": {}}), "deny"),
    ("A4 MCP other server name", lambda: run("pre-tool", {"session_id": "t", "tool_name": "mcp__claude_ai_GitHub__merge_pull_request",
                                                          "cwd": repo(GATES_WORK), "tool_input": {"owner": "owner", "repo": "repo"}}), "deny"),
    # --- A4: writes that commit, merge or publish without `git commit` / `gh pr merge`
    ("A4 git merge commits", lambda: bash("git merge origin/master", gates=GATES_NONE), "deny"),
    ("A4 git merge -n still commits", lambda: bash("git merge -n origin/master", gates=GATES_NONE), "deny"),
    ("A4 git merge, SECURITY ok", lambda: bash("git merge origin/master", gates=GATES_WORK), "allow"),
    ("A4 git merge --ff-only ok", lambda: bash("git merge --ff-only origin/feat/x", gates=GATES_NONE), "allow"),
    ("A4 git merge --abort ok", lambda: bash("git merge --abort", gates=GATES_NONE), "allow"),
    ("A4 git merge-base ok", lambda: bash("git merge-base HEAD origin/master", gates=GATES_NONE), "allow"),
    ("A4 cherry-pick commits", lambda: bash("git cherry-pick abc123", gates=GATES_NONE), "deny"),
    ("A4 cherry-pick -n ok", lambda: bash("git cherry-pick -n abc123", gates=GATES_NONE), "allow"),
    ("A4 revert commits", lambda: bash("git revert HEAD", gates=GATES_NONE), "deny"),
    ("A4 am commits", lambda: bash("git am fix.patch", gates=GATES_NONE), "deny"),
    ("A4 gh release edit", lambda: bash("gh release edit v1.2.0 --notes x", gates=GATES_NONE), "deny"),
    ("A4 gh release edit after gates ok", lambda: bash("gh release edit v1.2.0 --notes x"), "allow"),
    ("A4 gh release upload on work track", lambda: bash("gh release upload v1 a.zip", gates=GATES_WORK_MERGE), "deny"),
    ("A4 gh repo sync remote", lambda: bash("gh repo sync owner/repo --source up/repo", gates=GATES_WORK), "deny"),
    ("A4 gh repo sync local ok", lambda: bash("gh repo sync --source up/repo", gates=GATES_NONE), "allow"),
    ("A4 gh api merges", lambda: bash("gh api -X POST repos/o/r/merges -f base=master -f head=x", gates=GATES_WORK), "deny"),
    ("A4 gh api update-branch", lambda: bash("gh api -X PUT repos/o/r/pulls/5/update-branch", gates=GATES_NONE), "deny"),
    ("A4 gh api create PR", lambda: bash("gh api repos/o/r/pulls -f head=x -f base=master", gates=GATES_WORK), "deny"),
    ("A4 gh api contents, default branch", lambda: bash("gh api -X PUT repos/o/r/contents/a.md -f message=x -f content=eA==", gates=GATES_WORK), "deny"),
    ("A4 gh api contents, on a branch ok", lambda: bash("gh api -X PUT repos/o/r/contents/a.md -f message=x -f content=eA== -f branch=feat/x", gates=GATES_WORK), "allow"),
    ("A4 gh api contents read ok", lambda: bash("gh api repos/o/r/contents/a.md", gates=GATES_NONE), "allow"),
    ("A4 MCP auto-merge", lambda: run("pre-tool", {"session_id": "t", "tool_name": "mcp__github__enable_pr_auto_merge",
                                                   "cwd": repo(GATES_WORK), "tool_input": {"owner": "owner", "repo": "repo"}}), "deny"),
    ("A4 MCP auto-merge after gates ok", lambda: run("pre-tool", {"session_id": "t", "tool_name": "mcp__github__enable_pr_auto_merge",
                                                                  "cwd": repo(GATES_ALL), "tool_input": {"owner": "owner", "repo": "repo"}}), "allow"),
    ("A4 MCP update branch", lambda: run("pre-tool", {"session_id": "t", "tool_name": "mcp__github__update_pull_request_branch",
                                                      "cwd": repo(GATES_NONE), "tool_input": {"owner": "owner", "repo": "repo"}}), "deny"),
    # --- A4 (2.44.1): gh pr update-branch, git pull of another branch, git aliases
    ("A4 gh pr update-branch", lambda: bash("gh pr update-branch 5", gates=GATES_NONE), "deny"),
    ("A4 gh pr update-branch, SECURITY ok", lambda: bash("gh pr update-branch 5", gates=GATES_WORK), "allow"),
    ("A4 pull of another branch merges", lambda: bash("git pull origin master", gates=GATES_NONE), "deny"),
    ("A4 pull of another branch, SECURITY ok", lambda: bash("git pull origin master", gates=GATES_WORK), "allow"),
    ("A4 pull of own branch ok", lambda: bash("git pull origin feat/x", gates=GATES_NONE), "allow"),
    ("A4 bare pull ok", lambda: bash("git pull", gates=GATES_NONE), "allow"),
    ("A4 pull --ff-only ok", lambda: bash("git pull --ff-only origin master", gates=GATES_NONE), "allow"),
    ("A4 pull --rebase ok", lambda: bash("git pull --rebase origin master", gates=GATES_NONE), "allow"),
    ("A4 inline alias to commit", lambda: bash("git -c alias.ci=commit ci -m x", gates=GATES_NONE), "deny"),
    ("A4 inline alias to merge", lambda: bash("git -c alias.m=merge m origin/master", gates=GATES_NONE), "deny"),
    ("A4 inline shell alias to push", lambda: bash("git -c 'alias.p=!git push origin master' p", gates=GATES_WORK), "deny"),
    ("A4 config alias to commit", lambda: bash_alias("git ci -m x", "[alias]\n\tci = commit\n"), "deny"),
    ("A4 config shell alias", lambda: bash_alias("git save", '[alias]\n  save = "!git add -A && git commit -m wip"\n'), "deny"),
    ("A4 alias of an alias", lambda: bash_alias("git c2 -m x", "[alias]\n\tc1 = commit\n\tc2 = c1\n"), "deny"),
    ("A4 config alias to a read ok", lambda: bash_alias("git st", "[alias]\n\tst = status -sb\n"), "allow"),
    ("A4 alias shadowing a builtin is ignored ok", lambda: bash_alias("git status", "[alias]\n\tstatus = commit -m x\n"), "allow"),
    ("A4 config alias, SECURITY ok", lambda: bash_alias("git ci -m x", "[alias]\n\tci = commit\n", gates=GATES_WORK), "allow"),
    ("A4 unparseable alias fails closed", lambda: bash_alias("git q", '[alias]\n\tq = commit -m "open\n', gates=GATES_WORK), "deny"),
    ("A4 other section not read as alias ok", lambda: bash_alias("git ci -m x", "[core]\n\tci = commit\n"), "allow"),
    # --- A4: no dev version reaches the default branch
    ("A4 push to master with a final version ok", lambda: bash_files("git push origin master",
        {"VERSION": "1.2.0\n"}), "allow"),
    ("A4 push to master with VERSION -dev", lambda: bash_files("git push origin master",
        {"VERSION": "1.2.0-dev.1\n"}), "deny"),
    ("A4 gh pr merge with package.json -rc", lambda: bash_files("gh pr merge 5 --merge",
        {"package.json": '{\n  "name": "x",\n  "version": "2.0.0-rc.1"\n}\n'}), "deny"),
    ("A4 merge with pyproject .dev", lambda: bash_files("gh pr merge 5 --squash",
        {"pyproject.toml": '[project]\nname = "x"\nversion = "1.2.0.dev3"\n'}), "deny"),
    ("A4 merge with gradle versionName -beta", lambda: bash_files("gh pr merge 5 --merge",
        {"app/build.gradle.kts": 'android {\n  defaultConfig {\n    versionName = "1.4.0-beta.2"\n  }\n}\n'},
        gates=GATES_APK), "deny"),
    ("A4 merge with gradle versionName final ok", lambda: bash_files("gh pr merge 5 --merge",
        {"app/build.gradle.kts": 'android {\n  defaultConfig {\n    versionName = "1.4.0"\n  }\n}\n'},
        gates=GATES_APK), "allow"),
    ("A4 merge with HA manifest b1", lambda: bash_files("gh pr merge 5 --merge",
        {"custom_components/blind/manifest.json": '{"domain": "blind", "version": "0.3.0b1"}\n'}), "deny"),
    ("A4 merge with CHANGELOG top entry -dev", lambda: bash_files("gh pr merge 5 --merge",
        {"CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n## [1.3.0-dev.2] - 2026-09-27\n\n## [1.2.0]\n"}), "deny"),
    ("A4 older dev entry under a final one ok", lambda: bash_files("gh pr merge 5 --merge",
        {"CHANGELOG.md": "# Changelog\n\n## [1.3.0] - 2026-09-27\n\n## [1.3.0-dev.2]\n", "VERSION": "1.3.0\n"}), "allow"),
    ("A4 dev version pushed to its feature branch ok", lambda: bash_files("git push -u origin feat/x",
        {"VERSION": "1.2.0-dev.1\n"}), "allow"),
    ("A4 gh api merge with dev version", lambda: bash_files("gh api -X PUT repos/owner/repo/pulls/5/merge",
        {"VERSION": "1.2.0-alpha.1\n"}), "deny"),
    ("A4 presented merge with dev version", lambda: stop_files(
        RUN_OK.replace('git add -A && git commit -m "feat: x" && git push -u origin feat/x', "gh pr merge 5 --merge"),
        {"VERSION": "1.2.0-dev.1\n"}), "block"),
    ("C2 presented git merge", lambda: stop(RUN_OK.replace('git add -A && git commit -m "feat: x" && git push -u origin feat/x', "git merge origin/master"),
                                            gates=GATES_NONE), "block"),
    # --- declined
    ("declined: commit allowed", lambda: bash("git commit -m x", gates=GATES_DECLINED), "allow"),
    ("declined: docker allowed", lambda: bash("docker run -p 127.0.0.1:80:80 img", gates=GATES_DECLINED), "allow"),
    # --- B5: gate file and settings edits
    ("B5 manual gate to ✅ ok", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                            "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 0 open"},
                                   gates=GATES_NONE), "allow"),
    ("B5 mode set ok", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                          "old_string": "Mode: unchosen", "new_string": "Mode: manual"},
                                 gates=GATES_UNCHOSEN), "allow"),
    ("B5 decline", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                         "old_string": "Mode: manual", "new_string": "Mode: manual\nHook enforcement: declined"}), "ask"),
    ("B5 host net approval", lambda: edit("Write", {"file_path": ".dev-skills-gates.md",
                                                    "content": GATES_ALL + "Host network: x approved today\n"}), "ask"),
    ("B5 gate to ⏳ ok", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                               "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ⏳ scanning"},
                                      gates=GATES_NONE), "allow"),
    ("B5 declined can't skip B5", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                                        "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 1 waived"},
                                               gates=GATES_DECLINED), "ask"),
    ("B5 edit beside an approved waiver ok", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
        "old_string": "(fixed H1; waived M1)", "new_string": "(fixed H1 L2; waived M1)"}, gates=WAIVED_GATES), "allow"),
    ("B5 whole-file rewrite keeping waivers ok", lambda: edit("Write", {"file_path": ".dev-skills-gates.md",
        "content": WAIVED_GATES.replace("📄 DOCS       ✅", "📄 DOCS       ✅ changelog 1.2.0")}, gates=WAIVED_GATES), "allow"),
    ("B5 new waiver record asks", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
        "old_string": "    open notes", "new_string": "    🔕 waived 2026-09-27 by user: M2 accepted\n    open notes"},
        gates=WAIVED_GATES), "ask"),
    ("B5 widening a waiver asks", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
        "old_string": "waived M1)", "new_string": "waived M1 M2)"}, gates=WAIVED_GATES), "ask"),
    ("B5 a second identical waiver clause asks", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
        "old_string": "📄 DOCS       ✅", "new_string": "📄 DOCS       ✅ (waived M1)"}, gates=WAIVED_GATES), "ask"),
    ("B5 adding test artifact n/a asks", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
        "old_string": "🔨 BUILD      ➖ N/A — no build system", "new_string": "🔨 BUILD      ✅ docs only\n  test artifact: n/a — no app code changed"}), "ask"),
    ("B5 settings file", lambda: edit("Write", {"file_path": ".claude/settings.json", "content": "{}"}), "ask"),
    ("B5 bash routine write to gate file ok", lambda: bash("echo 'x' >> .dev-skills-gates.md"), "allow"),
    ("B5 bash sed of a gate row ok", lambda: bash("sed -i 's/^🔒 SECURITY .*/🔒 SECURITY   ✅ 0 open/' .dev-skills-gates.md"), "allow"),
    ("B5 bash heredoc row update ok", lambda: bash("python3 - <<'EOF'\np='.dev-skills-gates.md'; s=open(p).read()\nopen(p,'w').write(s.replace('⬜','✅'))\nEOF"), "allow"),
    ("B5 bash ignore entry naming gate file ok", lambda: bash("printf '.dev-skills-gates.md\\n' >> .gitignore"), "allow"),
    ("B5 probe naming gate file ok", lambda: bash("p() { o=$(\"$@\" 2>&1); echo \"$1=$o\"; }\np local_tracked bash -c 'git ls-files -- .dev-skills-gates.md | tr \"\\n\" \" \"'"), "allow"),
    ("B5 bash waiver into gate file asks", lambda: bash("sed -i 's/^🔒 SECURITY .*/🔒 SECURITY   ✅ 0 open (waived M1)/' .dev-skills-gates.md"), "ask"),
    ("B5 bash heredoc waiver asks", lambda: bash("python3 - <<'EOF'\np='.dev-skills-gates.md'; s=open(p).read()\nopen(p,'w').write(s+'🔕 waived by user: M1')\nEOF"), "ask"),
    ("B5 bash cp onto gate file asks", lambda: bash("cp /tmp/g.md .dev-skills-gates.md"), "ask"),
    ("B5 bash cat file into gate file asks", lambda: bash("cat /tmp/g.md > .dev-skills-gates.md"), "ask"),
    ("B5 bash decoded text into gate file asks", lambda: bash("echo d2FpdmVk | base64 -d >> .dev-skills-gates.md"), "ask"),
    ("B5 bash octal escapes into gate file ask", lambda: bash("printf '\\167aived M1' >> .dev-skills-gates.md"), "ask"),
    ("B5 bash emptying gate file asks", lambda: bash(": > .dev-skills-gates.md"), "ask"),
    ("B5 bash find -delete gate file asks", lambda: bash("find . -name .dev-skills-gates.md -delete"), "ask"),
    ("B5 bash git checkout of gate file asks", lambda: bash("git checkout HEAD~3 -- .dev-skills-gates.md"), "ask"),
    ("B5 bash git show into gate file asks", lambda: bash("git show HEAD~1:.dev-skills-gates.md > .dev-skills-gates.md"), "ask"),
    ("B5 bash heredoc rows ok", lambda: bash("cat >> .dev-skills-gates.md <<'EOF'\n  build ok\nEOF"), "allow"),
    ("B5 bash backup copy of gate file ok", lambda: bash("cp .dev-skills-gates.md /tmp/backup.md"), "allow"),
    ("B5 bash cat read piped ok", lambda: bash("cat .dev-skills-gates.md | head -5"), "allow"),
    ("B5 bash commit message naming gate file ok", lambda: bash("git add x && git commit -m 'waived M1 in .dev-skills-gates.md'", gates=GATES_WORK), "allow"),
    ("B5 bash enforcement decline asks", lambda: bash("printf 'Hook enforcement: declined\\n' >> .dev-skills-gates.md"), "ask"),
    ("B5 bash host network approval asks", lambda: bash("echo 'Host network: 8080 approved' >> .dev-skills-gates.md"), "ask"),
    ("B5 bash write into checks via ~", lambda: run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": repo(GATES_ALL),
                                                                  "tool_input": {"command": "cp x ~/.claude/skills/dsk/checks/enforce.py"}},
                                                     env={"CLAUDE_PLUGIN_ROOT": os.path.expanduser("~/.claude/skills/dsk")}), "ask"),
    ("B5 bash write into checks via $HOME", lambda: run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": repo(GATES_ALL),
                                                                      "tool_input": {"command": "cp x $HOME/.claude/skills/dsk/checks/enforce.py"}},
                                                         env={"CLAUDE_PLUGIN_ROOT": os.path.expanduser("~/.claude/skills/dsk")}), "ask"),
    ("B5 bash read gate file ok", lambda: bash("cat .dev-skills-gates.md"), "allow"),
    ("B5 semi-auto gate to ✅ ok", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                                     "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 0 open"},
                                            gates=GATES_SEMI), "allow"),
    ("B5 semi-auto waiver still asks", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                                             "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 1 waived"},
                                                    gates=GATES_SEMI), "ask"),
    ("B5 semi-auto mode change ok", lambda: edit("Edit", {"file_path": ".dev-skills-gates.md",
                                                                  "old_string": "Mode: semi-autonomous", "new_string": "Mode: manual"},
                                                         gates=GATES_SEMI), "allow"),
    ("B5 leaving semi-auto + gate in one edit ok", lambda: edit("Write", {"file_path": ".dev-skills-gates.md",
                                                                           "content": GATES_NONE.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ✅")},
                                                                  gates=GATES_SEMI), "allow"),
    ("B5 switching to semi-auto + gate in one edit ok", lambda: edit("Write", {"file_path": ".dev-skills-gates.md",
                                                                                 "content": GATES_SEMI.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ✅")},
                                                                        gates=GATES_NONE), "allow"),
    # --- B6: the gate file stays out of local commits
    ("B6 git add gate file", lambda: bash("git add .dev-skills-gates.md"), "deny"),
    ("B6 git add -f gate file", lambda: bash("git add -f .dev-skills-gates.md"), "deny"),
    ("B6 git add ./gate file", lambda: bash("git add ./.dev-skills-gates.md"), "deny"),
    ("B6 git add legacy .claude gate file", lambda: bash("git add -f .claude/dev-skills-gates.md"), "deny"),
    ("B6 git -C add gate file", lambda: bash("git -C . add -f .dev-skills-gates.md && git commit -m x"), "deny"),
    ("B6 git add -f .claude", lambda: bash("git add -f .claude/"), "deny"),
    ("B6 git add -Af", lambda: bash("git add -Af"), "deny"),
    ("B6 git add -f . ", lambda: bash("git add --force ."), "deny"),
    ("B6 PowerShell git add gate file", lambda: pwsh("git add .dev-skills-gates.md"), "deny"),
    ("B6 git add -A ok", lambda: bash("git add -A"), "allow"),
    ("B6 git rm --cached ok", lambda: bash("git rm --cached .dev-skills-gates.md"), "allow"),
    ("B5 git rm --cached then rm still asks", lambda: bash("git rm --cached .dev-skills-gates.md; rm .dev-skills-gates.md"), "ask"),
    ("B5 git rm (not cached) gate file asks", lambda: bash("git rm .dev-skills-gates.md"), "ask"),
    ("B6 remote container may stage it", lambda: run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": repo(GATES_ALL),
                                                                 "tool_input": {"command": "git add -f .dev-skills-gates.md"}},
                                                    env={"CLAUDE_CODE_REMOTE": "true"}), "allow"),
    ("B5 Windows settings path", lambda: edit("Write", {"file_path": "C:\\Users\\me\\.claude\\settings.json", "content": "{}"}), "ask"),
    ("B5 bash write to Windows settings path", lambda: bash("copy x C:\\Users\\me\\.claude\\settings.local.json > out"), "ask"),
    # --- B8: workflow edits
    ("B8 hardened workflow ok", lambda: wf("Write", GOOD_WF), "allow"),
    ("B8 version-tag pin", lambda: wf("Write", GOOD_WF.replace("@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1", "@v7")), "deny"),
    ("B8 branch pin", lambda: wf("Write", GOOD_WF.replace("      - name: Test\n",
        "      - uses: home-assistant/actions/hassfest@master\n      - name: Test\n")), "deny"),
    ("B8 hacs/action@main is the documented exception", lambda: wf("Write", GOOD_WF.replace("      - name: Test\n",
        "      - uses: hacs/action@main\n        with:\n          category: integration\n      - name: Test\n")), "allow"),
    ("B8 local action ok", lambda: wf("Write", GOOD_WF.replace("      - name: Test\n",
        "      - uses: ./.github/actions/setup\n      - name: Test\n")), "allow"),
    ("B8 expression in run block", lambda: wf("Write", GOOD_WF.replace('echo "$REF"', 'echo "${{ github.head_ref }}"')), "deny"),
    ("B8 expression in one-line run", lambda: wf("Write", GOOD_WF.replace('        run: |\n          set -euo pipefail\n          echo "$REF"\n',
        '        run: echo "${{ inputs.tag }}"\n')), "deny"),
    ("B8 expression in env ok", lambda: wf("Write", GOOD_WF), "allow"),
    ("B8 expression in a YAML comment ok", lambda: wf("Write", GOOD_WF.replace("      - name: Test\n",
        "      # never put ${{ }} inside run:\n      - name: Test\n")), "allow"),
    ("B8 checkout without persist-credentials", lambda: wf("Write", GOOD_WF.replace(
        "        with:\n          persist-credentials: false\n", "")), "deny"),
    ("B8 checkout with persist-credentials: true ok (job pushes)", lambda: wf("Write", GOOD_WF.replace(
        "persist-credentials: false", "persist-credentials: true")), "allow"),
    ("B8 checkout under - name: still read", lambda: wf("Write", GOOD_WF.replace(
        "      - uses: actions/checkout@", "      - name: Checkout\n        uses: actions/checkout@")), "allow"),
    ("B8 no permissions block asks", lambda: wf("Write", GOOD_WF.replace("permissions:\n  contents: read\n", "")), "ask"),
    ("B8 job without timeout asks", lambda: wf("Write", GOOD_WF.replace("    timeout-minutes: 10\n", "")), "ask"),
    ("B8 reusable-workflow job needs no timeout", lambda: wf("Write", GOOD_WF +
        "  shared:\n    uses: ./.github/workflows/shared.yml\n"), "allow"),
    ("B8 second job without timeout asks", lambda: wf("Write", GOOD_WF +
        "  lint:\n    runs-on: ubuntu-latest\n    steps:\n      - run: true\n"), "ask"),
    ("B8 gradlew after wrapper-validation ok", lambda: wf("Write", GRADLE_WF), "allow"),
    ("B8 gradlew after setup-gradle ok", lambda: wf("Write", GRADLE_WF.replace(
        "gradle/actions/wrapper-validation@", "gradle/actions/setup-gradle@")), "allow"),
    ("B8 gradlew with setup-java cache only asks", lambda: wf("Write", GRADLE_WF.replace(
        "      - uses: gradle/actions/wrapper-validation@9c971963bec38e04b3d30dcc455b5382be2fdbfb # v6.3.0\n", "")), "ask"),
    ("B8 setup-gradle with validate-wrappers: false asks", lambda: wf("Write", GRADLE_WF.replace(
        "      - uses: gradle/actions/wrapper-validation@9c971963bec38e04b3d30dcc455b5382be2fdbfb # v6.3.0\n",
        "      - uses: gradle/actions/setup-gradle@9c971963bec38e04b3d30dcc455b5382be2fdbfb # v6.3.0\n"
        "        with:\n          validate-wrappers: false\n")), "ask"),
    ("B8 gradlew in a block before validation asks", lambda: wf("Write", GOOD_WF.replace("          echo \"$REF\"\n",
        "          echo \"$REF\"\n          ./gradlew test\n")), "ask"),
    ("B8 validated in one job only asks for the other", lambda: wf("Write", GRADLE_WF +
        "  lint:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: ./gradlew lint\n"), "ask"),
    ("B8 gradlew under a subfolder asks", lambda: wf("Write", GOOD_WF.replace("          echo \"$REF\"\n",
        "          echo \"$REF\"\n          cd app && android/gradlew assembleDebug; echo done\n")), "ask"),
    ("B8 gradlew named, not run, ok", lambda: wf("Write", GOOD_WF.replace("      - name: Test\n",
        "      - name: Skip gradlew here\n        run: echo no\n      - name: Test\n")), "allow"),
    ("B8 commented-out gradlew ok", lambda: wf("Write", GOOD_WF.replace("      - name: Test\n",
        "      # - run: ./gradlew lint\n      - name: Test\n")), "allow"),
    ("B8 .yaml extension checked too", lambda: wf("Write", BAD_WF, name="ci.yaml"), "deny"),
    ("B8 non-workflow YAML ignored", lambda: edit("Write", {"file_path": "docker-compose.yml", "content": BAD_WF}), "allow"),
    ("B8 editing a legacy workflow without adding problems ok", lambda: wf("Edit",
        BAD_WF.replace("name: Legacy", "name: Legacy build"), existing=BAD_WF), "allow"),
    ("B8 fixing a legacy workflow ok", lambda: wf("Edit", BAD_WF.replace("@v4", "@3d3c42e5aac5ba805825da76410c181273ba90b1"), existing=BAD_WF), "allow"),
    ("B8 legacy workflow, new unpinned action", lambda: wf("Edit",
        BAD_WF + "      - uses: softprops/action-gh-release@v2\n", existing=BAD_WF), "deny"),
    ("B8 declined stands down", lambda: wf("Write", BAD_WF, gates=GATES_DECLINED), "allow"),
    # --- PowerShell tool (Windows)
    ("A4 PowerShell commit, gates pending", lambda: run("pre-tool", {"session_id": "t", "tool_name": "PowerShell", "cwd": repo(GATES_NONE),
                                                                     "tool_input": {"command": "git add -A; git commit -m x"}}), "deny"),
    ("A4 PowerShell commit, work gates pass", lambda: run("pre-tool", {"session_id": "t", "tool_name": "PowerShell", "cwd": repo(GATES_WORK),
                                                                       "tool_input": {"command": "git commit -m x"}}), "allow"),
    ("A4 PowerShell Set-Location into pending repo", lambda:
        run("pre-tool", {"session_id": "t", "tool_name": "PowerShell", "cwd": repo(GATES_WORK),
                         "tool_input": {"command": "Set-Location " + repo(GATES_NONE) + "; git commit -m x"}}), "deny"),
    ("A4 PowerShell call operator", lambda: pwsh("& git commit -m x"), "deny"),
    ("A4 PowerShell git.exe", lambda: pwsh("git.exe commit -m x"), "deny"),
    ("A4 PowerShell full path to git.exe", lambda: pwsh("& 'C:\\Program Files\\Git\\cmd\\git.exe' push"), "deny"),
    ("A4 bash git.exe", lambda: bash("git.exe push", gates=GATES_NONE), "deny"),
    ("A4 PowerShell iex", lambda: pwsh('iex "git commit -m x"'), "deny"),
    ("A4 PowerShell Invoke-Expression", lambda: pwsh("Invoke-Expression 'git commit -m x'"), "deny"),
    ("A4 PowerShell pwsh -c", lambda: pwsh('pwsh -NoProfile -c "git commit -m x"'), "deny"),
    ("A4 PowerShell powershell -Command", lambda: pwsh('powershell.exe -Command "git commit -m x"'), "deny"),
    ("A4 PowerShell -EncodedCommand", lambda: pwsh("pwsh -EncodedCommand " + ENC), "deny"),
    ("A4 PowerShell cmd /c", lambda: pwsh("cmd /c git commit -m x"), "deny"),
    ("A4 bash cmd.exe /c", lambda: bash("cmd.exe /c git push", gates=GATES_NONE), "deny"),
    ("A4 PowerShell subexpression", lambda: pwsh("Write-Output $(git commit -m x)"), "deny"),
    ("A4 PowerShell backtick is not a subshell", lambda: pwsh("Write-Output `git commit`", gates=GATES_WORK), "allow"),
    ("A4 PowerShell read-only git ok", lambda: pwsh("git status; Get-ChildItem"), "allow"),
    ("A4 Start-Process positional", lambda: pwsh("Start-Process git -ArgumentList 'push'"), "deny"),
    ("A4 Start-Process named", lambda: pwsh('Start-Process -Wait -FilePath git.exe -ArgumentList "commit -m x"'), "deny"),
    ("A4 Start-Process array args", lambda: pwsh("saps git push,origin -NoNewWindow"), "deny"),
    ("A4 Start-Process WorkingDirectory into pending repo", lambda:
        pwsh("Start-Process git -ArgumentList 'commit -m x' -WorkingDirectory " + repo(GATES_NONE), gates=GATES_WORK), "deny"),
    ("A4 Start-Process WorkingDirectory doesn't leak", lambda:
        pwsh("Start-Process notepad -WorkingDirectory " + repo(GATES_WORK) + "; git commit -m x"), "deny"),
    ("A4 Start-Process other program ok", lambda: pwsh("Start-Process notepad.exe"), "allow"),
    ("A4 here-string to bash", lambda: bash('bash <<< "git push"', gates=GATES_NONE), "deny"),
    ("A4 heredoc to bash still checked", lambda: bash("bash <<'EOF'\ngit push\nEOF", gates=GATES_NONE), "deny"),
    ("A4 heredoc piped to sh still checked", lambda: bash("cat <<EOF | sh\ngit push\nEOF", gates=GATES_NONE), "deny"),
    ("A4 quoted heredoc to python is data", lambda: bash("python3 - <<'EOF'\n# $(git push) and git push\nEOF", gates=GATES_NONE), "allow"),
    ("A4 unquoted data heredoc still expands $( )", lambda: bash("cat <<EOF > x\n$(git push)\nEOF", gates=GATES_NONE), "deny"),
    ("A4 command after heredoc checked", lambda: bash("cat <<'EOF' > x\nhi\nEOF\ngit push", gates=GATES_NONE), "deny"),
    ("A4 quoted << is not a heredoc", lambda: bash('python3 -c "x=1<<y"\ngit push\ny', gates=GATES_NONE), "deny"),
    ("A4 <<- heredoc with tab delimiter", lambda: bash("cat <<-EOF > x\n\tgit push\n\tEOF\ngit push", gates=GATES_NONE), "deny"),
    ("B5 PowerShell Set-Content gate file ok", lambda: pwsh('Set-Content .dev-skills-gates.md "x"'), "allow"),
    ("B5 PowerShell Out-File gate file ok", lambda: pwsh("'x' | Out-File .dev-skills-gates.md"), "allow"),
    ("B5 PowerShell waiver into gate file asks", lambda: pwsh("Add-Content .dev-skills-gates.md 'waived M1'"), "ask"),
    ("B5 PowerShell Remove-Item gate file asks", lambda: pwsh("Remove-Item .dev-skills-gates.md"), "ask"),
    ("B5 PowerShell Copy-Item settings", lambda: pwsh("Copy-Item x C:\\Users\\me\\.claude\\settings.json"), "ask"),
    ("B5 PowerShell .NET write gate file ok", lambda: pwsh("[IO.File]::WriteAllText('.dev-skills-gates.md', 'x')"), "allow"),
    ("B5 PowerShell read gate file ok", lambda: pwsh("Get-Content .dev-skills-gates.md"), "allow"),
    ("B5 other file ok", lambda: edit("Write", {"file_path": "README.md", "content": "hi"}), "allow"),
    # --- C: replies
    ("C ok reply", lambda: stop(RUN_OK, gates=GATES_WORK), "allow"),
    ("C prose code box mentioning git ok", lambda: stop("Message:\n```\nfeat: strict gates on git writes (wrappers)\n```\n"), "allow"),
    ("C prose only ok", lambda: stop("All done. The rule forbids 127.0.0.1 bindings."), "allow"),
    ("C1 loopback URL", lambda: stop("Open http://127.0.0.1:8080 to test."), "block"),
    ("C1 localhost URL", lambda: stop("URL: http://localhost:3000"), "block"),
    ("C1 bridge URL", lambda: stop("URL: http://172.17.0.1:8080/"), "block"),
    ("C1 LAN URL ok", lambda: stop(f"URL: http://{LAN}:8080"), "allow"),
    ("C1 for-reading ok", lambda: stop("📄 FOR READING — don't run\n```\ncurl http://127.0.0.1:8080\n```\n"), "allow"),
    ("C2 gates pending", lambda: stop(RUN_OK, gates=GATES_NONE), "block"),
    ("C2 mode unchosen", lambda: stop(RUN_OK, gates=GATES_UNCHOSEN), "block"),
    ("C2 tag before RELEASE", lambda: stop(RUN_OK.replace('git add -A && git commit -m "feat: x" && git push -u origin feat/x',
                                                          "git tag v1.2.0 && git push origin v1.2.0"),
                                           gates=GATES_ALL.replace("📦 RELEASE    ✅ PR #5", "📦 RELEASE    ⬜")), "block"),
    ("C2 tag after RELEASE ok", lambda: stop(RUN_OK.replace('git add -A && git commit -m "feat: x" && git push -u origin feat/x',
                                                            "git tag v1.2.0 && git push origin v1.2.0")), "allow"),
    ("C3 unlabeled git block", lambda: stop("`🔢✅ 🔒✅`\n```bash\ngit push -u origin feat/x\n```\nNo need to reply."), "block"),
    ("C3 missing START", lambda: stop(RUN_OK.replace("# ════════ ▶️ START: commit + push ════════\n", ""), gates=GATES_WORK), "block"),
    ("C3 two blocks unnumbered", lambda: stop(RUN_OK + "\n" + RUN_OK.split("\n", 2)[2], gates=GATES_WORK), "block"),
    ("C3 quoted git block", lambda: stop("`🔢✅ 🔒✅`\n> ```bash\n> git push -u origin feat/x\n> ```\nNo need to reply.",
                                         gates=GATES_WORK), "block"),
    ("C3 quoted for-reading ok", lambda: stop("> 📄 FOR READING — don't run\n> ```bash\n> git push origin feat/x\n> ```\n"), "allow"),
    ("C4 cd in block", lambda: stop(RUN_OK.replace("git add -A", "cd ~/repo && git add -A"), gates=GATES_WORK), "block"),
    ("C5 no tracker", lambda: stop(RUN_OK.split("\n", 2)[2], gates=GATES_WORK), "block"),
    ("C7 no 'no need to reply'", lambda: stop(RUN_OK.replace("No need to reply.", ""), gates=GATES_WORK), "block"),
    ("C7 question after the block ok", lambda: stop(RUN_OK.replace("No need to reply.", "Fix or waive #17?"),
                                                     gates=GATES_WORK), "allow"),
    ("C7 'tell me' after the block ok", lambda: stop(RUN_OK.replace("No need to reply.", "Tell me **fix or waive**."),
                                                      gates=GATES_WORK), "allow"),
    ("C7 other wording ok", lambda: stop(RUN_OK.replace("No need to reply.", "You don't need to reply."),
                                          gates=GATES_WORK), "allow"),
    ("C3 PowerShell block, push inside if ($?)", lambda: stop("`🔢✅ 🔒✅`\n```powershell\ngit add -A; if ($?) { git push -u origin feat/x }\n```\nNo need to reply."), "block"),
    ("C4 Set-Location in a PowerShell block", lambda: stop(RUN_OK.replace("```bash", "```powershell").replace(
        'git add -A && git commit -m "feat: x" && git push -u origin feat/x', "Set-Location C:\\src\\x; git status"),
        gates=GATES_WORK), "block"),
    ("handoff git add asks", lambda: bash("git add -f .dev-skills-handoff.md"), "ask"),
    ("lessons append to another repo ok", lambda: bash("R=/home/me/claude-vibe-skills; { git -C \"$R\" show refs/dev-skills/lessons:LESSONS.md "
        "2>/dev/null; cat <<'EOF'\n## 2026-09-26 · from x\n- $(git push origin master)\nEOF\n} | git -C \"$R\" hash-object -w --stdin "
        "| xargs printf '100644 blob %s\\tLESSONS.md\\n' | git -C \"$R\" mktree | xargs git -C \"$R\" commit-tree -m l "
        "| xargs git -C \"$R\" update-ref refs/dev-skills/lessons"), "allow"),
    ("lessons ref push asks", lambda: bash("git push origin refs/dev-skills/lessons"), "ask"),
    ("handoff ref push asks", lambda: bash("git push origin refs/dev-skills/handoff"), "ask"),
    ("handoff ref save ok", lambda: bash("git update-ref refs/dev-skills/handoff \"$(printf '100644 blob %s\\tHANDOFF.md\\n' "
        "\"$(git hash-object -w .dev-skills-handoff.md)\" | git mktree | xargs git -c user.name=dev-skills "
        "-c user.email=dev-skills@localhost commit-tree -m 'dev-skills handoff')\""), "allow"),
    ("handoff legacy path asks", lambda: bash("git add .claude/handoffs/h.md"), "ask"),
    ("handoff in a remote container ok", lambda: run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": repo(GATES_ALL),
        "tool_input": {"command": "git add -f .dev-skills-handoff.md"}}, env={"CLAUDE_CODE_REMOTE": "true"}), "allow"),
    ("C3 '!' block ok", lambda: stop(RUN_OK.replace("# ════════ ▶️ START", "! # ════════ ▶️ START"), gates=GATES_WORK), "allow"),
    ("C2 '!' block still gated", lambda: stop(RUN_OK.replace("# ════════ ▶️ START", "! # ════════ ▶️ START"), gates=GATES_NONE), "block"),
    ("C3 unlabeled '! git push' block", lambda: stop("```bash\n! git push -u origin feat/x\n```\n", gates=GATES_WORK), "block"),
    ("C3 read-only block ok", lambda: stop("```bash\ngit status -sb && git log --oneline -3\n```\n"), "allow"),
    ("C3 labeled read block still checked", lambda: stop("### ▶️ RUN THIS — check\n```bash\ngit status\n```\n"), "block"),
    ("C declined ok", lambda: stop("http://127.0.0.1:1", gates=GATES_DECLINED), "allow"),
    # --- header fallback (checks file missing): only Bash git/gh/docker and GitHub MCP tools stop
    ("fallback bash git blocked", lambda: header_fallback({"tool_name": "Bash", "tool_input": {"command": "git status"}}), "block"),
    ("fallback bash docker blocked", lambda: header_fallback({"tool_name": "Bash", "tool_input": {"command": "cd /x && docker ps"}}), "block"),
    ("fallback PowerShell git blocked", lambda: header_fallback({"tool_name": "PowerShell", "tool_input": {"command": "git push"}}), "block"),
    ("fallback bash ls ok", lambda: header_fallback({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}), "allow"),
    ("fallback github mcp blocked", lambda: header_fallback({"tool_name": "mcp__github__create_pull_request", "tool_input": {}}), "block"),
    ("fallback other mcp ok", lambda: header_fallback({"tool_name": "mcp__other__x", "tool_input": {"q": "git status"}}), "allow"),
    ("fallback edit mentioning git ok", lambda: header_fallback({"tool_name": "Edit", "tool_input": {"file_path": "a.md", "new_string": "run git status, gh pr list, docker ps"}}), "allow"),
    ("fallback write mentioning git ok", lambda: header_fallback({"tool_name": "Write", "tool_input": {"file_path": "a.md", "content": "git commit\ndocker run"}}), "allow"),
    ("fallback edit quoting a Bash payload ok", lambda: header_fallback({"tool_name": "Edit", "tool_input": {"new_string": '{"tool_name": "Bash", "tool_input": {"command": "git push"}}'}}), "allow"),
    # --- D1
    ("D1 unanswered", lambda: run("post-ask", {"tool_input": {"questions": [
        {"question": "Mode?", "options": [{"label": "Manual"}, {"label": "Semi"}]},
        {"question": "Version?", "options": [{"label": "1.0"}, {"label": "2.0"}]}]},
        "tool_response": {"answers": {"Mode?": "Manual"}}}), "context"),
    ("D1 free text", lambda: run("post-ask", {"tool_input": {"questions": [
        {"question": "Mode?", "options": [{"label": "Manual"}, {"label": "Semi"}]}]},
        "tool_response": {"answers": {"Mode?": "what's the difference?"}}}), "context"),
    ("D1 label with a comma ok", lambda: run("post-ask", {"tool_input": {"questions": [
        {"question": "Seen?", "options": [{"label": "Yes, I approved them"}, {"label": "No"}]}]},
        "tool_response": {"answers": {"Seen?": "Yes, I approved them"}}}), "allow"),
    ("D1 multi-select ok", lambda: run("post-ask", {"tool_input": {"questions": [
        {"question": "Which?", "multiSelect": True, "options": [{"label": "A"}, {"label": "B"}]}]},
        "tool_response": {"answers": {"Which?": "A, B"}}}), "allow"),
    ("D1 all answered ok", lambda: run("post-ask", {"tool_input": {"questions": [
        {"question": "Mode?", "options": [{"label": "Manual"}, {"label": "Semi"}]}]},
        "tool_response": {"answers": {"Mode?": "Manual"}}}), "allow"),
    ("D1 string response", lambda: run("post-ask", {"tool_input": {"questions": [
        {"question": "Version?", "options": [{"label": "1.0"}]}]},
        "tool_response": 'The user answered: "Version?" (No answer provided)'}), "context"),
]


def b8_severity_fails() -> list[str]:
    """Each B8 rule carries its WORKFLOW_REFERENCE.md severity."""
    sys.path.insert(0, os.path.dirname(ENFORCE))
    from enforce import workflow_findings
    want = {
        "legacy workflow": (BAD_WF, ["Critical", "High", "High", "High", "Low"]),
        "third-party tag": (GOOD_WF + "      - uses: softprops/action-gh-release@v2\n", ["Critical"]),
        "third-party branch": (GOOD_WF + "      - uses: home-assistant/actions/hassfest@master\n", ["Critical"]),
        "first-party branch": (GOOD_WF + "      - uses: github/codeql-action/init@main\n", ["High"]),
        "unvalidated gradlew": (GOOD_WF + "      - run: ./gradlew test\n", ["Medium"]),
        "hardened": (GOOD_WF, []),
    }
    fails = []
    for name, (text, expect) in want.items():
        got = sorted(s for s, _, _ in workflow_findings(text))
        if got != sorted(expect):
            fails.append(f"severity {name}: want {sorted(expect)}, got {got}")
    return fails


def reference_scale_fails() -> list[str]:
    """WORKFLOW_REFERENCE.md rates each B8 rule at the severity B8 reports."""
    ref = open(os.path.join(os.path.dirname(SKILL_MD), "WORKFLOW_REFERENCE.md"), encoding="utf-8").read()
    ref = " ".join(ref.split())
    marks = {"Critical": "🚨 **Critical**", "High": "⚠️ **High**", "Medium": "📝 **Medium**", "Low": "💡 **Low**"}
    ends = list(marks.values())[1:] + ["4. **Check for missing workflows"]
    phrases = {
        "Critical": ["unpinned third-party actions", "interpolated directly into a `run:` script"],
        "High": ["`persist-credentials: true` (or missing", "no `permissions:` block", "no timeouts",
                 "on a branch ref such as `@main`"],
        "Medium": ["a Gradle build with no wrapper validation"],
        "Low": ["actions pinned to version tags instead of SHAs (first-party"],
    }
    fails = []
    for (sev, mark), end in zip(marks.items(), ends):
        start, stop = ref.find(mark), ref.find(end)
        bullet = ref[start:stop] if 0 <= start < stop else ""
        fails += [f"WORKFLOW_REFERENCE.md {sev} bullet lacks B8's rule: {p}" for p in phrases[sev] if p not in bullet]
    return fails


def audit_order_fails() -> list[str]:
    """The weekly issue lists the worst repo first, and its worst finding first."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit_repos", os.path.join(HERE, "audit-repos.py"))
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    findings = [("o/b", "ci.yml", "Low", "low one"), ("o/a", "ci.yml", "High", "high one"),
                ("o/b", "release.yml", "Critical", "crit one"), ("o/b", "ci.yml", "High", "high two")]
    got = [x for x in audit.checklist(findings) if x]
    expect = ["### o/b (1 Critical, 1 High, 1 Low)", "- [ ] **Critical** · release.yml: crit one",
              "- [ ] **High** · ci.yml: high two", "- [ ] **Low** · ci.yml: low one",
              "### o/a (1 High)", "- [ ] **High** · ci.yml: high one"]
    return [] if got == expect else [f"audit checklist order: want {expect}, got {got}"]


def main() -> None:
    sev_fails = b8_severity_fails() + reference_scale_fails() + audit_order_fails()
    for msg in sev_fails:
        print(f"FAIL {msg}")
    fails = 1 if sev_fails else 0
    for name, fn, want in CASES:
        if LAN is None and "LAN" in name:
            print(f"skip {name}: no network route on this machine")
            continue
        got = fn()
        ok = got == want
        fails += not ok
        if not ok or "-v" in sys.argv:
            print(f"{'ok  ' if ok else 'FAIL'} {name}: want {want}, got {got}")
    # Stop loop guard: the third block for the same prompt goes through with a warning.
    d = repo(GATES_ALL)
    p = {"session_id": "t-loop", "prompt_id": "loop" + d[-6:], "cwd": d,
         "last_assistant_message": "http://127.0.0.1:1", "stop_hook_active": False}
    seq = [run("stop", p), run("stop", dict(p, stop_hook_active=True)), run("stop", dict(p, stop_hook_active=True))]
    if seq != ["block", "block", "warn"]:
        fails += 1
        print(f"FAIL stop loop guard: want block, block, warn, got {seq}")
    # Without prompt_id (Claude Code before 2.1.196) the limit is still per reply: a new
    # reply's first stop (stop_hook_active false) starts the count over.
    d = repo(GATES_ALL)
    p = {"session_id": "t-noid" + d[-6:], "cwd": d, "last_assistant_message": "http://127.0.0.1:1",
         "stop_hook_active": False}
    seq = [run("stop", p), run("stop", dict(p, stop_hook_active=True)), run("stop", dict(p, stop_hook_active=True)),
           run("stop", p)]
    if seq != ["block", "block", "warn", "block"]:
        fails += 1
        print(f"FAIL stop loop guard without prompt_id: want block, block, warn, block, got {seq}")
    total = len(CASES) + 3
    print(f"enforcement checks: {total - fails}/{total} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
