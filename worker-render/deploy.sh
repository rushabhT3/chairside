#!/usr/bin/env bash
# Deploys the render worker with the YouCam key read from ../.env, so the key never reaches a shell history.
# Pass --temporary to deploy to a throwaway Cloudflare account instead of the logged-in one.
set -euo pipefail

cd "$(dirname "$0")"
KEY="$(sed -n 's/^PERFECTCORP_API_KEY=//p' ../.env)"
if [ -z "$KEY" ]; then
  echo "PERFECTCORP_API_KEY is empty in ../.env" >&2
  exit 1
fi

npx wrangler deploy "$@" --var "PERFECTCORP_API_KEY:$KEY" 2>&1 | sed "s/$KEY/<key>/g"
