"""Offline S3 map release and map-frame tests: no ROS nor synthetic success."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s3release',ROOT/'scripts/s3_map_contract.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_release_map_sha_world_and_pickup_table3_connected():
    data=mod.validate_release(ROOT)
    assert data['free_connected'] is True
    assert data['release_run']=='44551726313'
    assert data['pickup_map_xy']==(0.,0.)
    assert abs(data['table3_map_xy'][0]-5.25)<1e-9
    assert abs(data['table3_map_xy'][1]-.38)<1e-9

def test_world_coords_are_not_map_goal_coords():
    assert mod.world_to_map(mod.WORLD_PICKUP)==mod.MAP_PICKUP
    got=mod.world_to_map(mod.WORLD_TABLE3)
    assert all(abs(a-b)<1e-9 for a,b in zip(got,mod.MAP_TABLE3))
    assert mod.WORLD_PICKUP!=mod.MAP_PICKUP

def test_binary_pgm_parser_rejects_corrupt_file(tmp_path):
    f=tmp_path/'map.pgm'
    f.write_bytes(b'P5\n# comment\n10 9\n255\n'+bytes([254])*90)
    w,h,px=mod.read_pgm(f)
    assert (w,h,len(px))==(10,9,90)
    f.write_bytes(b'P5\n10 9\n255\n'+bytes([254])*80)
    import pytest
    with pytest.raises(ValueError,match='PGM_PIXEL_LENGTH_MISMATCH'):
        mod.read_pgm(f)


def test_separate_s2_map03_observation_candidate_is_real_and_connected():
    from pathlib import Path
    candidate=ROOT/'maps/candidates/s2_map03/restaurant_map.pgm'
    assert candidate.is_file()
    q=mod.validate_s2_map03_candidate(ROOT)
    assert q['width']==202 and q['height']==185
    assert q['pgm_sha256']=='aedaed8f89e703f33ef22f9cf0c9d8f77b11763157d6e3a61c839a58fe871f00'
    assert q['free_connected']
    assert mod.validate_release(ROOT)['release_run']=='44551726313'
