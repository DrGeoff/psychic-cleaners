#!/usr/bin/env bash
# Cut a release: bump the CalVer version, tag it, and push.
#
# Version scheme is YYYYMMDD.N (matching today's date, N starting at 1 and
# incrementing for same-day re-releases). The pushed tag is what triggers
# .github/workflows/publish.yml to build and upload to PyPI -- a plain tag
# push, not a GitHub Release, because the release-published webhook proved
# unreliable in practice (see the 20260716.1 release notes).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "error: working tree is not clean" >&2
    exit 1
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" != "main" ]]; then
    echo "error: release from main, not '$branch'" >&2
    exit 1
fi

git fetch origin main
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
    echo "error: local main is not up to date with origin/main" >&2
    exit 1
fi

echo "Running checks (mirrors CI)..."
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=psychic_cleaners.core --cov-fail-under=90 \
    --override-ini="addopts=--cov-report=term-missing"

today="$(date +%Y%m%d)"
last_n="$(git tag -l "v${today}-*" | sed -E "s/^v${today}-//" | sort -n | tail -1)"
n=$(( ${last_n:-0} + 1 ))
version="${today}.${n}"
tag="v${today}-${n}"

echo "Releasing ${version} (tag ${tag})..."
uv version "$version"
git add pyproject.toml uv.lock
git commit -m "build: release ${version}"
git tag -a "$tag" -m "Release ${version}"
git push origin main "$tag"

echo "Pushed ${tag} -- publish.yml will build and publish ${version} to PyPI."
echo "Creating GitHub Release for changelog visibility (does not gate the PyPI publish)..."
gh release create "$tag" --title "$version" --generate-notes
