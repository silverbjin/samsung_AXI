"""S7 educational package static/contract L0; no synthetic L2 PASS claims."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
solution=ROOT/'education/s7/instructor/s7_evidence_solution.py'
spec=importlib.util.spec_from_file_location('s7_teacher',solution)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def sample(tmp_path):
    rgb=bytes([30,100,230])*(16*16)
    ppm=tmp_path/'sample.ppm'
    ppm.write_bytes(b'P6\n16 16\n255\n'+rgb)
    scene={'scenario':'stacked','fixture_preloaded_at_world_start':True,
           'dynamic_fixture_spawn_requested':False,'world_sha256':'a'*64}
    legs=[{'label':'TABLE_3','action_status':4},{'label':'PICKUP_RETURN','action_status':4}]
    img={'frames':3,'width':16,'height':16,'image_sha256':hashlib.sha256(rgb).hexdigest(),
         'captured_after_arrival':True,'captured_after_subscribe':True}
    evidence={'s7_scene':scene,'real_nav_legs':legs,'s6_return_goal_sent':True,
              's6_integrated':True,'s6_vision':{'authorized':True,
                  'prediction':{'result':'STACKED','confidence':.75,'reason':'REAL_RGB_MODEL_INFERENCE'},
                  'image':img},
              's4_safety_stop':{'filtered_output_max_abs_mps':0.,'physical_odom_motion_m':0.}}
    return evidence,ppm

def test_solution_contract_and_no_robot_used(tmp_path):
    e,p=sample(tmp_path)
    result=mod.evaluate(e,p)
    assert result['verdict']=='S7_TRAINING_EVIDENCE_CONTRACT_PASS'
    assert result['rgb_frames']==3
    assert result['nav2_labels']==['TABLE_3','PICKUP_RETURN']
    student=(ROOT/'education/s7/student/s7_evidence_todo.py').read_text()
    assert 'raise NotImplementedError' in student
    assert 'S7_STUDENT_TODO_NOT_COMPLETED_NO_PASS' in student

def test_solution_rejects_fake_vision_missing_stop_and_wrong_world(tmp_path):
    e,p=sample(tmp_path)
    bad=copy.deepcopy(e);bad['s6_vision']['authorized']=False
    with pytest.raises(ValueError,match='REAL_VISION'):mod.evaluate(bad,p)
    bad=copy.deepcopy(e);bad['s7_scene']['fixture_preloaded_at_world_start']=False
    with pytest.raises(ValueError,match='STARTUP_WORLD'):mod.evaluate(bad,p)
    bad=copy.deepcopy(e);bad['s4_safety_stop']['physical_odom_motion_m']=.11
    with pytest.raises(ValueError,match='LIDAR_STOP'):mod.evaluate(bad,p)
    bad=copy.deepcopy(e);bad['real_nav_legs'][1]['action_status']=6
    with pytest.raises(ValueError,match='GOAL_NOT_SUCCEEDED'):mod.evaluate(bad,p)
    p.write_bytes(p.read_bytes()[:-3]+bytes([0,0,0]))
    with pytest.raises(ValueError,match='PPM_SHA'):mod.evaluate(e,p)

def test_beginner_guides_and_s7_traceability_are_present():
    for doc in ('docs/s7/INSTRUCTOR_DEMO_GUIDE_KO.md','docs/s7/STUDENT_LAB_GUIDE_KO.md','docs/s7/INSTRUCTOR_SOLUTIONS_KO.md'):
        t=(ROOT/doc).read_text()
        assert 'TABLE_3' in t
        assert 'STOP' in t or 'Collision Monitor' in t
    assert (ROOT/'docs/reports/s7/2026-11-23_S7-DISH-STARTUP-01_EDU_KO.md').exists()
    assert (ROOT/'docs/reports/s7/2026-11-23_S7-VISION-NEGATIVE-01_EDU_KO.md').exists()
