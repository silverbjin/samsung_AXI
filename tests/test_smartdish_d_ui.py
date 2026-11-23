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
