"""S6-VISION-01: supervised model, UNKNOWN, negative return gate contracts."""
import importlib.util
from pathlib import Path
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s6_model',ROOT/'scripts/s6_vision_ai.py')
ml=importlib.util.module_from_spec(spec);spec.loader.exec_module(ml)

def ppm(path,w,h,data):
    path.write_bytes(f'P6\n{w} {h}\n255\n'.encode()+data)

def test_training_provenance_and_real_prediction_contract(tmp_path):
    a=bytes([50,40,30]*32*32)
    b=bytes([80,150,235]*32*32)
    p0=tmp_path/'empty.ppm';p1=tmp_path/'stacked.ppm'
    ppm(p0,32,32,a);ppm(p1,32,32,b)
    model=ml.train(p0,p1,tmp_path/'model.json')
    assert model['algorithm']=='supervised_two_prototype_rgb_layers'
    assert ml.infer(model,a,32,32)['result']=='NOT_STACKED'
    pos=ml.infer(model,b,32,32)
    assert pos['result']=='STACKED'
    assert pos['reason']=='REAL_RGB_MODEL_INFERENCE'
    assert ml.infer(model,b,12,32)['result']=='UNKNOWN'
    assert json.loads((tmp_path/'model.json').read_text())==model

def test_s6_must_hold_on_unknown_missing_image_nonstacked_and_motion(tmp_path):
    a=bytes([50,40,30]*32*32)
    b=bytes([80,150,235]*32*32)
    p0=tmp_path/'empty.ppm';p1=tmp_path/'stacked.ppm'
    ppm(p0,32,32,a);ppm(p1,32,32,b)
    model=ml.train(p0,p1,tmp_path/'m.json')
    stacked=ml.infer(model,b,32,32)
    empty=ml.infer(model,a,32,32)
    assert ml.accept_return(stacked,True,True,True)
    assert not ml.accept_return(empty,True,True,True)
    assert not ml.accept_return({'result':'UNKNOWN','reason':'TIMEOUT'},True,True,True)
    assert not ml.accept_return(stacked,False,True,True)
    assert not ml.accept_return(stacked,True,False,True)
    assert not ml.accept_return(stacked,True,True,False)
    assert not ml.accept_return({'result':'STACKED','confidence':1,'reason':'MANUAL_OVERRIDE'},True,True,True)
    with pytest.raises(ValueError,match='S6_TRAIN_CLASSES_NOT_VISUALLY_SEPARABLE'):
        ml.train(p0,p0,tmp_path/'bad.json')
