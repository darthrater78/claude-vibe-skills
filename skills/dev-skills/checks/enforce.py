#!/usr/bin/env python3
"""dev-skills enforcement checks.

Claude Code runs this file at fixed points once the dev-skills skill is loaded
(the `hooks:` block in SKILL.md registers it). It reads the payload Claude Code
sends on stdin, the project's gate file, and a compose file a docker command
names. It answers allow / deny / ask, and never runs a command. The only thing
it writes is a small status marker in the temp directory, so the session
banner can say whether enforcement is active.

Modes (argv[1]):
  pre-tool   PreToolUse: commands Claude runs, files Claude edits   (A1 A2 A4 A5 A6 B5 B6)
  stop       Stop: the reply Claude is about to end with            (C1 C2 C3 C4 C5 C7)
  post-ask   PostToolUse on AskUserQuestion: unanswered questions   (D1)

Every check is written out as a plain rule in ENFORCEMENT.md. Declining for a
session is the `Hook enforcement: declined` row in the gate file, which the user
confirms in a permission prompt (B5).
"""

from __future__ import annotations

import base64
import getpass
import ipaddress
import json
import os
import re
import shlex
import socket
import stat
import sys
import tempfile
import time
from typing import NoReturn

STATE_REL = ".dev-skills-gates.md"
GATE_EMOJI = {
    "VERSION": "🔢", "BUILD": "🔨", "SECURITY": "🔒",
    "DOCS": "📄", "RELEASE": "📦", "SHIP": "🚀",
}
WORK = ["SECURITY"]
PR = ["VERSION", "BUILD", "SECURITY", "DOCS"]
RELEASE = ["VERSION", "BUILD", "SECURITY", "DOCS", "RELEASE"]
NO_INTENT = re.compile(r"no publishing intent", re.I)
NO_INTENT_GATES = {"VERSION", "RELEASE", "SHIP"}
MAX_STOP_BLOCKS = 2  # per user prompt, then the reply goes through with a visible warning


# --- output -------------------------------------------------------------------

def emit(obj: dict) -> NoReturn:
    # Bytes, not text: on Windows sys.stdout encodes with the ANSI code page
    # (cp1252), which can't carry the emoji in these messages. Claude Code reads UTF-8.
    sys.stdout.buffer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.flush()
    sys.exit(0)


def pre_decision(kind: str, reason: str) -> NoReturn:
    emit({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": kind,
        "permissionDecisionReason": "dev-skills enforcement — " + reason,
    }})


def allow() -> NoReturn:
    sys.exit(0)


# --- status marker ------------------------------------------------------------

def state_dir() -> str:
    """Per-user folder for the status marker and the reply-fix counter. Refused
    if it's a symlink or someone else's, so another local user can't redirect
    these writes by creating it first."""
    user = re.sub(r"[^A-Za-z0-9_.-]", "", getpass.getuser() or "user")[:64]
    d = os.path.join(tempfile.gettempdir(), f"dev-skills-enforcement-{user}")
    os.makedirs(d, mode=0o700, exist_ok=True)
    st = os.lstat(d)
    if stat.S_ISLNK(st.st_mode) or (hasattr(os, "getuid") and st.st_uid != os.getuid()):
        raise OSError(f"refusing {d}: symlink or not owned by this user")
    return d


def mark_active(payload: dict) -> None:
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(payload.get("session_id", "")))[:80]
    if not sid:
        return
    try:
        with open(os.path.join(state_dir(), sid), "w", encoding="utf-8") as fh:
            fh.write(str(int(time.time())))
    except OSError:
        pass


# --- repo and gate file -------------------------------------------------------

def repo_root(start: str | None) -> str | None:
    cur = os.path.abspath(start or ".")
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def read(path: str | None) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


class Gates:
    def __init__(self, root: str | None) -> None:
        self.root = root
        self.path = os.path.join(root, STATE_REL) if root else None
        self.text = read(self.path) if self.path else None
        self.lines = (self.text or "").splitlines()

    @property
    def exists(self) -> bool:
        return self.text is not None

    def first(self, prefix: str) -> str | None:
        for line in self.lines:
            if line.startswith(prefix):
                return line
        return None

    @property
    def declined(self) -> bool:
        line = self.first("Hook enforcement:") or self.first("Enforcement:")
        return bool(line and re.match(r"(Hook )?[Ee]nforcement:\s*declined\b", line))

    @property
    def mode_ok(self) -> bool:
        line = self.first("Mode:")
        return bool(line and re.match(r"Mode:\s*(manual|semi-autonomous)(\s|$)", line))

    def row(self, gate: str) -> str | None:
        pat = re.compile(r"^\s*" + re.escape(GATE_EMOJI[gate]) + r"️?\s*" + gate + r"\b")
        for line in self.lines:
            if pat.match(line):
                return line
        return None

    def row_notes(self, gate: str) -> str:
        """The row's first line plus its indented evidence lines, for text notes
        (handoff, test artifact, test creds). Pass/fail is never read from here."""
        first = self.row(gate)
        if first is None:
            return ""
        i = self.lines.index(first)
        out = [first]
        for line in self.lines[i + 1:]:
            if not line.strip() or not line[:1].isspace():
                break
            out.append(line)
        return "\n".join(out)

    @property
    def work_track(self) -> bool:
        return bool(re.match(r"Track:\s*work commit", self.first("Track:") or "", re.I))

    def no_intent_rows(self) -> list[str]:
        return [line.strip() for gate in GATE_EMOJI if (line := self.row(gate))
                and "➖" in line and NO_INTENT.search(line)]

    def missing(self, required: list[str]) -> list[str]:
        out = []
        for gate in required:
            line = self.row(gate)
            if line is None:
                out.append(f"{gate} — no '{GATE_EMOJI[gate]} {gate}' row")
            elif "✅" not in line and "➖" not in line:
                out.append(line.strip())
            elif "✅" not in line and NO_INTENT.search(line):
                # ➖ "no publishing intent" is only for VERSION, RELEASE and SHIP, on the
                # work-commit track (SKILL.md §2, "A merge ... with no publishing intent").
                if gate not in NO_INTENT_GATES:
                    out.append(f"{line.strip()} (➖ no publishing intent covers only VERSION, RELEASE and SHIP)")
                elif not self.work_track:
                    out.append(f"{line.strip()} (➖ no publishing intent needs 'Track: work commit')")
        return out

    def origin(self) -> tuple[str | None, bool]:
        line = self.first("Origin:") or ""
        m = re.match(r"Origin:\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", line)
        return (m.group(1) if m else None), ("fork of" in line.lower())

    def host_network_approved(self, name: str | None) -> bool:
        if not name:
            return False
        for line in self.lines:
            if line.startswith("Host network:") and "approved" in line \
                    and re.search(r"(^|[\s:,])" + re.escape(name) + r"([\s,]|$)", line):
                return True
        return False


def git_head_branch(root: str | None) -> str | None:
    head = read(os.path.join(root, ".git", "HEAD")) if root else None
    m = re.match(r"ref: refs/heads/(\S+)", head or "")
    return m.group(1) if m else None


def default_branches(root: str | None) -> set[str]:
    ref = read(os.path.join(root, ".git", "refs", "remotes", "origin", "HEAD")) if root else None
    m = re.match(r"ref: refs/remotes/origin/(\S+)", ref or "")
    return {m.group(1)} if m else {"main", "master"}


# --- shell parsing ------------------------------------------------------------

OPS = {"&&", "||", ";", "|", "&", "(", ")", ";;", "|&", "\n"}
WRAPPERS = {"sudo", "env", "command", "nohup", "time", "exec", "nice", "stdbuf", "timeout", "xargs"}


# Programs that run what they read as commands. A heredoc or here-string fed to
# one of them is checked like any other command text.
SHELL_READERS = {"bash", "sh", "zsh", "dash", "ksh", "fish", "pwsh", "powershell", "cmd", "eval", "iex",
                 "invoke-expression", "xargs", "source", "."}


