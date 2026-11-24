"""L0 pixel-frame UI tests; no ROS nodes or display required."""
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "smartdish_service"))
from smartdish_service.ui_app import read_layout, STATES_KO

LAYOUT = ROOT / "src" / "smartdish_service" / "config" / "ui_layout.yaml"


def test_layout_is_pixel_only_and_t03_only_active():
    layout = read_layout(LAYOUT)
    assert layout["frame"] == "ui_pixels"
    assert [tid for tid, entry in layout["tables"].items() if entry["enabled"]] == ["T03"]
    assert set(layout["areas"]) == {"HOME", "DISH_RETURN"}
    for item in layout["tables"].values():
        assert len(item["rect"]) == 4


def test_fsm_states_have_ui_names():
    assert {"IDLE", "TO_TABLE", "WAIT_LOADING", "AI_CHECK",
            "NEEDS_CONFIRMATION", "TO_RETURN", "WAIT_UNLOADING",
            "TO_HOME", "COMPLETED", "ERROR", "CANCELED"}.issubset(STATES_KO)


def test_layout_wrong_frame_fails(tmp_path):
    p = tmp_path / "wrong.yaml"
    p.write_text("frame: map\ntables: {}\n")
    with pytest.raises(ValueError, match="UI_LAYOUT_MUST_USE_PIXEL_FRAME"):
        read_layout(p)


def test_no_ros_cmdvel_or_pixel_pose_in_d_service():
    from smartdish_service import mission_manager
    from smartdish_service import manager_node
    source = (ROOT / "src" / "smartdish_service" / "smartdish_service")
    text = "\n".join(p.read_text() for p in source.glob("*.py"))
    assert "create_publisher(SpeedLimit" not in text
    assert "BasicNavigator" not in text
    assert "PoseStamped(" not in text
    assert "create_publisher(Twist" not in text
    assert mission_manager.LEG_DESTINATIONS == {
        "TO_TABLE": "T03", "TO_RETURN": "DISH_RETURN", "TO_HOME": "HOME"}


def test_manager_callback_timer_is_monotonic_not_ros_sim_time():
    code = (ROOT / "src" / "smartdish_service" /
            "smartdish_service" / "manager_node.py").read_text()
    assert "ClockType.STEADY_TIME" in code
    assert "clock=Clock(clock_type=ClockType.STEADY_TIME)" in code


@pytest.mark.parametrize("width,height", [
    (806, 460), (760, 460), (610, 420), (1100, 730), (1450, 860)
])
def test_ui_floorplan_fits_canvas(width, height):
    from smartdish_service.ui_app import floorplan_scale
    s = floorplan_scale(width, height)
    assert 0 < s <= 1.10
    assert 806 * s <= width + 0.0001
    assert 460 * s <= height + 0.0001


@pytest.mark.parametrize("width,height", [(0, 460), (-1, 400), (806, 0)])
def test_ui_scale_rejects_invalid_size(width, height):
    from smartdish_service.ui_app import floorplan_scale
    with pytest.raises(ValueError, match="UI_CANVAS_DIMENSIONS_MUST_BE_POSITIVE"):
        floorplan_scale(width, height)


def test_controls_reserved_before_floorplan():
    code = (ROOT / "src/smartdish_service" /
            "smartdish_service/ui_app.py").read_text(encoding="utf-8")
    assert code.index('right.pack(side="right", fill="y")') < code.index(
        'left.pack(side="left", fill="both", expand=True')
    assert 'self.canvas = tk.Canvas(left, width=1, height=1' in code
    assert 'self.canvas.bind("<Configure>", self._resize_floorplan)' in code


def test_time_inputs_use_one_column():
    code = (ROOT / "src/smartdish_service" /
            "smartdish_service/ui_app.py").read_text(encoding="utf-8")
    assert 'timing.grid_columnconfigure(0, weight=1)' in code
    assert 'self.loading_spin.grid(row=1, column=0, sticky="ew"' in code
    assert 'self.dropoff_spin.grid(row=3, column=0, sticky="ew"' in code
    assert 'row=0, column=1' not in code


def test_request_protocol_unchanged_after_visual_fix():
    code = (ROOT / "src/smartdish_service" /
            "smartdish_service/ui_app.py").read_text(encoding="utf-8")
    for required in ('"table_id": "T03"', '"table_wait_s": wait',
                     '"dropoff_wait_s": dropoff', 'self.root.after(60, self.poll_ros)',
                     'SMARTDISH_D_UI_READY'):
        assert required in code
