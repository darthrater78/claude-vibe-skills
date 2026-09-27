#!/usr/bin/env python3
"""Check that every SHA-pinned action in this repo still resolves to what its
comment claims, and report pins that have a newer release.

Dependabot keeps .github/workflows/ current, but it can't see the templates:
they live in skills/dev-skills/*.md, so a template pin can point at a commit
that never matched its tag (the 2.41.0 setup-gradle bug) or fall releases
behind without anything noticing. check-pins.yml runs this weekly and on any
pull request that touches a pin.

  `# vX.Y.Z` comment  the tag must exist and resolve to exactly the pinned
                      commit (the peeled commit for an annotated tag)
  `# <branch> ...`    no tag to compare against (hassfest has none), so the
                      pinned commit must at least exist on GitHub

A mismatch, a missing tag or commit, or a pin with no comment fails the run.
A newer stable release of the same action is printed as a warning and does
not fail: bumping a pin is a decision, not a breakage.

Needs network access to github.com, so validate.sh doesn't run it.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted((ROOT / ".github" / "workflows").glob("*.yml")) + sorted(
    (ROOT / "skills" / "dev-skills").glob("*.md"))

# Comment lines count too: a commented-out template step is still copied.
PIN = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)(/[\w./-]+)?@([0-9a-f]{40})\s*(?:#\s*(\S+))?")
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, timeout=120)


def tags_of(repo: str) -> dict[str, str] | None:
    """tag name -> commit SHA, peeled through annotated tags. None if unreachable."""
    r = git("ls-remote", "--tags", f"https://github.com/{repo}.git")
    if r.returncode != 0:
        return None
    tags: dict[str, str] = {}
    for line in r.stdout.splitlines():
        sha, ref = line.split("\t")
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            tags[name[:-3]] = sha  # the peeled commit wins over the tag object
        else:
            tags.setdefault(name, sha)
    return tags


def commit_exists(repo: str, sha: str) -> bool:
    """GitHub serves any reachable commit by SHA to a shallow fetch."""
    with tempfile.TemporaryDirectory() as d:
        if git("init", "-q", d).returncode != 0:
            return False
        return git("-C", d, "fetch", "-q", "--depth=1",
                   f"https://github.com/{repo}.git", sha).returncode == 0


def newest(tags: dict[str, str], like: str) -> str | None:
    """Newest stable X.Y.Z tag, written the same way as `like` (v prefix or not)."""
    prefix = "v" if like.startswith("v") else ""
    best = None
    for name in tags:
        m = SEMVER.match(name)
        if m and name.startswith(prefix) and (prefix or not name.startswith("v")):
            key = tuple(map(int, m.groups()))
            if best is None or key > best[0]:
                best = (key, name)
    return best[1] if best else None


def main() -> int:
    pins: dict[tuple[str, str, str | None], list[str]] = {}
    for path in SOURCES:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in PIN.finditer(line):
                key = (m.group(1), m.group(3), m.group(4))
                pins.setdefault(key, []).append(f"{path.relative_to(ROOT)}:{n}")

    failures = warnings = 0
    cache: dict[str, dict[str, str] | None] = {}
    for (repo, sha, label), where in sorted(pins.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "")):
        at = f"{repo}@{sha[:12]} # {label or '(no comment)'} ({where[0]}{f' +{len(where) - 1}' if len(where) > 1 else ''})"

        def fail(why: str) -> None:
            nonlocal failures
            failures += 1
            print(f"  FAIL: {at}: {why}")

        if label is None:
            fail("no version comment, so neither Dependabot nor a reviewer can tell what it is")
            continue
        if repo not in cache:
            cache[repo] = tags_of(repo)
        tags = cache[repo]
        if tags is None:
            fail(f"git ls-remote could not reach github.com/{repo}")
            continue
        if SEMVER.match(label) or label in tags:
            if label not in tags:
                fail(f"tag {label} does not exist in {repo}")
            elif tags[label] != sha:
                fail(f"tag {label} is {tags[label][:12]}, not the pinned commit")
            else:
                latest = newest(tags, label)
                if latest and SEMVER.match(label) and \
                        tuple(map(int, SEMVER.match(latest).groups())) > \
                        tuple(map(int, SEMVER.match(label).groups())):
                    warnings += 1
                    print(f"  WARN: {at}: {latest} is available")
                else:
                    print(f"  OK: {at}")
        elif commit_exists(repo, sha):
            print(f"  OK: {at} (branch pin: commit exists)")
        else:
            fail(f"commit does not exist in {repo}")

    print(f"pin check: {len(pins)} pins, {failures} failure(s), {warnings} with a newer release")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
