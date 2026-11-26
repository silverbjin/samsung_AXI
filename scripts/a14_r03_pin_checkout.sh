#!/usr/bin/env bash
# Immutable checkout helper. New directory only; never merge/reset an existing workspace.
a14_pin_checkout() {
  local url="$1" pin="$2" branch="$3" target="$4"
  [[ "$pin" =~ ^[0-9a-f]{40}$ ]] || return 2
  [[ -d "$target" && ! -e "$target/.git" && -z "$(ls -A -- "$target")" ]] || return 2
  git init -q "$target" || return
  git -C "$target" remote add origin "$url" || return
  git -C "$target" fetch --no-tags --depth=1 origin "$pin" || return
  git -C "$target" switch -q -c "$branch" "$pin" || return
  [[ "$(git -C "$target" rev-parse HEAD)" == "$pin" ]] || return 2
  [[ "$(git -C "$target" branch --show-current)" == "$branch" ]] || return 2
  [[ -z "$(git -C "$target" status --porcelain --untracked-files=no)" ]] || return 2
}
