import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_a04_clearance import candidate,read_map,grid_screen,HALF
def test_original_real_map_hold():
    cfg,a=read_map(ROOT/"maps/restaurant_map.yaml")
    assert a.shape==(180,201)
    assert [(a==v).sum() for v in (0,-1,100)]==[24811,9781,1588]
    import yaml
    poses=yaml.safe_load((ROOT/"src/smartdish_robot/config/table_poses.yaml").read_text())["poses"]
    assert not grid_screen(cfg,a,poses)["connected"]
def test_candidate_preserves_occupied_and_outside():
    cfg={"resolution":.05,"origin":[0,0,0]}
    a=np.full((100,100),-1);a[50,50]=100
    g={"floor":{"lo":[-2,-2,-.2],"hi":[2,2,0]},
       "obstacles":[{"lo":[0,0,.5],"hi":[.2,.2,.8]}]}
    b=candidate(cfg,a,g)
    assert b[50,50]==100 and b[0,0]==-1
    assert b[45,53]==100 # high obstacle still projected
    assert np.count_nonzero(b==0)>0
def test_candidate_no_free_without_floor():
    cfg={"resolution":.05,"origin":[0,0,0]}
    g={"floor":{"lo":[10,10,-.2],"hi":[11,11,0]},"obstacles":[]}
    assert (candidate(cfg,np.full((20,20),-1),g)==-1).all()
