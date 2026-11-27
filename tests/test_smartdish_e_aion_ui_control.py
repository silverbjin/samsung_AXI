"""Owner parameter UI wiring contract (no display or Nav2 in CI)."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UI=(ROOT/"src/smartdish_service/smartdish_service/ui_app.py").read_text()
MANAGER=(ROOT/"src/smartdish_service/smartdish_service/manager_node.py").read_text()

def test_UI_optin_is_explicit_and_default_false():
    assert 'parser.add_argument("--owner-gazebo-integration", action="store_true"' in UI
    assert "owner_gazebo_integration=args.owner_gazebo_integration" in UI
    assert "if self.ai_available:" in UI
    assert "command=self.open_threshold_dialog" in UI

def test_UI_updates_C_via_ros_parameter_service_not_goal_topic():
    assert 'AsyncParameterClient(' in UI
    assert '"/smartdish_stability_inference"' in UI
    assert 'set_parameters_atomically([' in UI
    assert '"stable_confidence_min"' in UI
    assert '"unstable_confidence_min"' in UI
    assert '"E_OWNER_DYNAMIC_AI_CRITERIA_ACK' in UI
    assert 'self.active_state not in {"IDLE", "COMPLETED", "ERROR", "CANCELED"}' in UI

def test_AI_ON_manager_requires_owner_mode_and_manual_staff():
    assert 'parser.add_argument("--owner-gazebo-integration", action="store_true"' in MANAGER
    assert 'owner_manual_confirm_ai=(' in MANAGER
    assert 'AI_ON_PRODUCT_NOT_AUTHORIZED' in MANAGER
