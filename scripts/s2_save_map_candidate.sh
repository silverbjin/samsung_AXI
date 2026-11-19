#!/usr/bin/env bash
# Save a real /map from the currently running SLAM session without overwriting accepted maps.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ -r /opt/ros/jazzy/setup.bash ]] || { echo 'S2_BLOCKED_ROS_JAZZY'; exit 2; }
set +u
source /opt/ros/jazzy/setup.bash
if [[ -r "$ROOT/install/setup.bash" ]]; then source "$ROOT/install/setup.bash"; fi
set -u
ros2 pkg prefix nav2_map_server >/dev/null || exit 2
PREFIX="$ROOT/maps/candidates/$(date -u +%Y%m%dT%H%M%SZ)/restaurant_map"
mkdir -p "$(dirname "$PREFIX")"
timeout --signal=INT --kill-after=5s 45s ros2 run nav2_map_server map_saver_cli -f "$PREFIX"
python3 - "$PREFIX" <<'PY'
from pathlib import Path
import sys,yaml
p=Path(sys.argv[1]).with_suffix('.yaml')
if not p.is_file():raise SystemExit('S2_MAP_YAML_MISSING')
v=yaml.safe_load(p.read_text())
image=(p.parent/v['image']).resolve()
if not image.is_file() or image.stat().st_size<100:raise SystemExit('S2_MAP_IMAGE_MISSING')
print('S2_MAP_CANDIDATE_SAVED_NOT_PROMOTED='+str(p))
PY
