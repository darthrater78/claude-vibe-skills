#!/usr/bin/env bash
set -euo pipefail

# Rebuild skills/dev-skills.skill from skills/dev-skills/*.md.
#
# The bundle is what people install, and scripts/validate.sh compares it against
# the source byte for byte — so it must be rebuilt whenever any of those files
# change, or validation fails with "rebuild the bundle" no matter how correct
# the source is.
#
# Entries are stored at the archive root with LF endings, which is what the
# installers and validate.sh expect. .gitattributes already keeps checkouts LF;
# the newline is normalized here anyway rather than trusting the checkout.

cd "$(dirname "$0")/.."

src="skills/dev-skills"
out="skills/dev-skills.skill"
files=(SKILL.md GATE_REFERENCE.md SECURITY_REFERENCE.md QUALITY_REFERENCE.md SHELL_REFERENCE.md WORKFLOW_REFERENCE.md)

for f in "${files[@]}"; do
  if [ ! -f "$src/$f" ]; then
    echo "missing source file: $src/$f" >&2
    exit 1
  fi
done

# Pick a real Python 3. `python` is checked before `python3` on purpose: on
# Windows, `python3` often resolves to the Microsoft Store stub, which is on
# PATH but is not an interpreter.
python=""
for cand in python python3 py; do
  if command -v "$cand" > /dev/null 2>&1 &&
     "$cand" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' > /dev/null 2>&1; then
    python="$cand"
    break
  fi
done

if [ -z "$python" ]; then
  echo "no Python 3 interpreter found — needed to build the bundle" >&2
  exit 1
fi

"$python" - "$out" "$src" "${files[@]}" <<'PY'
import sys, zipfile

out, src, *names = sys.argv[1:]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in names:
        with open(f"{src}/{name}", "rb") as fh:
            z.writestr(name, fh.read().replace(b"\r\n", b"\n"))
PY

echo "built $out"