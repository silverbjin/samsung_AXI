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
    assert mod.world_to_map(mod.WORLD_TABLE3)==mod.MAP_TABLE3
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