def line_tokens(line: str) -> list[str]:
    """Tokens with their quotes kept, so a quoted `<<` stays inside its string."""
    lexer = shlex.shlex(line, posix=False, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        return list(lexer)
    except ValueError:
        return line.split()


def heredoc_marks(tokens: list[str]) -> list[tuple[str, bool, bool]]:
    """(delimiter, quoted, strip leading tabs) for each `<<` heredoc on a line."""
    marks = []
    for i, tok in enumerate(tokens):
        m = re.match(r"^[^'\"<]*<<(?!<)(-?)(.*)$", tok)
        if not m:
            continue
        dash, word = m.group(1), m.group(2) or (tokens[i + 1] if i + 1 < len(tokens) else "")
        quoted = word[:1] in ("'", '"', "\\")
        delim = word.strip("'\"\\")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", delim):
            marks.append((delim, quoted, bool(dash)))
    return marks


def split_heredocs(text: str) -> tuple[str, list[str], list[str]]:
    """Take heredoc bodies out of the command text.

    Returns the command lines, the bodies a shell will run (checked as
    commands), and the unquoted data bodies (checked only for `$( )`, which bash
    still expands in them). A quoted data body (`python3 - <<'EOF'`) is inert.
    """
    lines = text.split("\n")
    keep, run, expand = [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        keep.append(line)
        i += 1
        if "<<" not in line:
            continue
        tokens = line_tokens(line)
        fed = any(program_name(t.strip("'\"")) in SHELL_READERS for t in tokens)
        for delim, quoted, dash in heredoc_marks(tokens):
            body = []
            while i < len(lines):
                b = lines[i]
                i += 1
                if (b.lstrip("\t") if dash else b).rstrip("\r") == delim:
                    break
                body.append(b)
            if fed:
                run.append("\n".join(body))
            elif not quoted:
                expand.append("\n".join(body))
    return "\n".join(keep), run, expand


def simple_commands(text: str, depth: int = 0, ps: bool = False) -> list[list[str]]:
    """Split a shell string into argv lists, unwrapping env/sudo/bash -c and friends.

    ps: the text is PowerShell, where `\\` is a path separator, not an escape.
    """
    if depth > 4 or not text:
        return []
    run_bodies, expand_bodies = [], []
    if not ps and "<<" in text:
        text, run_bodies, expand_bodies = split_heredocs(text)
    tokens = []
    # One line at a time, so a `#` comment ends at its own line and doesn't
    # swallow the rest of a multi-line block.
    for line in (text if ps else re.sub(r"\\\r?\n", " ", text)).splitlines():
        lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        if ps:
            lexer.escape = ""
        try:
            tokens.extend(list(lexer))
        except ValueError:
            tokens.extend(line.split())
        tokens.append(";")
    cmds, cur = [], []
    for tok in tokens:
        if tok in OPS or set(tok) <= set(";&|()"):
            if cur:
                cmds.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        cmds.append(cur)
    out = []
    for argv in cmds:
        out.extend(unwrap(argv, depth, ps))
    # Command substitutions: $(git push), and `git push` outside PowerShell
    # (where the backtick is the escape character).
    subst = r"\$\(([^()]*)\)()" if ps else r"\$\(([^()]*)\)|`([^`]*)`"
    for inner in re.findall(subst, "\n".join([text] + expand_bodies)):
        out.extend(simple_commands(inner[0] or inner[1], depth + 1, ps))
    for body in run_bodies:
        out.extend(simple_commands(body, depth + 1))
    return out


# Compared case-insensitively and without `.exe`, so Windows spellings
# (`git.exe`, `C:\Program Files\Git\cmd\git.exe`, `Git`) classify like `git`.
KNOWN_PROGRAMS = {"git", "gh", "docker", "podman", "bash", "sh", "zsh", "dash", "ksh", "fish", "pwsh",
                  "powershell", "cmd", "eval", "iex", "invoke-expression", "xargs", "source",
                  "start-process", "saps", "start"}

# Start-Process switches that take no value; every other named parameter does.
PS_SWITCHES = {"wait", "nonewwindow", "passthru", "usenewenvironment", "loaduserprofile"}


def start_process(argv: list[str], depth: int) -> list[list[str]]:
    """`Start-Process git -ArgumentList 'push'` runs `git push`, in -WorkingDirectory if given."""
    named: dict[str, str] = {}
    positional: list[str] = []
    j = 1
    while j < len(argv):
        a = argv[j]
        if a[:1] == "-" and len(a) > 1:
            name = a[1:].lower().rstrip(":")
            if not any(s.startswith(name) for s in PS_SWITCHES):
                named[name] = argv[j + 1] if j + 1 < len(argv) else ""
                j += 1
        else:
            positional.append(a)
        j += 1
    pick = lambda full, pos: next((v for k, v in named.items() if full.startswith(k)), None) or \
        (positional[pos] if len(positional) > pos else "")  # noqa: E731
    exe, args = pick("filepath", 0), pick("argumentlist", 1)
    if not exe:
        return [argv]
    out = simple_commands(exe + " " + args.replace(",", " "), depth + 1, ps=True)
    # -WorkingDirectory applies to the started process only, so it becomes
    # `git -C <dir>` there, never a cd that would carry on to later commands.
    wd = pick("workingdirectory", len(argv))
    if wd:
        out = [["git", "-C", wd] + a[1:] if a[:1] == ["git"] else a for a in out]
    return out


def program_name(tok: str) -> str:
    base = re.split(r"[/\\]", tok)[-1]
    low = re.sub(r"\.exe$", "", base.lower())
    return low if low in KNOWN_PROGRAMS else base


def ps_param(arg: str, full: str, shortest: int) -> bool:
    """PowerShell accepts any unambiguous prefix of a parameter: -c, -Com, -Command."""
    name = arg[1:].lower()
    return arg[:1] in "-/" and len(name) >= shortest and full.startswith(name)


def ps_encoded(arg: str) -> str:
    try:
        return base64.b64decode(arg, validate=True).decode("utf-16-le")
    except (ValueError, UnicodeDecodeError):
        return ""


def unwrap(argv: list[str], depth: int, ps: bool = False) -> list[list[str]]:
    i = 0
    while i < len(argv):
        tok = argv[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tok):
            i += 1
            continue
        if tok in WRAPPERS:
            i += 1
            while i < len(argv) and (argv[i].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[i])
                                     or (tok == "timeout" and re.match(r"^\d", argv[i]))):
                i += 1
            continue
        break
    argv = argv[i:]
    if not argv:
        return []
    base = program_name(argv[0])
    argv = [base] + argv[1:]
    if base in SHELL_READERS:
        # Here-string: `bash <<< "git push"` runs the string.
        for j, a in enumerate(argv[1:], 1):
            if a.startswith("<<<"):
                inner = a[3:] or (argv[j + 1] if j + 1 < len(argv) else "")
                return [argv] + simple_commands(inner, depth + 1, base in ("pwsh", "powershell"))
    if base in ("start-process", "saps", "start"):
        return start_process(argv, depth)
    if base in ("bash", "sh", "zsh", "dash") and "-c" in argv:
        j = argv.index("-c")
        return simple_commands(argv[j + 1], depth + 1) if j + 1 < len(argv) else []
    if base in ("pwsh", "powershell"):
        for j, a in enumerate(argv[1:], 1):
            if ps_param(a, "command", 1):
                return simple_commands(" ".join(argv[j + 1:]), depth + 1, ps=True)
            if ps_param(a, "encodedcommand", 1) or a.lower() in ("-ec", "/ec"):
                return simple_commands(ps_encoded(argv[j + 1]) if j + 1 < len(argv) else "", depth + 1, ps=True)
        return [argv]
    if base == "cmd":
        j = next((j for j, a in enumerate(argv) if a.lower() in ("/c", "/k")), None)
        return simple_commands(" ".join(argv[j + 1:]), depth + 1) if j is not None else [argv]
    if base in ("eval", "iex", "invoke-expression"):
        return simple_commands(" ".join(argv[1:]), depth + 1, ps or base != "eval")
    return [argv]


def resolve_cd(argv: list[str], cur: str | None) -> str | None:
    """Where a `cd` leaves the shell, or None when it can't be known statically."""
    target = next((a for a in argv[1:] if not a.startswith("-")), "~")
    if cur is None or re.search(r"[$`*?]", target) or target == "-":
        return None
    path = os.path.expanduser(target)
    return os.path.normpath(path if os.path.isabs(path) else os.path.join(cur, path))


def git_dash_c(argv: list[str], cur: str | None) -> str | None:
    """The directory a git command acts on: `git -C <dir>` overrides the shell's."""
    if not argv or os.path.basename(argv[0]) != "git":
        return cur
    for i, a in enumerate(argv[1:-1], 1):
        if a == "-C":
            return resolve_cd(["cd", argv[i + 1]], cur)
        if not a.startswith("-") and argv[i - 1] not in ("-c", "-C"):
            break
    return cur


def git_argv(argv: list[str]) -> list[str] | None:
    """Strip git's global options: git -C dir -c k=v --no-pager push ... -> [push, ...]."""
    if not argv or os.path.basename(argv[0]) != "git":
        return None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            break
    return argv[i:]


TAG_READ_FLAGS = re.compile(r"^(-l|--list|-d|--delete|-v|--verify|--contains|--no-contains|--points-at|--merged|"
                            r"--no-merged|-n\d*|--column|--no-column|-i|--ignore-case|--sort(=.*)?|--format(=.*)?)$")
VERSIONISH = re.compile(r"^v?\d+\.\d+(\.\d+)?([-.+].*)?$")


class Op:
    def __init__(self, kind: str, label: str, reason: str = "") -> None:
        self.kind = kind      # work | pr | release | user_only
        self.label = label
        self.reason = reason
        self.targets_default = False
        self.remote = None
        self.gh_repos = []
        self.is_gh = False
        self.publishes = False  # a tag or a GitHub release: never on the work-commit track


def classify(argv: list[str], root: str | None) -> list["Op"]:
    ops = []
    g = git_argv(argv)
    if g is not None and g:
        sub, args = g[0], g[1:]
        if sub == "commit":
            ops.append(Op("work", "git commit"))
        elif sub == "tag":
            flags = [a for a in args if a.startswith("-")]
            names = [a for a in args if not a.startswith("-")]
            if any(f in ("-d", "--delete") for f in flags):
                pass  # local tag deletion, not a ref on the remote
            elif names and not any(TAG_READ_FLAGS.match(f) for f in flags):
                ops.append(Op("user_only", "creating a tag", "tag creation"))
                ops[-1].publishes = True
        elif sub == "push":
            ops.extend(classify_push(args, root))
    base = os.path.basename(argv[0]) if argv else ""
    if base == "gh" and len(argv) > 1:
        ops.extend(classify_gh(argv[1:]))
    return ops


def classify_push(args: list[str], root: str | None) -> list["Op"]:
    if any(a in ("-n", "--dry-run") for a in args):
        return []
    flags = [a for a in args if a.startswith("-")]
    pos = [a for a in args if not a.startswith("-")]
    if any(f in ("--tags", "--follow-tags", "--mirror", "--delete", "-d", "--prune") for f in flags):
        op = Op("user_only", "pushing tags or deleting a ref", "tag push / ref deletion")
        op.publishes = any(f in ("--tags", "--follow-tags", "--mirror") for f in flags)
        return [op]
    remote = pos[0] if pos else None
    refspecs = pos[1:]
    branch = git_head_branch(root)
    defaults = default_branches(root)
    op = Op("work", "git push")
    op.remote = remote
    if not refspecs:
        refspecs = [branch or "HEAD"]
    for spec in refspecs:
        spec = spec.lstrip("+")
        if spec.startswith(":"):
            return [Op("user_only", "deleting a remote ref", "ref deletion")]
        src, _, dst = spec.partition(":")
        dst = dst or src
        if "refs/tags/" in spec or VERSIONISH.match(dst):
            op = Op("user_only", "pushing a tag", "tag push")
            op.publishes = True
            return [op]
        dst = dst.replace("refs/heads/", "")
        if dst == "HEAD":
            dst = branch or "HEAD"
        if dst in defaults:
            op.kind, op.label, op.targets_default = "release", f"a push to the default branch ({dst})", True
    return [op]


def gh_repo_flags(args: list[str]) -> list[str]:
    repos = []
    for i, a in enumerate(args):
        if a in ("--repo", "-R") and i + 1 < len(args):
            repos.append(args[i + 1])
        elif a.startswith("--repo=") or (a.startswith("-R") and len(a) > 2):
            repos.append(a.split("=", 1)[1] if "=" in a else a[2:])
    return [re.sub(r"^https?://github\.com/|\.git$", "", r) for r in repos]


def classify_gh(args: list[str]) -> list["Op"]:
    words = [a for a in args if not a.startswith("-")]
    head = words[:2]
    op = None
    if head == ["pr", "create"]:
        op = Op("pr", "opening a pull request")
    elif head == ["pr", "merge"]:
        if any(a in ("--delete-branch", "-d") for a in args):
            op = Op("user_only", "gh pr merge --delete-branch", "branch deletion")
        else:
            op = Op("release", "merging a pull request")
            op.targets_default = True
    elif head == ["release", "create"]:
        op = Op("release", "creating a release")
        op.publishes = True
    elif head == ["release", "delete"]:
        op = Op("user_only", "deleting a release", "release deletion")
    elif words[:1] == ["api"]:
        method = None
        for i, a in enumerate(args):
            if a in ("-X", "--method") and i + 1 < len(args):
                method = args[i + 1].upper()
            elif a.startswith("--method=") or (a.startswith("-X") and len(a) > 2):
                method = a.split("=", 1)[1].upper() if "=" in a else a[2:].upper()
        if method is None and any(a in ("-f", "-F", "--field", "--raw-field", "--input") for a in args):
            method = "POST"
        endpoint = next((w for w in words[1:] if "/" in w), "")
        if method in ("POST", "PATCH", "PUT", "DELETE"):
            if re.search(r"git/refs|/git/tags", endpoint):
                op = Op("user_only", "creating or deleting a ref through gh api", "ref operation")
            elif re.search(r"/pulls/\d+/merge", endpoint):
                op = Op("release", "merging a pull request through gh api")
                op.targets_default = True
            elif re.search(r"/releases(/|$)", endpoint):
                op = Op("user_only" if method == "DELETE" else "release", "a release through gh api")
                op.publishes = method != "DELETE"
    if op:
        op.is_gh = True
        op.gh_repos = gh_repo_flags(args)
        return [op]
    return []


REQUIRED = {"work": WORK, "pr": PR, "release": RELEASE}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "build", "dist"}


