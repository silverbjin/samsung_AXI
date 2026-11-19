"""Small regression for CI/owner: ROS setup scripts may reference unset vars."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_all_ros_setup_sources_temporarily_disable_nounset(tmp_path):
    fake = tmp_path / 'ros_setup.bash'
    # Simulate an upstream setup script that expands an optional unset value.
    fake.write_text('printf "TRACE=%s\\n" "$AMENT_TRACE_SETUP_FILES"\n')
    unsafe = subprocess.run(['bash', '-c', f'set -Eeuo pipefail; source "{fake}"'],
                            capture_output=True, text=True)
    assert unsafe.returncode != 0 and 'unbound variable' in unsafe.stderr
    safe = subprocess.run(['bash', '-c', f'set -Eeuo pipefail; set +u; source "{fake}"; set -u'],
                          capture_output=True, text=True)
    assert safe.returncode == 0

    candidates = [ROOT / '.github/workflows/restaurant-ci.yml',
                  ROOT / 'scripts/restaurant_demo.sh']
    source_line = re.compile(r'^\s*source (?:/opt/ros/jazzy/setup\.bash|install/setup\.bash|"\$ROOT/install/setup\.bash")\s*$', re.M)
    for path in candidates:
        lines = path.read_text().splitlines()
        hits = [i for i, line in enumerate(lines) if source_line.fullmatch(line)]
        assert hits, f'No ROS setup found in {path}'
        for i in hits:
            assert i > 0 and lines[i - 1].strip() == 'set +u', f'Unguarded source {path}:{i+1}'
            assert i+1 < len(lines) and lines[i+1].strip() == 'set -u', f'nounset not restored {path}:{i+1}'
