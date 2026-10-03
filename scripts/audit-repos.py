#!/usr/bin/env python3
"""Audit the workflows of every repo the owner has, weekly, without a session.

Gate 3 audits a repo's workflows only when a Claude session opens that repo,
so a repo nobody is working in never meets a rule added after its last
session. audit-repos.yml runs this weekly: it reads each repo's
.github/workflows/ on its default branch, applies the same line-provable rules
enforce.py B8 applies to edits (workflow_findings), and keeps one summary issue
in this repo up to date. Nothing is written to the audited repos.

Only the mechanical rules run here: unpinned actions, `${{ }}` inside run:,
checkout keeping its credential, no permissions: block, no timeout, ./gradlew
before wrapper validation, each labeled with WORKFLOW_REFERENCE.md's severity
scale. The judgment rules (release gates, Docker scans, Dependabot, concurrency,
docs-only CI, secrets on disk) stay Gate 3's. The issue is a work queue: one
checklist per repo, worst repo first, worst finding first.

Environment:
  GITHUB_TOKEN        this repo's token: opens/updates the issue, and reads
                      public repos (authenticated, so the rate limit is 1000/h)
  AUDIT_TOKEN         optional, a fine-grained token with read-only Contents
                      and Metadata on the owner's repos; when set, private
                      repos are audited too. It is only ever sent to
                      api.github.com and never needs write access
  GITHUB_REPOSITORY   owner/repo that holds the summary issue
  GITHUB_STEP_SUMMARY where the report is also written, if set

`--dry-run` prints the report and touches no issue.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "dev-skills" / "checks"))

from enforce import workflow_findings  # noqa: E402

API = "https://api.github.com"
TITLE = "Weekly workflow audit"
SEVERITIES = ("Critical", "High", "Medium", "Low")
BOT = "github-actions[bot]"


class ApiError(Exception):
    pass


class ApiOnlyRedirects(urllib.request.HTTPRedirectHandler):
    """urllib keeps the Authorization header across a redirect, so a redirect off
    api.github.com would hand the token to another host. Refuse it instead."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        if urllib.parse.urlsplit(newurl).netloc != "api.github.com":
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(ApiOnlyRedirects)


