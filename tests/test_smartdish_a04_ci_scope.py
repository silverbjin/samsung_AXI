import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_a04_ci_scope import classify
def test_docs_only():
    assert classify(["docs/reports/smartdish/a/A_PROD_04_DBG_05_EDU_KO.md"])=={"geometry":False,"no-goal":False,"motion":False}
def test_motion_only():
    assert classify(["scripts/smartdish_a04_motion.py"])=={"geometry":False,"no-goal":False,"motion":True}
def test_geometry_requires_motion_same_session():
    assert classify(["scripts/smartdish_a04_clearance.py"])=={"geometry":True,"no-goal":False,"motion":True}
def test_workflow_only():
    assert not any(classify([".github/workflows/smartdish-a04-motion.yml","scripts/smartdish_a04_ci_scope.py","tests/test_smartdish_a04_ci_scope.py"]).values())
