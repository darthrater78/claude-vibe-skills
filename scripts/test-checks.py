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
GATES_SEMI = GATES_NONE.replace("Mode: manual", "Mode: semi-autonomous (approved 2026-09-24)")
GATES_UNCHOSEN = GATES_ALL.replace("Mode: manual", "Mode: unchosen")
GATES_DECLINED = GATES_NONE.replace("Mode: manual", "Mode: manual\nHook enforcement: declined (2026-09-24)")
GATES_FORK = GATES_ALL.replace("owner/repo (not a fork)", "me/repo (fork of up/repo)")
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
        with open(os.path.join(d, ".claude", "dev-skills-gates.md"), "w", encoding="utf-8") as fh:
            fh.write(gates)
    if compose:
        with open(os.path.join(d, "compose.yaml"), "w", encoding="utf-8") as fh:
            fh.write(compose)
    return d


def run(mode: str, payload: dict, env: dict | None = None) -> str:
    e = dict(os.environ)
    e.pop("CLAUDE_PLUGIN_ROOT", None)
    e["TMPDIR"] = TMP  # keep the checks' marker and counters out of the real temp folder
    e.update(env or {})
    p = subprocess.run([sys.executable, ENFORCE, mode], input=json.dumps(payload), capture_output=True,
                       text=True, env=e, timeout=20)
    if p.returncode != 0:
        return "error:" + p.stderr
    out = p.stdout.strip()
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


def bash_docker(cmd: str, build_row: str) -> str:
    d = repo(GATES_ALL.replace("🔨 BUILD      ➖ N/A — no build system", build_row))
    with open(os.path.join(d, "Dockerfile"), "w", encoding="utf-8") as fh:
        fh.write("FROM alpine:3.20\n")
    return run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": d, "tool_input": {"command": cmd}})


def edit(tool: str, inp: dict, gates: str | None = GATES_ALL) -> str:
    d = repo(gates)
    inp = dict(inp)
    inp["file_path"] = os.path.join(d, inp["file_path"])
    return run("pre-tool", {"session_id": "t", "tool_name": tool, "cwd": d, "tool_input": inp})


