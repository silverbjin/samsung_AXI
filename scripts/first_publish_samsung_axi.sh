#!/usr/bin/env bash
# One-time publishing helper. It never forces or overwrites a populated remote.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
URL='https://github.com/silverbjin/samsung_AXI.git'
[[ -d .git ]] || { echo 'BLOCKED_NOT_A_GIT_WORKTREE'; exit 2; }
[[ "$(git branch --show-current)" == main ]] || { echo 'BLOCKED_LOCAL_MAIN_REQUIRED'; exit 2; }
[[ -z "$(git status --porcelain)" ]] || { echo 'BLOCKED_UNCOMMITTED_CHANGES'; exit 2; }
if git remote get-url origin >/dev/null 2>&1; then
  [[ "$(git remote get-url origin)" == "$URL" ]] || { echo 'BLOCKED_ORIGIN_POINTS_ELSEWHERE'; exit 2; }
else
  git remote add origin "$URL"
fi
REMOTE_SHA="$(git ls-remote origin refs/heads/main | awk '{print $1}')"
LOCAL_SHA="$(git rev-parse HEAD)"
if [[ -n "$REMOTE_SHA" && "$REMOTE_SHA" != "$LOCAL_SHA" ]]; then
  echo "BLOCKED_REMOTE_MAIN_ALREADY_POPULATED remote=$REMOTE_SHA local=$LOCAL_SHA"
  echo 'Use a feature branch / PR. Do not force-push.'
  exit 2
fi
if [[ -z "$REMOTE_SHA" ]]; then
  git push -u origin main
fi
REMOTE_SHA="$(git ls-remote origin refs/heads/main | awk '{print $1}')"
[[ "$REMOTE_SHA" == "$LOCAL_SHA" ]] || { echo 'BLOCKED_REMOTE_HEAD_MISMATCH'; exit 1; }
echo "SAMSUNG_AXI_INITIAL_SOURCE_UPLOAD_VERIFIED_SHA=$REMOTE_SHA"
echo 'Next: check https://github.com/silverbjin/samsung_AXI/actions'
