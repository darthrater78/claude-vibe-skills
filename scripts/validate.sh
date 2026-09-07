#!/usr/bin/env bash
set -euo pipefail

errors=0

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
for f in skills/dev-skills/SKILL.md skills/dev-skills/GATE_REFERENCE.md skills/dev-skills/SECURITY_REFERENCE.md skills/dev-skills/QUALITY_REFERENCE.md skills/dev-skills/SHELL_REFERENCE.md; do
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

# Check .skill archive if present
if [ -f skills/dev-skills.skill ]; then
  echo ""
  echo "=== Skill archive ==="
  if unzip -t skills/dev-skills.skill > /dev/null 2>&1; then
    echo "  OK: dev-skills.skill is a valid zip"
    # Every required file must actually be in the bundle, and the bundled
    # SKILL.md must carry the current version — a stale archive ships old rules.
    for f in SKILL.md GATE_REFERENCE.md SECURITY_REFERENCE.md QUALITY_REFERENCE.md SHELL_REFERENCE.md; do
      if unzip -l skills/dev-skills.skill | grep -q "  $f\$"; then
        echo "  OK: bundled $f"
      else
        echo "  FAIL: $f missing from dev-skills.skill (rebuild the bundle)"
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
