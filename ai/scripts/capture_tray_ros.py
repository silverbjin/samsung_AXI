#!/usr/bin/env python3
"""Capture one RGB sensor_msgs/Image frame to *unlabelled* private PNG.

No stability classification, no ROS control publication, no manifest mutation.
The ROS dependency is imported only when running the live capture CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from PIL import Image

TRAY_TOPIC = '/smartdish/tray/image_raw'


def decode_ros_rgb(msg) -> Image.Image:
    """Decode only contract rgb8/bgr8, stripping optional row padding."""
    encoding = str(msg.encoding).lower()
    if encoding not in ('rgb8', 'bgr8'):
        raise ValueError('B_UNSUPPORTED_TRAY_IMAGE_ENCODING')
    try:
        width, height, step = int(msg.width), int(msg.height), int(msg.step)
        raw = bytes(msg.data)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError('B_INVALID_TRAY_IMAGE_BUFFER') from exc
    if width <= 0 or height <= 0 or step < width * 3 or len(raw) != step * height:
        raise ValueError('B_INVALID_TRAY_IMAGE_BUFFER')
    packed = b''.join(raw[y * step: y * step + width * 3] for y in range(height))
    mode = 'RGB' if encoding == 'rgb8' else 'BGR'
    return Image.frombytes('RGB', (width, height), packed, 'raw', mode)


def save_unlabelled_frame(msg, output: Path, root: Path, topic: str = TRAY_TOPIC) -> dict:
    """Store raw-resolution observation plus provenance; NEVER set physical labels."""
    if topic != TRAY_TOPIC:
        raise ValueError('B_CAMERA_TOPIC_CONTRACT_MISMATCH')
    allowed = (root.resolve() / 'ai/data/private').resolve()
    output = output.resolve()
    if not output.is_relative_to(allowed) or output.suffix.lower() != '.png':
        raise ValueError('B_CAPTURE_OUTPUT_MUST_BE_PRIVATE_PNG')
    metadata_path = output.with_suffix('.json')
    if output.exists() or metadata_path.exists():
        raise ValueError('B_CAPTURE_WILL_NOT_OVERWRITE')
    frame = decode_ros_rgb(msg)
    stamp = getattr(getattr(msg, 'header', None), 'stamp', None)
    stamp_ns = int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec) if stamp else None
    # Images without synchronized ROS stamps are still raw observations, NOT labels.
    raw_data_sha = hashlib.sha256(bytes(msg.data)).hexdigest()
    record = {'schema': 1, 'topic': topic, 'frame_id': getattr(getattr(msg, 'header', None), 'frame_id', ''),
              'stamp_ns': stamp_ns, 'encoding': msg.encoding,
              'width': frame.width, 'height': frame.height,
              'raw_message_sha256': raw_data_sha, 'annotation': 'UNLABELLED',
              'ground_truth': 'NOT_OBSERVED', 'label': None,
              'physics_evidence': None, 'scope': 'CAPTURE_ONLY_NOT_MODEL_TRAINING'}
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open('xb') as stream:
            frame.save(stream, format='PNG')
        record['image_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
        with metadata_path.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write('\n')
    except Exception:
        # Keep a preexisting file untouched; cleanup only the one just created.
        if output.is_file():
            output.unlink()
        raise
    return record


def receive_one_frame(timeout_s: float, topic: str = TRAY_TOPIC):
    """Read only, no navigation, no ROS message output or label inference."""
    if topic != TRAY_TOPIC:
        raise ValueError('B_CAMERA_TOPIC_CONTRACT_MISMATCH')
    if not 0 < timeout_s <= 120:
        raise ValueError('B_INVALID_CAPTURE_TIMEOUT')
    try:
        import rclpy
        from rclpy.qos import qos_profile_sensor_data
        from sensor_msgs.msg import Image as RosImage
    except ImportError as exc:
        raise RuntimeError('B_ROS_JAZZY_RUNTIME_NOT_AVAILABLE') from exc
    received = []
    rclpy.init()
    node = None
    try:
        node = rclpy.create_node('smartdish_b_tray_one_frame')
        node.create_subscription(RosImage, topic, lambda msg: received.append(msg), qos_profile_sensor_data)
        deadline = time.monotonic() + timeout_s
        while not received and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(.2, max(0., deadline - time.monotonic())))
        if not received:
            raise TimeoutError('B_TRAY_CAMERA_TIMEOUT_NO_IMAGE')
        return received[0]
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, default=Path('ai/data/private/tray_unlabelled.png'))
    parser.add_argument('--topic', default=TRAY_TOPIC)
    parser.add_argument('--timeout-s', type=float, default=15.)
    args = parser.parse_args()
    try:
        frame = receive_one_frame(args.timeout_s, args.topic)
        row = save_unlabelled_frame(frame, args.root / args.output, args.root, args.topic)
    except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
        print('B_TRAY_CAPTURE_BLOCKED ' + str(exc), flush=True)
        return 2
    print('B_TRAY_CAPTURE_UNLABELLED_SAVED ' + json.dumps(row, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