def find_names(root: str | None, names: set[str], depth: int = 4) -> bool:
    if not root:
        return False
    base = root.rstrip(os.sep).count(os.sep)
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS] if cur.count(os.sep) - base < depth else []
        low = {f.lower() for f in files}
        if low & names or any(f.endswith((".csproj", ".sln")) for f in low) and ".csproj" in names:
            return True
    return False


def artifact_repo(root: str | None) -> bool:
    return find_names(root, {"dockerfile", "androidmanifest.xml", "build.gradle", "build.gradle.kts", ".csproj"})


def docker_repo(root: str | None) -> bool:
    return find_names(root, {"dockerfile", "compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"})


def gate_problems(ops: list[Op], gates: Gates, presented: bool, text_for_fork: str = "") -> list[str]:
    """Problems for these operations against the gate file. Empty list = allowed."""
    if not ops:
        return []
    if not gates.exists:
        return [f"no gate file at {STATE_REL}. Write it (SESSION_START.md) and run the gates first."]
    if not gates.mode_ok:
        return ["the operating mode is not chosen (Mode: row). Ask the mode question first."]
    problems = []
    slug, is_fork = gates.origin()
    for op in ops:
        if op.publishes and (gates.work_track or gates.no_intent_rows()):
            problems.append(f"{op.label} publishes, but the gate file is on the work-commit track "
                            "(Track: work commit, or a ➖ no publishing intent row). A release runs all six gates.")
            continue
        if op.kind == "user_only":
            if not presented:
                problems.append(f"{op.label} is the user's to run in both modes (SKILL.md §5.8). "
                                "Present it as a ▶️ RUN THIS block instead.")
                continue
            if "tag" in op.reason:
                miss = gates.missing(RELEASE)
                if miss:
                    problems.append(f"{op.label} before the merge is confirmed. Not ✅: " + "; ".join(miss))
            continue
        required = REQUIRED[op.kind]
        miss = gates.missing(required)
        if miss:
            problems.append(f"{op.label} needs {', '.join(required)}. Not ✅ or ➖: " + "; ".join(miss))
        build = gates.row("BUILD") or ""
        notes = gates.row_notes("BUILD").lower()
        if "BUILD" in required and "✅" in build and "handoff" not in notes and artifact_repo(gates.root):
            problems.append("BUILD is ✅ with no 'handoff' note, but this repo builds a Docker image, .exe or .apk. "
                            "Offer the user the test artifact (GATE_REFERENCE.md Gate 2) and note it on the BUILD row.")
        if op.targets_default and artifact_repo(gates.root):
            if "test artifact:" not in notes:
                problems.append("no 'test artifact: <path or link> @ <sha>' on the BUILD row. Nothing merges "
                                "without a test artifact built from the merged commit (Gate 2).")
            if docker_repo(gates.root) and "test creds" not in notes:
                problems.append("no 'test creds: …' note on the BUILD row. Docker test runs get fresh "
                                "throwaway credentials, shown to the user (Gate 2).")
        if op.kind == "release":
            sec = gates.row("SECURITY") or ""
            if "✅" in sec and not re.search(r"(^|[^0-9])0\s+open", sec):
                problems.append("SECURITY is ✅ but its row does not say '0 open'. Nothing releases with an open finding.")
        if slug:
            if op.is_gh:
                for r in op.gh_repos:
                    if r != slug:
                        problems.append(f"{op.label} targets {r}, not {slug}.")
                if is_fork and not op.gh_repos and "GH_REPO=" not in text_for_fork:
                    problems.append(f"{op.label} has no --repo in a fork, so it would target the parent repo. Pass --repo {slug}.")
            if is_fork and op.label.startswith("git push") and op.remote not in (None, "origin"):
                problems.append("git push must go to origin (the fork).")
            if is_fork and op.label == "git push" and op.remote is None:
                problems.append("git push must name origin (the fork) explicitly.")
    return problems


