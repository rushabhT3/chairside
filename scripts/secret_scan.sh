#!/usr/bin/env sh
# Same patterns as .github/workflows/ci.yml; run before every commit.
set -eu
cd "$(dirname "$0")/.."
if git grep -nE 'pdf_live_[A-Za-z0-9]{8,}|serpapi[_-]?key\s*[:=]\s*["'"'"']?[A-Za-z0-9]{20,}|client_secret\s*[:=]\s*["'"'"']?[A-Za-z0-9_-]{16,}' -- ':!.github/workflows/ci.yml' ':!scripts/secret_scan.sh'; then
  echo "secret pattern found; refusing" >&2
  exit 1
fi
echo "secret scan clean"
