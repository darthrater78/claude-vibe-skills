#!/usr/bin/env python3
"""Run the line-provable workflow rules (enforce.py B8) over this repo's own
workflows and every template workflow in skills/dev-skills/WORKFLOW_*.md.

validate.sh calls this, so CI re-checks the reference repo and its templates on
every push instead of only when Claude edits a workflow. Any deny or ask
finding fails the run.

`--extract DIR` writes each full template workflow to DIR as a .yml file
instead, for lint-workflows.yml to run actionlint over: the templates live in
Markdown because that's what Claude loads, but actionlint only reads YAML.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "dev-skills"
sys.path.insert(0, str(SKILL / "checks"))

from enforce import workflow_problems  # noqa: E402

YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.S)


def targets() -> list[tuple[str, str]]:
    """(label, text) for every repo workflow and every full template workflow."""
    found = [(str(p.relative_to(ROOT)), p.read_text(encoding="utf-8"))
             for p in sorted((ROOT / ".github" / "workflows").glob("*.yml"))]
    for doc in sorted(SKILL.glob("WORKFLOW_*.md")):
        if doc.name == "WORKFLOW_REFERENCE.md":
            continue
        blocks = YAML_BLOCK.findall(doc.read_text(encoding="utf-8"))
        # Only complete workflows: fragments (a single step, a dependabot.yml)
        # have no jobs: and aren't workflows on their own.
        found.extend((f"{doc.name} block {i + 1}", b)
                     for i, b in enumerate(blocks) if re.search(r"^jobs:", b, re.M))
    return found


def snippets() -> list[tuple[str, str]]:
    """(label, text) for every YAML fragment in every WORKFLOW_*.md, including
    WORKFLOW_REFERENCE.md. Only the `${{ }}`-in-run: rule applies to these:
    Claude copies snippets into workflows, and the hook would then deny them.
    A fragment showing the wrong way on purpose opens with `# bad`."""
    found = []
    for doc in sorted(SKILL.glob("WORKFLOW_*.md")):
        for i, b in enumerate(YAML_BLOCK.findall(doc.read_text(encoding="utf-8"))):
            if not re.search(r"^jobs:", b, re.M) and not re.search(r"^\s*# bad\b", b, re.M):
                found.append((f"{doc.name} snippet {i + 1}", b))
    return found


def extract(out: Path) -> int:
    """Write every full template workflow to out/<doc>-<n>.yml."""
    out.mkdir(parents=True, exist_ok=True)
    templates = [(label, text) for label, text in targets() if " block " in label]
    for label, text in templates:
        doc, _, n = label.partition(" block ")
        (out / f"{doc.removesuffix('.md').lower()}-{n}.yml").write_text(text, encoding="utf-8")
    print(f"extracted {len(templates)} template workflows to {out}")
    return 0


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--extract":
        return extract(Path(sys.argv[2]))
    failures = 0
    checked = targets()
    for label, text in checked:
        deny, ask = workflow_problems(text)
        for problem in deny + ask:
            print(f"  FAIL: {label}: {problem}")
            failures += 1
    fragments = snippets()
    for label, text in fragments:
        for problem in workflow_problems(text)[0]:
            if "inside a run: script" in problem:
                print(f"  FAIL: {label}: {problem}")
                failures += 1
    print(f"workflow audit: {len(checked)} workflows, {len(fragments)} snippets, "
          f"{failures} finding(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