def api(method: str, path: str, token: str, body: dict | None = None) -> tuple[object, str | None]:
    """(parsed JSON, next-page URL). `path` is relative to api.github.com, or a
    full api.github.com URL from a Link header."""
    url = path if path.startswith(API + "/") else API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "claude-vibe-skills-audit",
    })
    try:
        with OPENER.open(req, timeout=30) as resp:
            raw = resp.read()
            link = resp.headers.get("Link") or ""
    except urllib.error.HTTPError as e:
        raise ApiError(f"{method} {url.removeprefix(API)}: HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"{method} {url.removeprefix(API)}: {e.reason}") from None
    m = re.search(r'<(https://api\.github\.com/[^>]+)>;\s*rel="next"', link)
    return (json.loads(raw) if raw else None), (m.group(1) if m else None)


def paged(path: str, token: str) -> list:
    out: list = []
    nxt: str | None = path
    while nxt:
        page, nxt = api("GET", nxt, token)
        out.extend(page if isinstance(page, list) else [])
    return out


def list_repos(owner: str, read_token: str, private: bool) -> list[dict]:
    if private:
        repos = paged("/user/repos?affiliation=owner&per_page=100", read_token)
    else:
        repos = paged(f"/users/{urllib.parse.quote(owner)}/repos?type=owner&per_page=100", read_token)
    return sorted((r for r in repos if not r.get("archived") and not r.get("disabled")),
                  key=lambda r: r["full_name"].lower())


def workflow_files(repo: dict, token: str) -> list[tuple[str, str]]:
    """(file name, text) for each workflow on the default branch."""
    full, ref = repo["full_name"], urllib.parse.quote(repo["default_branch"])
    try:
        listing, _ = api("GET", f"/repos/{full}/contents/.github/workflows?ref={ref}", token)
    except ApiError as e:
        if "HTTP 404" in str(e):
            return []
        raise
    out = []
    for entry in listing if isinstance(listing, list) else []:
        name = entry.get("name", "")
        if entry.get("type") != "file" or not name.endswith((".yml", ".yaml")):
            continue
        blob, _ = api("GET", f"/repos/{full}/contents/.github/workflows/{urllib.parse.quote(name)}?ref={ref}", token)
        if not isinstance(blob, dict) or blob.get("encoding") != "base64":
            # Over 1MB the contents API returns no content: an empty file would read as clean.
            raise ApiError(f"{name}: the contents API returned no file content")
        out.append((name, base64.b64decode(blob.get("content", "")).decode("utf-8", "replace")))
    return out


def cell(text: str) -> str:
    """Workflow text is data from another repo: keep it from breaking the table,
    mentioning anyone, or running long."""
    text = " ".join(text.split()).replace("|", "\\|").replace("@", "&#64;").replace("<", "&lt;")
    text = text.replace("[", "\\[").replace("!", "&#33;")
    return text if len(text) <= 180 else text[:177] + "..."


def audit(repos: list[dict], token: str) -> tuple[list[tuple[str, str, str, str]], list[str], int]:
    """(findings as (repo, file, severity, text), repos that couldn't be read, files audited)."""
    findings, unread, files = [], [], 0
    for repo in repos:
        label = repo["full_name"] + (" (fork)" if repo.get("fork") else "")
        try:
            wfs = workflow_files(repo, token)
        except ApiError as e:
            unread.append(f"{label}: {e}")
            continue
        for name, text in wfs:
            files += 1
            findings += [(label, name, sev, p) for sev, _, p in workflow_findings(text)]
    return findings, unread, files


def counts(findings: list) -> str:
    n = [sum(f[2] == s for f in findings) for s in SEVERITIES]
    return ", ".join(f"{c} {s}" for c, s in zip(n, SEVERITIES) if c)


def checklist(findings: list) -> list[str]:
    """One checklist per repo, the repo with the most severe findings first (by
    Critical count, then High, ...), and within a repo the most severe first."""
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    repos: dict[str, list] = {}
    for f in findings:
        repos.setdefault(f[0], []).append(f)
    order = sorted(repos, key=lambda r: ([-sum(f[2] == s for f in repos[r]) for s in SEVERITIES], r.lower()))
    out: list[str] = []
    for r in order:
        out += [f"### {cell(r)} ({counts(repos[r])})", ""]
        out += [f"- [ ] **{s}** · {cell(f)}: {cell(t)}"
                for _, f, s, t in sorted(repos[r], key=lambda f: (rank[f[2]], f[1], f[3]))]
        out.append("")
    return out[:-1]


def report(findings: list, unread: list[str], repos: int, files: int, private: bool) -> str:
    scope = "public and private" if private else "public only (set AUDIT_TOKEN to include private repos)"
    lines = [f"Audited {files} workflow files in {repos} repos ({scope}), on each repo's default branch.", ""]
    if findings:
        lines += [f"**{len(findings)} findings** in {len({f[0] for f in findings})} repos, "
                  f"{counts(findings)}. Work down the list: fix each repo in a session there "
                  "(Gate 3 re-audits every workflow), and this issue updates on the next run.", ""]
        lines += checklist(findings)
    else:
        lines.append("**No findings.**")
    if unread:
        lines += ["", "**Not audited** (couldn't read):", ""] + [f"- {cell(u)}" for u in unread]
    lines += ["", "Line-provable rules only (enforce.py B8). The workflow checklist's judgment rules "
              "(release gates, Docker scans, Dependabot, concurrency, docs-only CI, secrets written to "
              "disk) still run at each repo's Gate 3."]
    return "\n".join(lines) + "\n"


def sync_issue(repo: str, token: str, body: str, clean: bool) -> str:
    issues = paged(f"/repos/{repo}/issues?state=open&creator={urllib.parse.quote(BOT)}&per_page=100", token)
    mine = next((i for i in issues if i.get("title") == TITLE and "pull_request" not in i), None)
    if mine and clean:
        api("POST", f"/repos/{repo}/issues/{mine['number']}/comments", token, {"body": body})
        api("PATCH", f"/repos/{repo}/issues/{mine['number']}", token, {"state": "closed", "body": body})
        return f"closed #{mine['number']}: no findings"
    if mine:
        api("PATCH", f"/repos/{repo}/issues/{mine['number']}", token, {"body": body})
        return f"updated #{mine['number']}"
    if clean:
        return "no findings, no open issue"
    made, _ = api("POST", f"/repos/{repo}/issues", token, {"title": TITLE, "body": body})
    return f"opened #{made['number']}"


def main() -> int:
    dry = "--dry-run" in sys.argv[1:]
    token = os.environ.get("GITHUB_TOKEN", "")
    read_token = os.environ.get("AUDIT_TOKEN", "") or token
    here = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in here:
        print("GITHUB_TOKEN and GITHUB_REPOSITORY (owner/repo) are required", file=sys.stderr)
        return 2
    private = bool(os.environ.get("AUDIT_TOKEN"))
    try:
        repos = list_repos(here.split("/")[0], read_token, private)
        findings, unread, files = audit(repos, read_token)
        body = report(findings, unread, len(repos), files, private)
        print(body)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(f"## {TITLE}\n\n{body}")
        if not dry:
            print(sync_issue(here, token, body, clean=not findings and not unread))
    except ApiError as e:
        # A failed listing or issue write fails the run, so the owner gets
        # GitHub's failure email. Findings never do: the issue is the signal.
        print(f"audit could not finish: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
