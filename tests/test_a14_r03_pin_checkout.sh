#!/usr/bin/env bash
set -Eeuo pipefail
root="$(mktemp -d)"
trap 'rm -rf -- "$root"' EXIT
source scripts/a14_r03_bootstrap.sh
git init -q -b main "$root/remote"
git -C "$root/remote" -c user.name=Fixture -c user.email=fixture@example.invalid commit --allow-empty -qm first
pin="$(git -C "$root/remote" rev-parse HEAD)"
git -C "$root/remote" -c user.name=Fixture -c user.email=fixture@example.invalid commit --allow-empty -qm next
head="$(git -C "$root/remote" rev-parse HEAD)"
[[ "$pin" != "$head" ]]
mkdir "$root/owner"
a14_pin_checkout "file://$root/remote" "$pin" feat/smartdish-a14-physics-evidence "$root/owner"
[[ "$(git -C "$root/owner" rev-parse HEAD)" == "$pin" ]]
[[ "$(git -C "$root/remote" rev-parse HEAD)" == "$head" ]]
echo untouched > "$root/owner/keep.txt"
if a14_pin_checkout "file://$root/remote" "$head" feat/smartdish-a14-physics-evidence "$root/owner"; then
  echo R03_EXISTING_DIRECTORY_MUST_BE_REJECTED; exit 2
fi
[[ "$(cat "$root/owner/keep.txt")" == untouched ]]
echo R03_PIN_CHECKOUT_FIXTURE_PASS