def stop(msg: str, gates: str | None = GATES_ALL, prompt: str = "p1") -> str:
    d = repo(gates)
    return run("stop", {"session_id": "t-stop", "prompt_id": prompt + d[-6:], "cwd": d,
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
    ("A4 pr create needs docs", lambda: bash("gh pr create --title x", gates=GATES_WORK), "deny"),
    ("A4 docker repo: no handoff/artifact/creds", lambda: bash("gh pr merge 5 --merge",
                                                             gates=GATES_ALL.replace("🔨 BUILD      ➖ N/A — no build system", "🔨 BUILD      ✅ built"),
                                                             compose="services:\n  app:\n    image: a:1\n"), "allow"),
    ("A4 Dockerfile repo: BUILD ✅ without handoff", lambda: bash_docker("gh pr merge 5 --merge", "🔨 BUILD      ✅ built"), "deny"),
    ("A4 Dockerfile repo: no test creds", lambda: bash_docker("gh pr merge 5 --merge",
                                                              "🔨 BUILD      ✅ handoff offered · test artifact: img:pr-5 @ abc"), "deny"),
    ("A4 Dockerfile repo: all notes ok", lambda: bash_docker("gh pr merge 5 --merge",
                                                             "🔨 BUILD      ✅ handoff offered · test artifact: img:pr-5 @ abc · test creds: per run"), "allow"),
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
    # --- declined
    ("declined: commit allowed", lambda: bash("git commit -m x", gates=GATES_DECLINED), "allow"),
    ("declined: docker allowed", lambda: bash("docker run -p 127.0.0.1:80:80 img", gates=GATES_DECLINED), "allow"),
    # --- B5: gate file and settings edits
    ("B5 gate to ✅", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                            "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 0 open"},
                                   gates=GATES_NONE), "ask"),
    ("B5 mode set", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                          "old_string": "Mode: unchosen", "new_string": "Mode: manual"},
                                 gates=GATES_UNCHOSEN), "ask"),
    ("B5 decline", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                         "old_string": "Mode: manual", "new_string": "Mode: manual\nHook enforcement: declined"}), "ask"),
    ("B5 host net approval", lambda: edit("Write", {"file_path": ".claude/dev-skills-gates.md",
                                                    "content": GATES_ALL + "Host network: x approved today\n"}), "ask"),
    ("B5 gate to ⏳ ok", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                               "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ⏳ scanning"},
                                      gates=GATES_NONE), "allow"),
    ("B5 declined can't skip B5", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                                        "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 0 open"},
                                               gates=GATES_DECLINED), "ask"),
    ("B5 settings file", lambda: edit("Write", {"file_path": ".claude/settings.json", "content": "{}"}), "ask"),
    ("B5 bash write to gate file", lambda: bash("echo 'x' >> .claude/dev-skills-gates.md"), "ask"),
    ("B5 bash write into checks via ~", lambda: run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": repo(GATES_ALL),
                                                                  "tool_input": {"command": "cp x ~/.claude/skills/dsk/checks/enforce.py"}},
                                                     env={"CLAUDE_PLUGIN_ROOT": os.path.expanduser("~/.claude/skills/dsk")}), "ask"),
    ("B5 bash write into checks via $HOME", lambda: run("pre-tool", {"session_id": "t", "tool_name": "Bash", "cwd": repo(GATES_ALL),
                                                                      "tool_input": {"command": "cp x $HOME/.claude/skills/dsk/checks/enforce.py"}},
                                                         env={"CLAUDE_PLUGIN_ROOT": os.path.expanduser("~/.claude/skills/dsk")}), "ask"),
    ("B5 bash read gate file ok", lambda: bash("cat .claude/dev-skills-gates.md"), "allow"),
    ("B5 semi-auto gate to ✅ ok", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                                     "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 0 open"},
                                            gates=GATES_SEMI), "allow"),
    ("B5 semi-auto waiver still asks", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                                             "old_string": "🔒 SECURITY   ⬜", "new_string": "🔒 SECURITY   ✅ 1 waived"},
                                                    gates=GATES_SEMI), "ask"),
    ("B5 semi-auto mode change still asks", lambda: edit("Edit", {"file_path": ".claude/dev-skills-gates.md",
                                                                  "old_string": "Mode: semi-autonomous", "new_string": "Mode: manual"},
                                                         gates=GATES_SEMI), "ask"),
    ("B5 leaving semi-auto + gate in one edit asks", lambda: edit("Write", {"file_path": ".claude/dev-skills-gates.md",
                                                                           "content": GATES_NONE.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ✅")},
                                                                  gates=GATES_SEMI), "ask"),
    ("B5 switching to semi-auto + gate in one edit asks", lambda: edit("Write", {"file_path": ".claude/dev-skills-gates.md",
                                                                                 "content": GATES_SEMI.replace("🔒 SECURITY   ⬜", "🔒 SECURITY   ✅")},
                                                                        gates=GATES_NONE), "ask"),
    ("B5 Windows settings path", lambda: edit("Write", {"file_path": "C:\\Users\\me\\.claude\\settings.json", "content": "{}"}), "ask"),
    ("B5 bash write to Windows settings path", lambda: bash("copy x C:\\Users\\me\\.claude\\settings.local.json > out"), "ask"),
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
    ("B5 PowerShell Set-Content gate file", lambda: pwsh('Set-Content .claude\\dev-skills-gates.md "x"'), "ask"),
    ("B5 PowerShell Out-File gate file", lambda: pwsh("'x' | Out-File .claude/dev-skills-gates.md"), "ask"),
    ("B5 PowerShell Copy-Item settings", lambda: pwsh("Copy-Item x C:\\Users\\me\\.claude\\settings.json"), "ask"),
    ("B5 PowerShell .NET write gate file", lambda: pwsh("[IO.File]::WriteAllText('.claude/dev-skills-gates.md', 'x')"), "ask"),
    ("B5 PowerShell read gate file ok", lambda: pwsh("Get-Content .claude/dev-skills-gates.md"), "allow"),
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


def main() -> None:
    fails = 0
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
    total = len(CASES) + 1
    print(f"enforcement checks: {total - fails}/{total} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