# --- A1 / A2: docker ----------------------------------------------------------

def lan_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("1.1.1.1", 80))  # UDP connect sends nothing; it only picks the route
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


# The documented ways to read the host's LAN IP from its default route: `ip` on
# Linux, Find-NetRoute on Windows (from PowerShell, or through powershell.exe in Git Bash).
ROUTE_RECIPE = re.compile(r"HOST_IP=\"?\$\(\s*ip\s+-4\s+route\s+get\s+1\.1\.1\.1"
                          r"|HOST_IP\s*=\s*\"?\$?\(\s*(powershell(\.exe)?\s+(-NoProfile\s+)?-Command\s+[\"']?\(?)?"
                          r"\(?\s*Find-NetRoute\s+-RemoteIPAddress\s+1\.1\.1\.1", re.I)


def port_problem(spec: str, env: dict[str, str], recipe_ok: bool) -> str | None:
    """Problem with one published-port spec, or None."""
    spec = spec.strip().strip("'\"")
    spec = re.sub(r"\$\(\$(\w+)\)", r"${\1}", spec)  # PowerShell "$($HOST_IP):8080:80"
    for var in re.findall(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?", spec):
        if var in env:
            spec = re.sub(r"\$\{?" + var + r"\}?", env[var], spec)
        elif var == "HOST_IP" and recipe_ok:
            spec = re.sub(r"\$\{?HOST_IP\}?", "__ROUTE__", spec)
        else:
            return f"'{spec}' uses ${var}, which can't be checked. Use the LAN IP or the documented HOST_IP recipe."
    if spec.startswith("["):
        ip, _, rest = spec[1:].partition("]")
        return f"'{spec}' publishes on {ip}, not the LAN IP." if ip else None
    parts = spec.split("/")[0].split(":")
    if len(parts) < 3:
        return f"'{spec}' publishes on every interface. Bind it to the LAN IP: -p <LAN IP>:{parts[-1]}:{parts[-1]}"
    ip = parts[0]
    if ip == "__ROUTE__":
        return None
    if ip in ("localhost", "0.0.0.0", "127.0.0.1") or ip.startswith("127."):
        return f"'{spec}' publishes on {ip}. The user tests from other machines: use the LAN IP."
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return f"'{spec}': '{ip}' is not an IP address."
    if not addr.is_private or addr.is_loopback:
        return f"'{spec}': {ip} is not a private LAN address. Stop and ask the user before publishing."
    lan = lan_ip()
    if lan is None:
        return f"'{spec}': can't confirm {ip} is the host's LAN IP (no route to check against)."
    if ip != lan:
        return f"'{spec}': {ip} is not the host's LAN IP ({lan}). Docker bridge addresses can't be reached from other machines."
    return None


def temp_roots() -> list[str]:
    roots = {"/tmp", "/var/tmp", tempfile.gettempdir(), os.environ.get("TMPDIR", "")}
    return [os.path.realpath(r) for r in roots if r]


def in_temp(path: str, base: str) -> bool:
    """A bind-mount source under a temp folder, which a reboot wipes."""
    if not path or not (path.startswith(("/", ".", "~", "$")) or "/" in path):
        return False  # a named volume, not a host path
    path = os.path.expanduser(re.sub(r"\$\{?(TMPDIR|TMP|TEMP)\}?", tempfile.gettempdir(), path))
    full = os.path.realpath(path if os.path.isabs(path) else os.path.join(base, path))
    return any(full == r or full.startswith(r + os.sep) for r in temp_roots())


RESTARTS = ("always", "unless-stopped", "on-failure")
TEST_LABEL = "dev-skills.test"
TEST_PROJECT = "dev-skills-test"


def mkdir_targets(text: str, base: str) -> set[str]:
    """Folders an earlier `mkdir -p` in the same command creates (as the user)."""
    out = set()
    for argv in simple_commands(text):
        if argv and argv[0] == "mkdir":
            for a in argv[1:]:
                if not a.startswith("-"):
                    a = os.path.expanduser(a)
                    out.add(os.path.realpath(a if os.path.isabs(a) else os.path.join(base, a)))
    return out


def temp_mount_problems(who: str, sources: list[str], as_user: bool, text: str, base: str) -> list[str]:
    """A10: a bind mount under a temp folder must never end up owned by root."""
    problems = []
    if os.name == "nt":
        return problems  # Docker Desktop creates missing mount folders as the Windows user, not root
    for src in sources:
        if not in_temp(src, base):
            continue
        if re.search(r"\$(?!\{?(TMPDIR|TMP|TEMP)\b)", src):
            problems.append(f"{who}: the temp mount {src} uses a variable that can't be checked. Use a literal path.")
            continue
        full = os.path.realpath(os.path.expanduser(re.sub(r"\$\{?(TMPDIR|TMP|TEMP)\}?", tempfile.gettempdir(), src)))
        if not as_user:
            problems.append(f"{who} bind-mounts {src} from a temp folder but doesn't run as the user, so it writes "
                            "root-owned files there. Add --user \"$(id -u):$(id -g)\" (or PUID/PGID for images that use "
                            "them). If it has to run as root, mount from outside temp, e.g. /opt/docker/<name>-test/.")
        if os.path.exists(full):
            if hasattr(os, "getuid") and os.stat(full).st_uid != os.getuid():
                problems.append(f"{who}: {src} already exists and isn't owned by the user (root-created?). "
                                "Don't reuse it: pick a fresh folder created with mkdir -p.")
        elif not any(full == m or full.startswith(m + os.sep) for m in mkdir_targets(text, base)):
            problems.append(f"{who}: {src} doesn't exist yet, so Docker would create it as root. "
                            f"Run mkdir -p {src} first in the same command.")
    return problems


def restart_mount_problem(who: str, restart: str | None, sources: list[str], base: str) -> str | None:
    if os.name == "nt":
        return None  # A9 is about a Linux reboot wiping /tmp; Windows doesn't clear %TEMP% on boot
    restart = (restart or "").strip("'\" ").split(":")[0]
    temp = [src for src in sources if in_temp(src, base)]
    if restart in RESTARTS and temp:
        return (f"{who} has restart policy '{restart}' and bind-mounts {temp[0]} from a temp folder. "
                "After a reboot wipes it, Docker restarts the container and recreates the folder as root. "
                "Use --rm and no restart policy for test containers, or mount from outside the temp folder.")
    return None


def compose_file(argv: list[str], cwd: str) -> str | None:
    for i, a in enumerate(argv):
        if a in ("-f", "--file") and i + 1 < len(argv):
            p = argv[i + 1]
            return p if os.path.isabs(p) else os.path.join(cwd, p)
        if a.startswith("--file="):
            p = a.split("=", 1)[1]
            return p if os.path.isabs(p) else os.path.join(cwd, p)
    for name in ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"):
        p = os.path.join(cwd, name)
        if os.path.isfile(p):
            return p
    return None


def compose_scan(text: str) -> dict[str, dict]:
    """Minimal compose reader: (service, port specs, host_ip-less long ports, network_mode host)."""
    services, cur, cur_name = {}, None, None
    in_services, svc_indent = False, None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.split(" #")[0].rstrip()
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            in_services = line.startswith("services:")
            continue
        if not in_services:
            continue
        if svc_indent is None or indent <= svc_indent:
            m = re.match(r"\s*([A-Za-z0-9_.-]+):\s*$", line)
            if m:
                svc_indent = indent
                cur_name = m.group(1)
                cur = services.setdefault(cur_name, {"ports": [], "host": False, "name": cur_name,
                                                     "restart": None, "volumes": [], "as_user": False,
                                                     "puid": False, "pgid": False})
            continue
        if cur is None:
            continue
        s = line.strip()
        m = re.match(r"network_mode:\s*[\"']?host[\"']?\s*$", s)
        if m:
            cur["host"] = True
        if re.match(r"user:\s*\S", s):
            cur["as_user"] = True
        if re.search(r"\bPUID\b", s):
            cur["puid"] = True
        if re.search(r"\bPGID\b", s):
            cur["pgid"] = True
        if cur["puid"] and cur["pgid"]:
            cur["as_user"] = True
        m = re.match(r"restart:\s*[\"']?([^\"'\s]+)", s)
        if m:
            cur["restart"] = m.group(1)
        if re.match(r"volumes:\s*$", s):
            vindent = indent
            while i < len(lines):
                nxt = lines[i].split(" #")[0].rstrip()
                if not nxt.strip():
                    i += 1
                    continue
                if len(nxt) - len(nxt.lstrip()) <= vindent:
                    break
                ns = nxt.strip()
                km = re.match(r"-?\s*source:\s*[\"']?([^\"'\s]+)", ns)
                if km:
                    cur["volumes"].append(km.group(1))
                elif ns.startswith("- ") and not re.match(r"-\s+[a-z_]+:", ns):
                    cur["volumes"].append(ns[2:].strip().strip("'\"").split(":")[0])
                i += 1
            continue
        m = re.match(r"container_name:\s*[\"']?([^\"'\s]+)", s)
        if m:
            cur["name"] = m.group(1)
        if re.match(r"ports:\s*$", s):
            pindent = indent
            while i < len(lines):
                nxt = lines[i].split(" #")[0].rstrip()
                if not nxt.strip():
                    i += 1
                    continue
                nind = len(nxt) - len(nxt.lstrip())
                if nind <= pindent:
                    break
                ns = nxt.strip()
                if ns.startswith("- ") and not re.match(r"-\s+[a-z_]+:", ns):
                    cur["ports"].append(ns[2:].strip())
                elif ns.startswith("- ") or ":" in ns:
                    # long syntax: collect one mapping's keys
                    entry = {}
                    km = re.match(r"-?\s*([a-z_]+):\s*(.*)", ns)
                    if km:
                        entry[km.group(1)] = km.group(2).strip("'\" ")
                    i += 1
                    while i < len(lines):
                        n2 = lines[i].split(" #")[0].rstrip()
                        n2s = n2.strip()
                        n2ind = len(n2) - len(n2.lstrip())
                        if not n2s:
                            i += 1
                            continue
                        if n2ind <= nind or n2s.startswith("- "):
                            break
                        km = re.match(r"([a-z_]+):\s*(.*)", n2s)
                        if km:
                            entry[km.group(1)] = km.group(2).strip("'\" ")
                        i += 1
                    if "published" in entry:
                        hip = entry.get("host_ip", "")
                        cur["ports"].append(f"{hip}:{entry['published']}:{entry.get('target', '')}" if hip
                                            else f"{entry['published']}:{entry.get('target', '')}")
                    continue
                i += 1
    return services


DOCKER_VALUE_FLAGS = {"--context", "-c", "-H", "--host", "--config", "--log-level", "-l",
                      "-p", "--project-name", "-f", "--file", "--env-file", "--profile",
                      "--project-directory", "--ansi", "--parallel", "--progress"}


def docker_words(args: list[str]) -> list[str]:
    """The subcommand words (compose, up, run, ...) with global flags and their values skipped."""
    words, i = [], 0
    while i < len(args):
        a = args[i]
        if a in DOCKER_VALUE_FLAGS:
            i += 2
            continue
        if not a.startswith("-"):
            words.append(a)
            if a not in ("compose", "container"):
                break
        i += 1
    return words


def docker_checks(argv: list[str], text: str, cwd: str, gates: Gates) -> list[str]:
    if not argv or os.path.basename(argv[0]) not in ("docker", "podman"):
        return []
    args = argv[1:]
    words = docker_words(args)
    env = dict(re.findall(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=([0-9.]+)(?=\s)", " " + text + " "))
    recipe_ok = bool(ROUTE_RECIPE.search(text))
    problems = []
    is_run = words[:1] in (["run"], ["create"]) or words[:2] in (["container", "run"], ["container", "create"])
    is_up = words[:1] == ["compose"] and words[1:2] in (["up"], ["create"], ["run"], ["start"])
    if is_run:
        name = None
        restart = None
        mounts: list[str] = []
        as_user = any(a in ("-u", "--user") or a.startswith(("--user=", "-u=")) for a in args) \
            or (re.search(r"(-e|--env)[= ]PUID=", " ".join(args)) and re.search(r"(-e|--env)[= ]PGID=", " ".join(args)))
        labeled = any(TEST_LABEL in a for a in args)
        i = 0
        while i < len(args):
            a = args[i]
            val = None
            if a in ("-p", "--publish") and i + 1 < len(args):
                val = args[i + 1]
                i += 1
            elif a.startswith("--publish="):
                val = a.split("=", 1)[1]
            elif a.startswith("-p") and len(a) > 2 and not a.startswith("--"):
                val = a[2:]
            elif a in ("-P", "--publish-all"):
                problems.append("-P publishes every exposed port on every interface. Publish each on the LAN IP.")
            elif a in ("--network", "--net") and i + 1 < len(args):
                if args[i + 1] == "host":
                    problems.append("__HOST__")
                i += 1
            elif a in ("--network=host", "--net=host"):
                problems.append("__HOST__")
            elif a == "--restart" and i + 1 < len(args):
                restart = args[i + 1]
                i += 1
            elif a.startswith("--restart="):
                restart = a.split("=", 1)[1]
            elif a in ("-v", "--volume") and i + 1 < len(args):
                mounts.append(args[i + 1].split(":")[0])
                i += 1
            elif a.startswith("--volume="):
                mounts.append(a.split("=", 1)[1].split(":")[0])
            elif a == "--mount" and i + 1 < len(args):
                mm = re.search(r"(?:^|,)(?:source|src)=([^,]+)", args[i + 1])
                if mm and "type=bind" in args[i + 1]:
                    mounts.append("--mount:" + mm.group(1))
                i += 1
            elif a == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 1
            elif a.startswith("--name="):
                name = a.split("=", 1)[1]
            if val is not None:
                p = port_problem(val, env, recipe_ok)
                if p:
                    problems.append(p)
            i += 1
        who = f"container '{name or '(no --name)'}'"
        # --mount refuses a missing source instead of creating it, so only -v needs the mkdir check.
        plain = [m for m in mounts if not m.startswith("--mount:")]
        srcs = [m.replace("--mount:", "", 1) for m in mounts]
        p = restart_mount_problem(who, restart, srcs, cwd)
        if p:
            problems.append(p)
        problems.extend(temp_mount_problems(who, plain, bool(as_user), text, cwd))
        problems.extend(q for q in temp_mount_problems(who, [m for m in srcs if m not in plain], bool(as_user), text, cwd)
                        if "doesn't exist yet" not in q)
        if not labeled:
            problems.append(f"{who} has no --label {TEST_LABEL}=\"$CLAUDE_CODE_SESSION_ID\". Test containers are "
                            "labeled so the next session start can find any that were left behind.")
        if "__HOST__" in problems:
            problems.remove("__HOST__")
            if not gates.host_network_approved(name):
                problems.append(f"host networking for container '{name or '(no --name)'}' has no "
                                "'Host network: <name> approved <date> — <reason>' row in the gate file. "
                                "It needs the user's explicit permission first.")
    elif is_up:
        pdir = next((args[i + 1] for i, a in enumerate(args[:-1]) if a == "--project-directory"), None)
        cdir = os.path.join(cwd, os.path.expanduser(pdir)) if pdir else cwd
        path = compose_file(args, cdir)
        if path is None:
            return ["docker compose: no compose file found to check."]
        text_c = read(path)
        if text_c is None:
            return [f"docker compose: can't read {path} to check it."]
        for svc in compose_scan(text_c).values():
            for spec in svc["ports"]:
                p = port_problem(spec, env, recipe_ok)
                if p:
                    problems.append(f"service {svc['name']}: {p}")
            base = os.path.dirname(path)
            p = restart_mount_problem(f"service {svc['name']}", svc["restart"], svc["volumes"], base)
            if p:
                problems.append(p)
            problems.extend(temp_mount_problems(f"service {svc['name']}", svc["volumes"], svc["as_user"], text, base))
        project = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-p", "--project-name")), "")
        project = project or next((a.split("=", 1)[1] for a in args if a.startswith("--project-name=")), "")
        if not project.startswith(TEST_PROJECT) and TEST_LABEL not in text_c:
            problems.append(f"docker compose: run test stacks as -p {TEST_PROJECT}-<name> (or label the services "
                            f"{TEST_LABEL}), so the next session start can find any that were left behind.")
            if svc["host"] and not (gates.host_network_approved(svc["name"])):
                problems.append(f"service {svc['name']} uses network_mode: host without a "
                                "'Host network: <name> approved' row. It needs the user's explicit permission.")
    return problems


# --- B5: protected files ------------------------------------------------------

# Gate rows and the Mode: line pass without a prompt in both modes: the mode is
# the user's answer to the session-start question, and a gate passing is shown
# on the tracker and backed by the commit approval. What asks is the short list
# of lines that switch a check off or grant an exception, which only the user
# can decide.
SENSITIVE = [
    (re.compile(r"^(Hook )?[Ee]nforcement:\s*declined"), "declining hook enforcement"),
    (re.compile(r"^Host network:.*approved"), "a host-network approval"),
    (re.compile(r"waive", re.I), "a finding waiver"),
]


def sensitive_lines(text: str | None) -> set[str]:
    out = set()
    for line in (text or "").splitlines():
        for pat, _ in SENSITIVE:
            if pat.search(line):
                out.add(line.strip())
    return out


def protected_path(path: str | None, root: str | None) -> str | None:
    if not path:
        return None
    p = os.path.abspath(path)
    if p.endswith(os.sep + STATE_REL) or p.endswith("/" + STATE_REL.replace(os.sep, "/")):
        return "gate"
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin and os.path.abspath(p).startswith(os.path.abspath(plugin) + os.sep):
        return "checks"
    if re.search(r"(^|[/\\])\.claude[^/\\]*[/\\]settings(\.local)?\.json$", p):
        return "settings"
    return None


def new_content(tool: str, inp: dict, current: str | None) -> str:
    if tool == "Write":
        return inp.get("content", "")
    text = current or ""
    edits = inp.get("edits") if tool == "MultiEdit" else [inp]
    for e in edits or []:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        if e.get("replace_all"):
            text = text.replace(old, new)
        else:
            text = text.replace(old, new, 1)
    return text


def file_edit_check(tool: str, inp: dict, root: str | None) -> tuple[str, str] | None:
    path = inp.get("file_path") or inp.get("notebook_path")
    kind = protected_path(path, root)
    if kind is None:
        return None
    if kind in ("checks", "settings"):
        return ("ask", f"this edits {path}, which is where enforcement lives. The user decides.")
    current = read(path)
    new = new_content(tool, inp, current)
    added = sensitive_lines(new) - sensitive_lines(current)
    if not added:
        return None
    return ("ask", "the gate file change needs the user's OK:\n" + "\n".join(f"  + {line}" for line in sorted(added)))


WRITE_HINT = re.compile(r"(>|\btee\b|\bsed\s+-i|\bperl\s+-[a-z]*i|\bcp\b|\bmv\b|\brm\b|\bpython3?\b|\bnode\b|"
                        r"\btruncate\b|\bdd\b|\binstall\b|\bln\b|\bchmod\b|"
                        # PowerShell and cmd: cmdlets, their aliases, and .NET file writes.
                        r"\b(set|add|clear)-content\b|\bout-file\b|\b(copy|move|remove|rename|new)-item\b|"
                        r"\btee-object\b|\b(sc|ac|clc|cpi|mi|ri|rni|ni|copy|move|del|erase|ren|xcopy|robocopy)\b|"
                        r"\[(system\.)?io\.file\]::)", re.I)


def bash_protected_check(cmd: str) -> tuple[str, str] | None:
    home = os.path.expanduser("~")
    cmd = re.sub(r"(?<![\w/])~(?=/|\s|$)", home, cmd).replace("${HOME}", home).replace("$HOME", home)
    # `git rm --cached` only untracks the file (SESSION_START.md); it never writes it.
    cmd = re.sub(r"\bgit\s+(-C\s+\S+\s+)?rm\s+(-r\s+)?--cached\s+(-r\s+)?(--\s+)?[^\s;&|<>`$()]*dev-skills-gates\.md(?=\s|$|[;&|])",
                 "", cmd)
    touches = "dev-skills-gates.md" in cmd or re.search(r"\.claude[^/\\\s]*[/\\]settings(\.local)?\.json", cmd)
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin and plugin in cmd:
        touches = True
    if touches and WRITE_HINT.search(cmd.replace("2>&1", "").replace(">/dev/null", "").replace("2>/dev/null", "")):
        return ("ask", "this shell command may write the gate file, a settings file, or the enforcement checks. "
                       "Edit the gate file with the Edit/Write tools so the change can be shown line by line.")
    return None


GATE_FILE_SPEC = re.compile(r"(^|[/\\])\.?dev-skills-gates\.md$")
CLAUDE_DIR_SPEC = re.compile(r"^(\.|\./|:/|\.claude[/\\]?(\*)?|\./\.claude[/\\]?(\*)?)$")


def gate_file_add_check(argv: list[str]) -> str | None:
    """B6: on a local session the gate file is never staged (every session rewrites
    it, so a tracked copy blocks git checkout). Remote containers commit it."""
    g = git_argv(argv)
    if not g or g[0] != "add" or os.environ.get("CLAUDE_CODE_REMOTE", "").lower() in ("1", "true", "yes"):
        return None
    args = g[1:]
    short = "".join(a[1:] for a in args if re.match(r"^-[a-zA-Z]+$", a))
    force = "f" in short or "--force" in args
    every = "A" in short or "--all" in args
    specs = [a for a in args if not a.startswith("-")]
    if any(GATE_FILE_SPEC.search(s) for s in specs) or (force and any(CLAUDE_DIR_SPEC.match(s) for s in specs)) \
            or (force and every and not specs):
        return ("this stages the gate file (.dev-skills-gates.md) on a local session. The gate file stays untracked "
                "locally: every session rewrites it, so a committed copy blocks git checkout (SKILL.md §2).")
    return None


HANDOFF_SPEC = re.compile(r"(^|[/\\])(\.dev-skills-handoff\.md$|\.dev-skills-handoffs([/\\]|$)|\.claude[/\\]handoffs([/\\]|$))")
HANDOFF_REF = re.compile(r"refs/dev-skills/")


def handoff_add_check(argv: list[str]) -> str | None:
    """Handoffs stay local unless the session is a remote container, where they'd
    die with it. The user can still say yes to committing one, so this asks."""
    g = git_argv(argv)
    if not g or os.environ.get("CLAUDE_CODE_REMOTE", "").lower() in ("1", "true", "yes"):
        return None
    specs = [a for a in g[1:] if not a.startswith("-")]
    if g[0] == "add" and any(HANDOFF_SPEC.search(sp) for sp in specs):
        return ("this stages the handoff on a branch on a local session. Locally it's committed to the "
                "local-only ref refs/dev-skills/handoff, never to a branch that gets pushed (SKILL.md §5.6). "
                "Approve only if the user asked for this.")
    if g[0] == "push" and any(HANDOFF_REF.search(sp) for sp in specs):
        return ("this pushes the local handoff ref. Handoffs stay local unless the user asks (SKILL.md §5.6). "
                "Approve only if the user asked for this.")
    return None


# --- pre-tool -----------------------------------------------------------------

def pre_tool(payload: dict) -> NoReturn:
    tool = payload.get("tool_name", "")
    inp = payload.get("tool_input") or {}
    cwd = payload.get("cwd") or os.getcwd()
    root = repo_root(cwd) or os.environ.get("CLAUDE_PROJECT_DIR")
    gates = Gates(root)

    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        res = file_edit_check(tool, inp, root)
        if res:
            pre_decision(*res)
        allow()

    if gates.declined:
        allow()

    if tool in ("Bash", "PowerShell"):
        cmd = inp.get("command") or ""
        res = bash_protected_check(cmd)
        problems = []
        cur: str | None = cwd
        for argv in simple_commands(cmd, ps=tool == "PowerShell"):
            if argv and argv[0].lower() in ("cd", "pushd", "set-location", "sl", "chdir", "push-location"):
                cur = resolve_cd(argv, cur)
                continue
            here = git_dash_c(argv, cur)
            here_root = repo_root(here) if here else None
            here_gates = Gates(here_root) if here else gates
            ops = classify(argv, here_root)
            if ops and here is None:
                problems.append("a git write runs after a cd whose target can't be resolved "
                                "(a variable or command substitution), so there's no telling "
                                "which repo's gates apply. Use a literal path.")
            elif ops:
                problems.extend(gate_problems(ops, here_gates, presented=False, text_for_fork=cmd))
            staged = gate_file_add_check(argv)
            if staged:
                problems.append(staged)
            problems.extend(docker_checks(argv, cmd, here or cwd, here_gates))
        if problems:
            pre_decision("deny", "blocked:\n- " + "\n- ".join(problems))
        if res:
            pre_decision(*res)
        for argv in simple_commands(cmd, ps=tool == "PowerShell"):
            handoff = handoff_add_check(argv)
            if handoff:
                pre_decision("ask", handoff)
        allow()

    m = re.match(r"^mcp__(.+)__([a-z_]+)$", tool)
    if m and "github" in m.group(1).lower():
        name = m.group(2)
        if name in ("create_tag", "delete_branch", "delete_tag", "delete_ref", "delete_release"):
            pre_decision("deny", f"{name} is the user's to run (SKILL.md §5.8). Present the git command instead.")
        kind = {"create_pull_request": "pr", "merge_pull_request": "release",
                "create_release": "release", "push_files": "work",
                "create_or_update_file": "work", "delete_file": "work"}.get(name)
        if kind:
            op = Op(kind, name)
            op.is_gh = True
            op.publishes = name == "create_release"
            op.targets_default = name == "merge_pull_request"
            owner, repo = inp.get("owner"), inp.get("repo")
            if owner and repo:
                op.gh_repos = [f"{owner}/{repo}"]
            problems = gate_problems([op], gates, presented=False, text_for_fork="GH_REPO=" if op.gh_repos else "")
            if problems:
                pre_decision("deny", "blocked:\n- " + "\n- ".join(problems))
    allow()


# --- stop: the reply ----------------------------------------------------------

FENCE = re.compile(r"^(\s*)(```|~~~)")
BAD_URL = re.compile(r"https?://(localhost|127(?:\.\d{1,3}){3}|0\.0\.0\.0|\[::1\]|172\.1[7-9](?:\.\d{1,3}){2})(?=[:/\s)`'\"\]]|$)", re.I)
GIT_CMD = re.compile(r"(^|&&|\|\||[;|(])\s*(sudo\s+|env\s+)?(git\s+(-C\s+\S+\s+)?(add|commit|push|pull|checkout|switch|"
                     r"branch|merge|rebase|tag|reset|clone|remote|stash|cherry-pick|revert)"
                     r"|gh\s+(pr|release|api|repo|run|issue|auth|workflow))\b", re.M)
# A block of reads only (git status/log/diff/fetch, ls-remote) is not policed as a run block
# unless it is labeled one: a bounce costs a whole model request.
NO_REPLY = re.compile(r"no need to reply|(don'?t|do not) need to (reply|tell me|answer)|nothing (you need )?to reply", re.I)
ASKS = re.compile(r"\?\s*(\*\*)?\s*$|^\s*(\*\*)?(tell me|reply with|answer|let me know|say )", re.I | re.M)
SKELETON = """
Run-block shape (ENFORCEMENT.md C3-C7):
`<one-line tracker>`

### ▶️ RUN THIS — <what it does> · in <repo>
```bash
# ════════ ▶️ START: <what>
<commands chained with &&>
# ════════ ⏹️ END
```
### ⏹️ END — nothing else to run
No need to reply."""
TRACKER = re.compile(r"🔢.*🔒|🔒️?\s*SECURITY")


def blocks(text: str) -> tuple[list[str], list[tuple[int, int, list[str]]]]:
    # A block inside a `>` quote is just as copyable, so quotes are unwrapped first.
    lines = [re.sub(r"^\s*(>\s?)+", "", line) for line in text.splitlines()]
    out, i = [], 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if m:
            fence = m.group(2)
            start = i
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                i += 1
            out.append((start, min(i, len(lines) - 1), lines[start + 1:i]))
        i += 1
    return lines, out


def near(lines: list[str], idx: int, step: int) -> str:
    j = idx + step
    while 0 <= j < len(lines):
        if lines[j].strip():
            return lines[j].strip()
        j += step
    return ""


def stop_check(payload: dict) -> NoReturn:
    msg = payload.get("last_assistant_message")
    if msg is None:
        msg = last_message_from_transcript(payload.get("transcript_path"))
    if not msg:
        allow()
    cwd = payload.get("cwd") or os.getcwd()
    root = repo_root(cwd) or os.environ.get("CLAUDE_PROJECT_DIR")
    gates = Gates(root)
    if gates.declined:
        allow()
    lines, blks = blocks(msg)
    reading = set()
    run = []
    for start, end, body in blks:
        label = near(lines, start, -1)
        if "📄 FOR READING" in label:
            reading.update(range(start, end + 1))
            continue
        code = "\n".join(l for l in body if not l.strip().startswith("#"))
        if "▶️ RUN THIS" in label or GIT_CMD.search(code):
            run.append((start, end, body, label))

    problems = []
    for n, line in enumerate(lines):
        if n in reading:
            continue
        for m in BAD_URL.finditer(line):
            problems.append(f"C1: '{m.group(0)}' is a loopback or Docker-bridge URL. Hand over the LAN URL that curl reached.")

    if run:
        first = run[0][0]
        if not any(TRACKER.search(l) for l in lines[:first]):
            problems.append("C5: no gate tracker line above the first ▶️ RUN THIS block.")
        after_last = "\n".join(lines[run[-1][1] + 1:])
        # A reply that asks the user something after the block needs their answer, so
        # "No need to reply" would be false there.
        if not NO_REPLY.search(after_last) and not ASKS.search(after_last):
            problems.append("C7: say 'No need to reply' under the last ▶️ RUN THIS block.")
        for k, (start, end, body, label) in enumerate(run, 1):
            tag = f"block {k}"
            if "▶️ RUN THIS" not in label:
                problems.append(f"C3: {tag} has no '### ▶️ RUN THIS — <what it does>' label directly above it.")
            if len(run) > 1 and not re.search(r"block\s+\d+\s+of\s+\d+", label):
                problems.append(f"C3: {tag}: with several run blocks, each label says 'block N of M'.")
            nonblank = [l.strip() for l in body if l.strip()]
            if not nonblank or not nonblank[0].startswith("# ════════ ▶️ START"):
                problems.append(f"C3: {tag} must start with '# ════════ ▶️ START: <what>'.")
            if not nonblank or not nonblank[-1].startswith("# ════════ ⏹️ END"):
                problems.append(f"C3: {tag} must end with '# ════════ ⏹️ END'.")
            if "⏹️ END" not in near(lines, end, 1):
                problems.append(f"C3: {tag} needs a '### ⏹️ END' line directly below it.")
            body_text = "\n".join(body)
            fence_lang = lines[start].strip().lstrip("`~").strip().lower()
            cmds = simple_commands(body_text, ps=fence_lang in ("powershell", "pwsh", "ps1", "ps"))
            if any(argv and argv[0].lower() in ("cd", "set-location", "sl", "chdir", "pushd", "push-location")
                   for argv in cmds):
                problems.append(f"C4: {tag} contains a cd. Blocks assume the terminal is already in the repo.")
            ops = []
            for argv in cmds:
                ops.extend(classify(argv, root))
            for p in gate_problems(ops, gates, presented=True, text_for_fork=body_text):
                problems.append(f"C2: {tag}: {p}")

    if not problems:
        allow()
    counter = stop_counter(payload)
    if counter > MAX_STOP_BLOCKS:
        emit({"systemMessage": "dev-skills enforcement: this reply still breaks these rules after "
                               f"{MAX_STOP_BLOCKS} fixes and was let through so the session isn't stuck:\n- "
                               + "\n- ".join(problems)})
    shape = SKELETON if any(p.startswith(("C3", "C5", "C7")) for p in problems) else ""
    emit({"decision": "block",
          "reason": "dev-skills enforcement — fix the reply before ending it (see ENFORCEMENT.md):\n- "
                    + "\n- ".join(problems) + shape})


def stop_counter(payload: dict) -> int:
    key = re.sub(r"[^A-Za-z0-9_-]", "", f"{payload.get('session_id', '')}-{payload.get('prompt_id', '')}")[:160]
    try:
        path = os.path.join(state_dir(), "stop-" + key)
        n = int(read(path) or "0") + 1
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(str(n))
        return n
    except (OSError, ValueError):
        return 1


def last_message_from_transcript(path: str | None) -> str | None:
    text = None
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message") or {}
                if msg.get("role") == "assistant":
                    parts = msg.get("content")
                    if isinstance(parts, list):
                        t = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text")
                        if t:
                            text = t
    except (OSError, TypeError):
        return None
    return text


# --- post-ask: D1 -------------------------------------------------------------

def post_ask(payload: dict) -> NoReturn:
    inp = payload.get("tool_input") or {}
    questions = [q.get("question", "") for q in inp.get("questions", []) if isinstance(q, dict)]
    options = {q.get("question", ""): {o.get("label", "") for o in q.get("options", []) if isinstance(o, dict)}
               for q in inp.get("questions", []) if isinstance(q, dict)}
    multi = {q.get("question", ""): bool(q.get("multiSelect")) for q in inp.get("questions", []) if isinstance(q, dict)}
    resp = payload.get("tool_response")
    answers = None
    if isinstance(resp, dict) and isinstance(resp.get("answers"), dict):
        answers = resp["answers"]
    elif isinstance(inp.get("answers"), dict):
        answers = inp["answers"]
    notes = []
    if answers is not None:
        for q in questions:
            a = answers.get(q)
            if a is None or not str(a).strip():
                notes.append(f"'{q}' was NOT answered. Re-ask it and wait. Do not pick a default.")
            elif options.get(q) and str(a).strip() not in options[q] \
                    and not (multi.get(q) and all(part.strip() in options[q] for part in str(a).split(","))):
                notes.append(f"'{q}' was answered in the user's own words: \"{a}\". Respond to that before acting.")
    else:
        blob = json.dumps(resp, ensure_ascii=False) if not isinstance(resp, str) else resp
        for q in questions:
            if q and (q not in blob or re.search(re.escape(q) + r'"?\s*\(No answer provided\)', blob)):
                notes.append(f"'{q}' was NOT answered. Re-ask it and wait. Do not pick a default.")
    if notes:
        emit({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                     "additionalContext": "dev-skills enforcement (D1):\n- " + "\n- ".join(notes)}})
    allow()


# --- main ---------------------------------------------------------------------

RAW = {"text": ""}


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    # Claude Code sends UTF-8. Decode it as such: Windows' default stdin encoding
    # (cp1252) garbles emoji and raises on some bytes (▶️ contains 0x8F).
    RAW["text"] = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(RAW["text"] or "{}")
    except ValueError:
        payload = {}
    mark_active(payload)
    if mode == "pre-tool":
        pre_tool(payload)
    elif mode == "stop":
        if payload.get("stop_hook_active") and stop_counter_peek(payload) > MAX_STOP_BLOCKS:
            allow()
        stop_check(payload)
    elif mode == "post-ask":
        post_ask(payload)
    allow()


def stop_counter_peek(payload: dict) -> int:
    key = re.sub(r"[^A-Za-z0-9_-]", "", f"{payload.get('session_id', '')}-{payload.get('prompt_id', '')}")[:160]
    try:
        return int(read(os.path.join(state_dir(), "stop-" + key)) or "0")
    except (OSError, ValueError):
        return 0


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        # Fail closed where it matters: a git, gh or docker command, or a GitHub
        # MCP write. Everything else goes through, so a bug here can't stop the
        # user editing the gate file to decline enforcement.
        risky = re.search(r'(^|[^A-Za-z])(git|gh|docker)\s|"tool_name":\s*"mcp__[^"]*github', RAW["text"])
        if len(sys.argv) > 1 and sys.argv[1] == "pre-tool" and risky:
            pre_decision("deny", f"the enforcement check itself failed ({type(exc).__name__}: {exc}). "
                                 "Blocked rather than allowed. Report it, or decline enforcement for this session.")
        sys.exit(0)
