"""C MVP read-only contract tests. No ROS/Nav2 motion and NO model training."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src/smartdish_ai'))

from ai.evaluation.dataset_contract import FIELDS, read_verified_split
from ai.train.evaluate import classification_metrics
from smartdish_ai.inference_core import InferenceCore
from smartdish_ai.stability_inference_node import unpack_ros_rgb


def frame(value=20):
    return bytes([value, 40, 60]) * (16 * 16)


def query(req="REQ-1", cap="CAP-1"):
    return json.dumps({"request_id": req, "capture_id": cap})


def test_contract_one_request_one_response_and_ids():
    core = InferenceCore(lambda *_: ('STABLE', 0.91), 'resnet18-realsha', confidence_min=.80)
    assert core.cache_rgb(frame(),16,16,received_at=100,stamp_ns=400)
    response = core.handle_request(query(),now=101)
    assert response == {"request_id":"REQ-1","capture_id":"CAP-1", "status":"STABLE",
                        "confidence":.91,"model_version":"resnet18-realsha"}
    assert core.handle_request(query(),now=101) is None


def test_new_request_cannot_reuse_consumed_frame():
    core = InferenceCore(lambda *_: ('STABLE', .99), 'v')
    core.cache_rgb(frame(),16,16,received_at=10)
    assert core.handle_request(query(),now=11)['status'] == 'STABLE'
    nxt = core.handle_request(query('REQ-1','CAP-2'),now=11)
    assert nxt['status'] == 'UNKNOWN' and nxt['confidence'] is None


def test_new_frame_new_request_works():
    core = InferenceCore(lambda *_: ('UNSTABLE', .84), 'v')
    core.cache_rgb(frame(20),16,16,received_at=10)
    assert core.handle_request(query(),now=11)['status'] == 'UNSTABLE'
    core.cache_rgb(frame(30),16,16,received_at=12)
    assert core.handle_request(query('REQ-2','CAP-2'),now=12)['status'] == 'UNSTABLE'


def test_model_absent_unknown_even_with_image():
    core = InferenceCore(None,'fake_version')
    core.cache_rgb(frame(),16,16,received_at=0)
    r = core.handle_request(query(),now=1)
    assert (r['status'],r['confidence'],r['model_version']) == ('UNKNOWN',None,'none')


def test_stale_and_future_frames_unknown():
    for now in (12.1, 9.9):
        core = InferenceCore(lambda *_: ('STABLE', .9), 'v',max_image_age_s=2)
        core.cache_rgb(frame(),16,16,received_at=10)
        assert core.handle_request(query(),now=now)['status'] == 'UNKNOWN'


def test_low_confidence_unknown_and_never_fake_stable():
    for conf in (0.79,float('nan'),float('inf'),-1,1.1,True):
        core = InferenceCore(lambda *_: ('STABLE', conf), 'v')
        core.cache_rgb(frame(),16,16,received_at=1)
        result = core.handle_request(query(),now=2)
        assert result['status'] == 'UNKNOWN' and result['confidence'] is None


def test_predictor_exception_unknown():
    def broken(*_):
        raise RuntimeError('test-only simulated weights/cuda error')
    core = InferenceCore(broken,'v')
    core.cache_rgb(frame(),16,16,received_at=1)
    assert core.handle_request(query(),now=2)['status'] == 'UNKNOWN'


def test_invalid_request_does_not_publish_or_consume_frame():
    core = InferenceCore(lambda *_: ('STABLE', .95), 'v')
    core.cache_rgb(frame(),16,16,received_at=1)
    for invalid in ('{', '[]', '{}', '{"request_id":"","capture_id":"x"}',
                    '{"request_id":3,"capture_id":"x"}'):
        assert core.handle_request(invalid,now=2) is None
    assert core.handle_request(query(),now=2)['status'] == 'STABLE'


def test_duplicate_timestamp_rejected():
    core = InferenceCore(lambda *_: ('STABLE', .99), 'v')
    assert core.cache_rgb(frame(),16,16,received_at=1,stamp_ns=123)
    assert not core.cache_rgb(frame(),16,16,received_at=2,stamp_ns=123)
    assert not core.cache_rgb(frame(),16,16,received_at=3,stamp_ns=122)
    assert core.cache_rgb(frame(),16,16,received_at=4,stamp_ns=124)


def test_rgb_and_bgr_padded_rows():
    rgb = bytes([9, 17, 21]) * 16 + bytes([0]) * 2
    msg = SimpleNamespace(encoding='rgb8', width=16, height=16, step=50, data=rgb*16)
    raw,w,h = unpack_ros_rgb(msg)
    assert (w,h,raw[:3],len(raw)) == (16,16,bytes([9,17,21]),16*16*3)
    msg.encoding = 'bgr8'
    raw,_,_ = unpack_ros_rgb(msg)
    assert raw[:3] == bytes([21,17,9])


def test_bad_image_encoding_and_corrupt_buffer():
    msg = SimpleNamespace(encoding='mono8',width=16,height=16,step=48,data=bytes(768))
    with pytest.raises(ValueError,match='C_UNSUPPORTED_IMAGE_ENCODING'):
        unpack_ros_rgb(msg)
    msg.encoding = 'rgb8'; msg.data = b'bad'
    with pytest.raises(ValueError,match='C_INVALID_IMAGE_BUFFER'):
        unpack_ros_rgb(msg)


def test_no_real_data_fails_training_contract(tmp_path):
    path = tmp_path/'split.csv'
    with path.open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS); writer.writeheader()
    with pytest.raises(ValueError,match='C_TRAINING_NOT_RUN_NO_REAL_DATA'):
        read_verified_split(path,tmp_path)


def physical_rows(tmp_path):
    """FAKE metadata is ONLY to exercise validation; never feed to a trainer."""
    rows=[]
    for label in ('STABLE','UNSTABLE'):
        for n, split in enumerate(('train','val','test')):
            name=f'{label}_{n}.png'
            path=tmp_path/name
            Image.new('RGB',(224,224),(n*30+10,50 if label=='STABLE' else 100,90)).save(path)
            rows.append({"sample_id":f'{label}-{n}',"scene_id":f'{label}-{n}',
                         "stack_id":f'{label}-{n}',"label":label,"image_path":name,
                         "source":"GAZEBO_TRAY", "capture_config":json.dumps({"physics_evidence":"TEST_ONLY"}),
                         "license_status":"OWNED","ground_truth":"PHYSICS_OBSERVED",
                         "image_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"split":split})
    return rows


def write_rows(tmp_path, rows):
    path=tmp_path/'split.csv'
    with path.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    return path


def test_contract_rejects_b_fixture_even_when_label_looks_valid(tmp_path):
    rows=physical_rows(tmp_path)
    rows[0].update(source='CONTRACT_FIXTURE',ground_truth='MOCK_ONLY')
    with pytest.raises(ValueError,match='C_FIXTURE_OR_UNVERIFIED_GROUND_TRUTH'):
        read_verified_split(write_rows(tmp_path,rows),tmp_path)


def test_contract_rejects_wrong_s7_label(tmp_path):
    rows=physical_rows(tmp_path);rows[0]['label']='STACKED'
    with pytest.raises(ValueError,match='C_INVALID_LABEL'):
        read_verified_split(write_rows(tmp_path,rows),tmp_path)


def test_contract_rejects_group_leak(tmp_path):
    rows=physical_rows(tmp_path);rows[1]['stack_id']=rows[0]['stack_id']
    with pytest.raises(ValueError,match='C_STACK_SPLIT_LEAK'):
        read_verified_split(write_rows(tmp_path,rows),tmp_path)


def test_contract_rejects_sha_tamper(tmp_path):
    rows=physical_rows(tmp_path);rows[0]['image_sha256']='0'*64
    with pytest.raises(ValueError,match='C_IMAGE_SHA_MISMATCH'):
        read_verified_split(write_rows(tmp_path,rows),tmp_path)


def test_contract_rejects_missing_physics_reference(tmp_path):
    rows=physical_rows(tmp_path);rows[0]['capture_config']='{}'
    with pytest.raises(ValueError,match='C_PHYSICS_EVIDENCE_REFERENCE_MISSING'):
        read_verified_split(write_rows(tmp_path,rows),tmp_path)


def test_contract_complete_fixture_shape_mock_only(tmp_path):
    rows=physical_rows(tmp_path)
    checked=read_verified_split(write_rows(tmp_path,rows),tmp_path)
    assert len(checked)==6  # Structurally valid only; labels NOT PHYSICALLY VERIFIED.


def test_metrics_known_confusion_matrix():
    data=classification_metrics(['STABLE','STABLE','UNSTABLE','UNSTABLE'],
                                ['STABLE','UNSTABLE','UNSTABLE','UNSTABLE'])
    assert data['confusion_matrix']==[[1,1],[0,2]]
    assert data['accuracy']==.75
    assert data['macro_f1']==pytest.approx((2/3 + 4/5)/2)


def test_metrics_missing_class_rejected():
    with pytest.raises(ValueError,match='C_EVALUATION_CLASS_MISSING'):
        classification_metrics(['STABLE'],['STABLE'])
