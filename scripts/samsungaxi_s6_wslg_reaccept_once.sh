#!/usr/bin/env bash
# S6 WSLg GUI/Qt safe WSL2 L3 acceptance launcher. No hidden Goal.
set -Eeuo pipefail
SOURCE_SHA='9d402a991d1ee0a1c46027abe91a55266b69d9bd'
REPO='silverbjin/samsung_AXI'
WRAPPER='scripts/samsungaxi_wsl2_gui_acceptance_once.sh'
PROBE='scripts/s6_wslg_gl_probe.py'
if [[ $# == 1 && "$1" == '--self-test' ]]; then
  [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
  [[ "$WRAPPER" == 'scripts/samsungaxi_wsl2_gui_acceptance_once.sh' ]]
  echo "S6_WSLG_REACCEPT_SELF_TEST_PASS_NO_GOAL SOURCE_SHA=$SOURCE_SHA"
  exit 0
fi
DIAG=0
if [[ $# == 1 && "$1" == '--diagnose-only' ]]; then
  DIAG=1
elif (( $# != 0 )); then
  echo S6_WSLG_BLOCKED_INVALID_ARGUMENTS_NO_GOAL >&2; exit 2
fi
if (( ! DIAG )) && [[ ! -t 0 ]]; then
  echo S6_WSLG_BLOCKED_TTY_REQUIRED_NO_GOAL >&2; exit 2
fi
for cmd in curl bash python3; do
  command -v "$cmd" >/dev/null || {
    echo "S6_WSLG_BLOCKED_REQUIRED_COMMAND=$cmd" >&2; exit 2;
  }
done
TEMP="$(mktemp -d)"
trap 'rm -rf -- "$TEMP"' EXIT
fetch() {
  curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/$REPO/$SOURCE_SHA/$1" -o "$2"
  test -s "$2"
}
if (( DIAG )); then
  fetch "$PROBE" "$TEMP/s6_wslg_gl_probe.py"
  python3 -m py_compile "$TEMP/s6_wslg_gl_probe.py"
  OUT="$HOME/samsungaxi_gui_evidence/s6_wslg_qt_gl_$(date -u +%Y%m%dT%H%M%SZ)_$$"
  mkdir -p "$(dirname "$OUT")"
  python3 "$TEMP/s6_wslg_gl_probe.py" --out-dir "$OUT"
  echo S6_WSLG_DIAGNOSTIC_ONLY_NO_GOAL
  exit 0
fi
fetch "$WRAPPER" "$TEMP/owner_entry.sh"
bash -n "$TEMP/owner_entry.sh"
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$TEMP/owner_entry.sh" --self-test
echo "S6_WSLG_TESTED_RUNTIME_SOURCE_SHA=$SOURCE_SHA"
# Step 1: no Goal, no ROS startup; unchanged original Owner preflight.
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" SAMSUNGAXI_S6_VISION=1 \
  bash "$TEMP/owner_entry.sh" --s5-live --preflight-only
echo 'S6_WSLG_PREFLIGHT_PASS_NO_GOAL'
echo 'S6 Qt GUI uses scoped QT_QPA_PLATFORM=xcb; no automatic D3D12 forcing.'
echo 'Inspect REAL Gazebo/RViz scene; no Goal until YOU type YES-S5-LIVE-GOALS.'
echo 'If OpenGL still fails, do not approve Goal. Save ZIP; --diagnose-only is available.'
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" SAMSUNGAXI_S6_VISION=1 \
  bash "$TEMP/owner_entry.sh" --s5-live --perf-rgbd2 --approve-goals
