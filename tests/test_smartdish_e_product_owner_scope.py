import sys,ast
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_e_product_owner_scope import check_identity,model_receipt,MODEL_SHA,MODEL_VERSION,MODEL_SCOPE
PIN="a"*40;RUN="20261127T133000Z-1"
def env():
    return dict(WSL_DISTRO_NAME="Ubuntu",DISPLAY=":0",SMARTDISH_E_OWNER_PRODUCT_RUN=RUN,
        SMARTDISH_E_SOURCE_SHA=PIN,GZ_PARTITION="smartdish_a04_owner_"+RUN,
        SMARTDISH_E_OWNER_CONSENT="YES-E-PRODUCT-GO",ROS_DOMAIN_ID="80")
def test_explicit_owner_admission():
    check_identity(env(),"WSL2-microsoft",True,PIN,RUN)
    for k,v in (("CI","true"),("GITHUB_ACTIONS","true"),("DISPLAY",""),("SMARTDISH_E_OWNER_CONSENT",""),("GZ_PARTITION","wrong")):
        with pytest.raises(RuntimeError):check_identity(env()|{k:v},"WSL2-microsoft",True,PIN,RUN)
    with pytest.raises(RuntimeError):check_identity(env(),"linux",True,PIN,RUN)
    with pytest.raises(RuntimeError):check_identity(env(),"WSL2-microsoft",False,PIN,RUN)
def test_owner_model_receipt_never_accepts_ci_or_product_release():
    d=dict(scope=MODEL_SCOPE,private_model_loaded=True,checkpoint_sha256=MODEL_SHA,model_version=MODEL_VERSION,
           test4_opened=False,general_product_approved=False)
    assert model_receipt(d)
    for patch in (dict(private_model_loaded=False),dict(scope="CI_DOUBLE_NOT_ACTUAL_MODEL"),dict(checkpoint_sha256="a"*64),dict(test4_opened=True),dict(general_product_approved=True)):
        assert not model_receipt(d|patch)
def test_owner_ui_has_no_auto_click_and_c_has_real_loader():
    ui=ast.parse((ROOT/"scripts/smartdish_e_product_owner_ui.py").read_text())
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="invoke" for n in ast.walk(ui))
    c=(ROOT/"scripts/smartdish_e_product_owner_c.py").read_text()
    assert "load_predictor(path,**kwargs)" in c and "self.real(rgb,w,h)" in c and "CI_DOUBLE" not in c

def test_owner_request_cannot_use_ai_off_or_change_wait_scenario():
    from smartdish_e_product_owner_scope import owner_request
    d=dict(schema_version=2,profile="OWNER_PRODUCT_RECOVERY",table_id="T03",ai_enabled=True,table_wait_s=10,dropoff_wait_s=5)
    assert owner_request(d)
    for patch in (dict(ai_enabled=False),dict(table_id="T04"),dict(table_wait_s=9),dict(dropoff_wait_s=6),dict(table_wait_s=10.0)):
        assert not owner_request(d|patch)
