"""E contract-only tests: synthetic data verifies witness rules, NEVER Gazebo PASS."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "smartdish_e_live_witness", ROOT / "scripts/smartdish_e_live_witness.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def specimen():
    req_id = "REQ-E-001"
    return {
        "requests": [{"request_id": req_id, "table_id": "T03",
                      "table_wait_s": 10, "dropoff_wait_s": 5, "ai_enabled": False}],
        "goals": [
            {"request_id": req_id, "leg": leg, "destination_id": dest,
             "t": t, "odom_max_m": displacement, "odom_count": 30, "scan_count": 8}
            for leg, dest, t, displacement in zip(
                module.LEGS, module.DEST, (1.0, 23.0, 39.0), (5.1, 6.4, 1.9))
        ],
        "results": [
            {"request_id": req_id, "leg": leg, "result": "SUCCEEDED",
             "reason": "", "t": t}
            for leg, t in zip(module.LEGS, (10.0, 30.0, 50.0))
        ],
        "states": [
            {"state": st, "t": t} for st, t in (
                ("TO_TABLE", 0.5), ("WAIT_LOADING", 10.1),
                ("TO_RETURN", 23.1), ("WAIT_UNLOADING", 30.1),
                ("TO_HOME", 39.1), ("COMPLETED", 50.2)
            )
        ],
    }


def test_expected_trace_schema_only():
    assert module.verify_observations(specimen()) == ""


def test_no_navigation_result_never_passes():
    x = specimen()
    x["results"].pop()
    assert module.verify_observations(x) == "THREE_REAL_GOALS_OR_RESULTS_MISSING"


def test_ai_off_is_required():
    x = specimen()
    x["requests"][0]["ai_enabled"] = True
    assert module.verify_observations(x) == "AI_OFF_REQUIRED"


def test_one_request_id_only():
    x = specimen()
    x["results"][2]["request_id"] = "OTHER"
    assert module.verify_observations(x) == "REQUEST_ID_MISMATCH"


def test_wait_cannot_start_before_nav_success():
    x = specimen()
    x["goals"][1]["t"] = 18.0
    assert module.verify_observations(x) == "TABLE_WAIT_BEFORE_NAV_SUCCESS_OR_TOO_SHORT"


def test_unloading_wait_cannot_be_skipped():
    x = specimen()
    x["goals"][2]["t"] = 33.0
    assert module.verify_observations(x) == "RETURN_WAIT_BEFORE_NAV_SUCCESS_OR_TOO_SHORT"


def test_no_fabricated_odom():
    x = specimen()
    x["goals"][1]["odom_max_m"] = 0.0
    assert module.verify_observations(x) == "ODOM_MOVEMENT_NOT_PROVEN_TO_RETURN"


def test_failed_nav_never_completes():
    x = specimen()
    x["results"][0]["result"] = "FAILED"
    assert module.verify_observations(x) == "NAV2_NOT_SUCCEEDED_TO_TABLE"


def test_unexpected_ai_check_rejected():
    x = specimen()
    x["states"].insert(2, {"state": "AI_CHECK", "t": 21.0})
    assert module.verify_observations(x) == "AI_OFF_TRIGGERED_AI_CHECK"


def test_ui_completed_only_after_third_result():
    x = specimen()
    x["states"][-1]["t"] = 47.0
    assert module.verify_observations(x) == "COMPLETED_BEFORE_NAV_RESULT"


def test_legacy_s7_scripts_not_replaced():
    for path in (
        "scripts/s7_scene.py", "scripts/s6_vision_ai.py",
        "scripts/samsungaxi_s7_wsl2_l3_once.sh",
    ):
        assert (ROOT / path).is_file()


def test_integration_runner_syntax_contract():
    s = (ROOT / "scripts/smartdish_e_wsl2_one_shot.sh").read_text()
    assert "YES-SMARTDISH-A-GOALS" in s
    assert "SMARTDISH_D_UI_APPLIED" in s
    assert "gui:=true" in s
    assert "AI_OFF_REAL_RUN_PASS" in s
    assert "pkill" not in s and "killall" not in s
    assert "samsungaxi_s7_wsl2_l3_once.sh" not in s
