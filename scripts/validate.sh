#!/usr/bin/env bash
set -euo pipefail

errors=0

# Extract versions from each source
version_file=$(cat VERSION | tr -d '[:space:]')
skill_frontmatter=$(grep -m1 '^version:' skills/dev-skills/SKILL.md | sed 's/version:[[:space:]]*//' | tr -d '[:space:]')
skill_banner=$(grep -oP 'Dev Skills v\K[0-9]+\.[0-9]+\.[0-9]+' skills/dev-skills/SKILL.md | head -1)
readme_version=$(grep -A0 '## Version' README.md | head -1)
readme_version_code=$(grep -oP '`v\K[0-9]+\.[0-9]+\.[0-9]+' README.md | head -1)

echo "=== Version sources ==="
echo "  VERSION file:        $version_file"
echo "  SKILL.md frontmatter: $skill_frontmatter"
echo "  SKILL.md banner:      $skill_banner"
echo "  README.md:            $readme_version_code"

# Check all versions match
if [ "$version_file" != "$skill_frontmatter" ]; then
  echo "FAIL: VERSION ($version_file) != SKILL.md frontmatter ($skill_frontmatter)"
  errors=$((errors + 1))
fi

if [ "$version_file" != "$skill_banner" ]; then
  echo "FAIL: VERSION ($version_file) != SKILL.md banner ($skill_banner)"
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
for f in skills/dev-skills/SKILL.md skills/dev-skills/SECURITY_REFERENCE.md skills/dev-skills/QUALITY_REFERENCE.md skills/dev-skills/SHELL_REFERENCE.md; do
  if [ -f "$f" ]; then
    echo "  OK: $f"
  else
    echo "  FAIL: $f not found"
    errors=$((errors + 1))
  fi
done

# Check .skill archive if present
if [ -f skills/dev-skills.skill ]; then
  echo ""
  echo "=== Skill archive ==="
  if unzip -t skills/dev-skills.skill > /dev/null 2>&1; then
    echo "  OK: dev-skills.skill is a valid zip"
    contents=$(unzip -l skills/dev-skills.skill | grep -c '\.md$' || true)
    echo "  Contains $contents .md files"
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
