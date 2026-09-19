#!/usr/bin/env bash
set -euo pipefail

errors=0

# The skill's files, in load order: the always-on tier first, then the
# on-demand references. build-skill.sh bundles exactly this list — keep the
# two in step.
files=(SKILL.md SESSION_START.md GATE_REFERENCE.md SHIP_REFERENCE.md AUTO_MODE.md SECURITY_REFERENCE.md QUALITY_REFERENCE.md SHELL_REFERENCE.md WORKFLOW_REFERENCE.md WORKFLOW_DOCKER.md WORKFLOW_WINDOWS.md WORKFLOW_LINUX.md WORKFLOW_HOMEASSISTANT.md WORKFLOW_SCRIPTS.md WORKFLOW_ANDROID.md WORKFLOW_PYTHON.md WORKFLOW_NODEJS.md SECURITY_WINDOWS.md SECURITY_LINUX.md SECURITY_ANDROID.md QUALITY_ANDROID.md)

# Extract versions from each source
version_file=$(cat VERSION | tr -d '[:space:]')
skill_frontmatter=$(grep -m1 '^version:' skills/dev-skills/SKILL.md | sed 's/version:[[:space:]]*//' | tr -d '[:space:]')
skill_banner=$(grep -rhoP 'Dev Skills v\K[0-9]+\.[0-9]+\.[0-9]+' skills/dev-skills/*.md | head -1)
readme_version=$(grep -A0 '## Version' README.md | head -1)
readme_version_code=$(grep -oP '`v\K[0-9]+\.[0-9]+\.[0-9]+' README.md | head -1)

echo "=== Version sources ==="
echo "  VERSION file:        $version_file"
echo "  SKILL.md frontmatter: $skill_frontmatter"
echo "  Session banner:       $skill_banner"
echo "  README.md:            $readme_version_code"

# Check all versions match
if [ "$version_file" != "$skill_frontmatter" ]; then
  echo "FAIL: VERSION ($version_file) != SKILL.md frontmatter ($skill_frontmatter)"
  errors=$((errors + 1))
fi

if [ "$version_file" != "$skill_banner" ]; then
  echo "FAIL: VERSION ($version_file) != session banner ($skill_banner)"
  errors=$((errors + 1))
fi

if [ "$version_file" != "$readme_version_code" ]; then
  echo "FAIL: VERSION ($version_file) != README.md ($readme_version_code)"
  errors=$((errors + 1))
fi

# Check CHANGELOG has an entry for current version
if [ -f CHANGELOG.md ]; then
  if ! grep -q "## \[${version_file}\]" CHANGELOG.md && ! grep -q "## ${version_file}" CHANGELOG.md; then
    echo "FAIL: CHANGELOG.md has no entry for version $version_file"
    errors=$((errors + 1))
  fi
fi

# Check required skill files exist
echo ""
echo "=== Required files ==="
for name in "${files[@]}"; do
  f="skills/dev-skills/$name"
  if [ -f "$f" ]; then
    echo "  OK: $f"
  else
    echo "  FAIL: $f not found"
    errors=$((errors + 1))
  fi
done

# Check the README size table matches reality.
# SKILL.md is loaded every turn, so an understated figure hides a real per-request
# cost. Tolerance is 2KB; update the README when a file legitimately grows.
echo ""
echo "=== README size table ==="
for f in skills/dev-skills/*.md; do
  base=$(basename "$f")
  claimed=$(grep -oP '^\| `'"$base"'` \| ~\K[0-9]+' README.md | head -1 || true)
  if [ -z "$claimed" ]; then
    echo "  FAIL: $base has no size row in the README table"
    errors=$((errors + 1))
    continue
  fi
  actual=$(( ( $(wc -c < "$f") + 512 ) / 1024 ))
  diff=$(( claimed - actual )); [ $diff -lt 0 ] && diff=$(( -diff ))
  if [ $diff -gt 2 ]; then
    echo "  FAIL: $base README says ~${claimed}KB, actual ${actual}KB"
    errors=$((errors + 1))
  else
    echo "  OK: $base ~${claimed}KB (actual ${actual}KB)"
  fi
done

# Per-file size ceilings.
#
# SKILL.md is billed on every request of every session that loads the skill, so
# every KB here is a recurring cost, not a one-time one. The reference files are
# each read IN FULL when they load, so a file that grows back into a monolith
# charges the whole file for the one section that was actually needed — which is
# what the 2.27.0 split was undoing.
#
# A ceiling is not a cap on what the skill may say. It is a prompt to put new
# content where it belongs: extract a section that has its own trigger, or raise
# the number here in the same commit as the growth that needs it, on the record.
# What it stops is the silent 2KB-per-release drift that undid the 2.14.0
# extraction over ten releases without anyone deciding to.
echo ""
echo "=== Size ceilings ==="
ceiling_for() {
  case "$1" in
    # Billed every request. Deliberately the tightest number here.
    SKILL.md) echo 64 ;;
    # Still carries the best-practices and Dependabot sections; it is the next
    # extraction candidate, and this number comes down when they move.
    WORKFLOW_REFERENCE.md) echo 44 ;;
    # Every other reference file: read in full, one purpose each.
    *) echo 32 ;;
  esac
}
for f in skills/dev-skills/*.md; do
  base=$(basename "$f")
  ceiling=$(ceiling_for "$base")
  actual=$(( ( $(wc -c < "$f") + 512 ) / 1024 ))
  if [ "$actual" -gt "$ceiling" ]; then
    echo "  FAIL: $base is ${actual}KB, over its ${ceiling}KB ceiling"
    echo "        Extract a section that has its own load trigger, or raise the"
    echo "        ceiling in scripts/validate.sh in this same commit."
    errors=$((errors + 1))
  else
    echo "  OK: $base ${actual}KB / ${ceiling}KB"
  fi
done

# Check .skill archive if present
if [ -f skills/dev-skills.skill ]; then
  echo ""
  echo "=== Skill archive ==="
  if unzip -t skills/dev-skills.skill > /dev/null 2>&1; then
    echo "  OK: dev-skills.skill is a valid zip"
    # Every required file must actually be in the bundle, and the bundled
    # SKILL.md must carry the current version — a stale archive ships old rules.
    for f in "${files[@]}"; do
      if unzip -l skills/dev-skills.skill | grep -q "  $f\$"; then
        echo "  OK: bundled $f"
      else
        echo "  FAIL: $f missing from dev-skills.skill (rebuild the bundle)"
        errors=$((errors + 1))
      fi
    done
    # The bundle must match the source, not merely contain the right filenames —
    # a stale archive ships old rules under a current version number.
    for f in "${files[@]}"; do
      if ! unzip -p skills/dev-skills.skill "$f" 2>/dev/null | diff -q - "skills/dev-skills/$f" > /dev/null 2>&1; then
        # Tell a stale bundle apart from a CRLF checkout. The bundle always holds
        # LF and .gitattributes keeps checkouts LF, but an older clone predating
        # it still has CRLF — and "rebuild the bundle" sends that person chasing
        # the wrong problem, however freshly they just rebuilt it.
        if unzip -p skills/dev-skills.skill "$f" 2>/dev/null | tr -d '\r' \
             | diff -q - <(tr -d '\r' < "skills/dev-skills/$f") > /dev/null 2>&1; then
          echo "  FAIL: $f matches the bundle except for line endings — this is a CRLF checkout."
          echo "        Fix: git add --renormalize . && git checkout -- ."
          echo "        WARNING: 'git checkout -- .' discards uncommitted changes."
          echo "        Commit or stash first."
        else
          echo "  FAIL: bundled $f differs from skills/dev-skills/$f (rebuild the bundle)"
        fi
        errors=$((errors + 1))
      fi
    done

    bundled_version=$(unzip -p skills/dev-skills.skill SKILL.md 2>/dev/null | grep -m1 '^version:' | sed 's/version:[[:space:]]*//' | tr -d '[:space:]')
    if [ "$bundled_version" != "$version_file" ]; then
      echo "  FAIL: bundled SKILL.md is v${bundled_version:-none}, VERSION is $version_file (rebuild the bundle)"
      errors=$((errors + 1))
    else
      echo "  OK: bundle version $bundled_version"
    fi
  else
    echo "  FAIL: dev-skills.skill is not a valid zip"
    errors=$((errors + 1))
  fi
fi

echo ""
if [ $errors -eq 0 ]; then
  echo "All checks passed."
else
  echo "FAILED: $errors error(s) found."
  exit 1
fi
