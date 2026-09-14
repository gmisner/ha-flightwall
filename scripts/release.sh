#!/usr/bin/env bash
# Tag the current commit and create a GitHub release from CHANGELOG.md.
# Usage: scripts/release.sh [version]
# Version defaults to custom_components/flightwall/manifest.json.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  VERSION="$(python3 -c "import json; print(json.load(open('custom_components/flightwall/manifest.json'))['version'])")"
fi
VERSION="${VERSION#v}"
TAG="v${VERSION}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Commit or stash first." >&2
  exit 1
fi

NOTES="$(python3 - "$VERSION" <<'PY'
import sys
from pathlib import Path

version = sys.argv[1]
text = Path("CHANGELOG.md").read_text(encoding="utf-8")
needle = f"## {version}"
start = text.find(needle)
if start < 0:
    raise SystemExit(f"No CHANGELOG.md section for {version}")
start = text.find("\n", start) + 1
end = text.find("\n## ", start)
body = text[start:] if end < 0 else text[start:end]
print(body.strip())
PY
)"

if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  git tag -a "$TAG" -m "$TAG"
fi

git push origin HEAD
git push origin "$TAG"

gh api --method POST "repos/gmisner/ha-flightwall/releases" \
  -f tag_name="$TAG" \
  -f name="$TAG" \
  -f target_commitish="$(git rev-parse HEAD)" \
  -f body="$NOTES"
