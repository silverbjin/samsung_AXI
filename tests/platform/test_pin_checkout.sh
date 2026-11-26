#!/usr/bin/env bash
set -Eeuo pipefail
source scripts/smartdish_platform_bootstrap.sh
d="$(mktemp -d)";trap 'rm -rf -- "$d"' EXIT
git init -q "$d/origin"
git -C "$d/origin" config user.name fixture
git -C "$d/origin" config user.email fixture@example.invalid
echo original > "$d/origin/file";git -C "$d/origin" add file;git -C "$d/origin" commit -qm original
pin="$(git -C "$d/origin" rev-parse HEAD)"
echo newer > "$d/origin/file";git -C "$d/origin" commit -qam newer
a="$(smartdish_new_workspace "$pin" A "$d")";b="$(smartdish_new_workspace "$pin" B "$d")"
[[ "$a" != "$b" ]]
smartdish_pin_checkout "$d/origin" "$pin" fixture "$a"
smartdish_pin_checkout "$d/origin" "$pin" fixture "$b"
[[ "$(cat "$a/file")" == original && "$(cat "$b/file")" == original ]]
echo preserve > "$a/local"
if smartdish_pin_checkout "$d/origin" "$pin" fixture "$a";then exit 2;fi
[[ "$(cat "$a/local")" == preserve ]]
if smartdish_pin_checkout "$d/origin" bad fixture "$b";then exit 2;fi
echo PLATFORM_PIN_CHECKOUT_PASS
