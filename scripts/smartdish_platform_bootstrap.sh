#!/usr/bin/env bash
# Shared exact-pin checkout. Source from a verified commit or download this
# standalone file from the approved immutable SHA. No moving-HEAD fallback.
smartdish_pin_checkout() {
  local url="$1" pin="$2" branch="$3" target="$4"
  [[ "$pin" =~ ^[0-9a-f]{40}$ ]] || return 2
  git check-ref-format --branch "$branch" >/dev/null || return 2
  [[ -d "$target" && ! -L "$target" && -z "$(ls -A -- "$target")" ]] || return 2
  git init -q "$target" || return
  git -C "$target" remote add origin "$url" || return
  timeout --signal=INT --kill-after=5s 120s git -C "$target" fetch --no-tags --depth=1 origin "$pin" || return
  git -C "$target" switch -q -c "$branch" "$pin" || return
  [[ "$(git -C "$target" rev-parse HEAD)" == "$pin" ]] || return 2
  [[ "$(git -C "$target" remote get-url origin)" == "$url" ]] || return 2
  [[ "$(git -C "$target" branch --show-current)" == "$branch" ]] || return 2
  [[ -z "$(git -C "$target" status --porcelain --untracked-files=no)" ]] || return 2
}
smartdish_new_workspace() {
  local pin="$1" role="$2" root="$3"
  [[ "$pin" =~ ^[0-9a-f]{40}$ && "$role" =~ ^[A-Z0-9_]+$ && -d "$root" ]] || return 2
  root="$(realpath "$root")" || return
  case "$root" in /mnt/*) return 2;; esac
  mktemp -d "$root/samsung_AXI_${role}_${pin:0:7}_XXXXXX"
}
