"""A-04 candidate provenance and S2-MAP-03 actual occupancy (NOT Nav2 L2)."""
from pathlib import Path
import math
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/smartdish_robot"))
from smartdish_robot.contract import load_pose_config, resolve_pose
from s3_map_contract import (
    validate_s2_map03_candidate, world_to_map, read_pgm,
    pixel_index, connected,
)

CANDIDATE = ROOT / "src/smartdish_robot/config/return_pose_candidate.yaml"
RELEASED = ROOT / "src/smartdish_robot/config/table_poses.yaml"


def test_candidate_reuses_actual_survey_world_waypoint_and_map_contract():
    metric = yaml.safe_load(
        (ROOT / "maps/candidates/s2_map03/restaurant_map_quality.json").read_text()
    )
    assert any(abs(w["world"][0] + 3.75) < .001 and
               abs(w["world"][1] + .60) < .001
               for w in metric["waypoints"])
    assert validate_s2_map03_candidate(ROOT)["free_connected"]
    poses = load_pose_config(CANDIDATE)
    dish = resolve_pose(poses, "DISH_RETURN")
    x, y = world_to_map((-3.75, -.60))
    assert math.dist((dish.x, dish.y), (x, y)) < .001
    assert dish.yaw == -1.57079632679


def test_candidate_cell_known_free_with_robot_clearance_and_connected():
    map_root = ROOT / "maps/candidates/s2_map03"
    meta = yaml.safe_load((map_root / "restaurant_map.yaml").read_text())
    w, h, pixels = read_pgm(map_root / "restaurant_map.pgm")
    res = float(meta["resolution"])
    origin = meta["origin"]
    point = (-1.15, 1.60)
    idx = pixel_index(w, h, origin, res, point)
    assert idx is not None and pixels[idx] >= 250, "RETURN_CELL_NOT_FREE"
    # Candidate should not be adjacent to occupied/unknown space at robot center.
    row, col = divmod(idx, w)
    radius_m = .25  # approximate footprint guard; NOT a Nav2 costmap proof
    radius_cells = math.ceil(radius_m / res)
    samples = 0
    for dr in range(-radius_cells, radius_cells + 1):
        for dc in range(-radius_cells, radius_cells + 1):
            if (dr * res)**2 + (dc * res)**2 > radius_m**2:
                continue
            r, c = row + dr, col + dc
            assert 0 <= r < h and 0 <= c < w, "RETURN_CLEARANCE_OUT_OF_MAP"
            assert pixels[r * w + c] >= 250, "RETURN_CLEARANCE_NOT_FREE"
            samples += 1
    assert samples >= 20
    assert connected(w, h, pixels, origin, res, (5.25, .38), point)
    assert connected(w, h, pixels, origin, res, point, (0., 0.))


def test_production_is_exactly_verified_real_gazebo_candidate():
    # A-06: Run 45124877004 physically validated this exact candidate.
    production = load_pose_config(RELEASED)
    candidate = load_pose_config(CANDIDATE)
    for destination in ("HOME", "T03", "DISH_RETURN"):
        assert resolve_pose(production, destination) == resolve_pose(candidate, destination)
