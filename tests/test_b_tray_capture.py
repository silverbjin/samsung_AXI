"""Read-only ROS Image converter contract tests: no rclpy/Gazebo required."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parents[1] / 'ai/scripts'))
from capture_tray_ros import decode_ros_rgb, save_unlabelled_frame, TRAY_TOPIC


def msg(encoding='rgb8', pad=0):
    # Two pixels per row; optional padding. red then green in RGB source.
    rgb = bytes((255, 0, 0, 0, 255, 0))
    if encoding == 'bgr8':
        rgb = bytes((0, 0, 255, 0, 255, 0))
    return SimpleNamespace(width=2,height=2,step=6+pad,encoding=encoding,
                           data=(rgb + bytes([99])*pad)*2,
                           header=SimpleNamespace(frame_id='tray_camera',stamp=SimpleNamespace(sec=42,nanosec=123)))


def test_rgb8_and_bgr8_with_padding_decode_the_same():
    a = decode_ros_rgb(msg('rgb8',2))
    b = decode_ros_rgb(msg('bgr8',4))
    assert a.size == (2,2)
    assert a.getpixel((0,0)) == (255,0,0)
    assert a.tobytes() == b.tobytes()


def test_invalid_encoding_stride_payload_rejected():
    m = msg('mono8')
    with pytest.raises(ValueError,match='B_UNSUPPORTED_TRAY_IMAGE_ENCODING'):
        decode_ros_rgb(m)
    m = msg(); m.step = 3
    with pytest.raises(ValueError,match='B_INVALID_TRAY_IMAGE_BUFFER'):
        decode_ros_rgb(m)
    m = msg(); m.data = b'bad'
    with pytest.raises(ValueError,match='B_INVALID_TRAY_IMAGE_BUFFER'):
        decode_ros_rgb(m)


def test_capture_unlabelled_private_and_no_manifest(tmp_path):
    out = tmp_path / 'ai/data/private/once.png'
    m = msg('rgb8',2)
    record = save_unlabelled_frame(m,out,tmp_path)
    assert record['label'] is None
    assert record['ground_truth'] == 'NOT_OBSERVED'
    assert record['topic'] == TRAY_TOPIC
    assert record['stamp_ns'] == 42_000_000_123
    assert record['image_sha256'] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert json.loads(out.with_suffix('.json').read_text()) == record
    assert not (tmp_path/'ai/data/manifest.csv').exists()
    with Image.open(out) as image:
        assert image.mode == 'RGB' and image.size == (2,2)
    with pytest.raises(ValueError,match='B_CAPTURE_WILL_NOT_OVERWRITE'):
        save_unlabelled_frame(m,out,tmp_path)


def test_capture_topic_and_private_path_guards(tmp_path):
    with pytest.raises(ValueError,match='B_CAMERA_TOPIC_CONTRACT_MISMATCH'):
        save_unlabelled_frame(msg(),tmp_path/'ai/data/private/x.png',tmp_path,topic='/camera/image_raw')
    with pytest.raises(ValueError,match='B_CAPTURE_OUTPUT_MUST_BE_PRIVATE_PNG'):
        save_unlabelled_frame(msg(),tmp_path/'public.png',tmp_path)
