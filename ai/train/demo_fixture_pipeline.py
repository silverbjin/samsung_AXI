#!/usr/bin/env python3
"""Use B's exact external branch fixture generator to exercise C without physical labels.

All artifacts are MOCK_ONLY, produced outside the repository and not deployable.
B script is supplied by a separate read-only checkout; no B source is vendored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from ai.evaluation.dataset_contract import read_verified_split, summarize


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, env={**os.environ, 'OMP_NUM_THREADS': '2'})


def orchestrate(args) -> dict:
    repo = Path(__file__).resolve().parents[2]
    target = args.output.resolve()
    if target == repo or target.is_relative_to(repo):
        raise ValueError('C_DEMO_ARTIFACTS_MUST_BE_OUTSIDE_REPO')
    if not args.b_script.is_file():
        raise FileNotFoundError('C_B_FIXTURE_GENERATOR_MISSING')
    # When the B script comes from a real Git checkout, record its exact commit.
    source_root = args.b_script.resolve().parents[2]
    try:
        source_head = subprocess.run(['git', '-C', str(source_root), 'rev-parse', 'HEAD'],
                                     check=True, capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        source_head = 'NOT_GIT_CHECKOUT'
    if len(args.b_ref) == 40 and all(c in '0123456789abcdef' for c in args.b_ref.lower()):
        if source_head != args.b_ref:
            raise ValueError('C_B_CHECKOUT_PIN_MISMATCH')
    target.mkdir(parents=True, exist_ok=True)
    fixture_root = target / 'b_fixtures'
    split_path = target / 'b_split_manifest.csv'
    b_report = target / 'b_quality.json'
    python = sys.executable
    run([python, str(args.b_script), '--make-fixtures', str(fixture_root)])
    run([python, str(args.b_script), '--manifest', str(fixture_root / 'manifest.csv'),
         '--root', str(fixture_root), '--out', str(split_path),
         '--report', str(b_report), '--allow-fixtures'])
    rows = read_verified_split(split_path, fixture_root, demo_fixtures=True)
    if len(rows) != 6:
        raise ValueError('C_B_DEMO_EXPECTS_SIX_CONTRACT_FIXTURES')
    try:
        read_verified_split(split_path, fixture_root)
    except ValueError as exc:
        if 'C_FIXTURE_OR_UNVERIFIED_GROUND_TRUTH' not in str(exc):
            raise
    else:
        raise AssertionError('C_PRODUCTION_DATA_GATE_ACCEPTED_DUMMY')
    record = {
        'data_scope': 'MOCK_ONLY', 'deployment_allowed': False,
        'physical_validation': 'NOT_RUN', 'gazebo_rgb_live': 'NOT_RUN',
        'b_script_sha256': hashlib.sha256(args.b_script.read_bytes()).hexdigest(),
        'b_branch_pin': args.b_ref, 'b_actual_checkout_sha': source_head, 'split_sha256': hashlib.sha256(split_path.read_bytes()).hexdigest(),
        'fixture_summary': summarize(rows), 'contract_gate': 'PASS',
        'training_status': 'NOT_RUN' if args.contract_only else 'RUNNING',
    }
    if not args.contract_only:
        checkpoints = {}
        for phase in ('frozen', 'finetune'):
            checkpoint = target / f'{phase}_MOCK_ONLY.pt'
            report = target / f'{phase}_train_MOCK_ONLY.json'
            cmd = [python, '-m', 'ai.train.train_classifier', '--demo-fixtures',
                   '--root', str(fixture_root), '--split-manifest', str(split_path),
                   '--phase', phase, '--epochs', str(args.epochs),
                   '--batch-size', '2', '--device', 'cpu',
                   '--out', str(checkpoint), '--report', str(report)]
            if phase == 'finetune':
                cmd.extend(['--init-checkpoint', str(checkpoints['frozen'])])
            run(cmd)
            checkpoints[phase] = checkpoint
        eval_path = target / 'independent_test_MOCK_ONLY.json'
        run([python, '-m', 'ai.train.evaluate', '--demo-fixtures',
             '--root', str(fixture_root), '--split-manifest', str(split_path),
             '--checkpoint', str(checkpoints['finetune']), '--report', str(eval_path)])
        # Critical red-team test: ROS production loader must refuse synthetic checkpoint.
        from src.smartdish_ai.smartdish_ai.model_runtime import load_predictor
        try:
            load_predictor(checkpoints['finetune'])
        except ValueError as exc:
            if str(exc) != 'C_MODEL_CONTRACT_MISMATCH':
                raise
        else:
            raise AssertionError('C_PRODUCTION_ROS_ACCEPTED_MOCK_CHECKPOINT')
        import torch
        from PIL import Image
        from ai.evaluation.stability_model import load_checkpoint, predict_pil
        from src.smartdish_ai.smartdish_ai.inference_core import InferenceCore
        model, _ = load_checkpoint(checkpoints['finetune'], allow_mock=True)
        def demo_predict(rgb, width, height):
            return predict_pil(model, Image.frombytes('RGB', (width, height), rgb))
        core = InferenceCore(demo_predict, 'MOCK_ONLY_NON_DEPLOYABLE', confidence_min=0.5)
        outputs = []
        for i, row in enumerate(r for r in rows if r['split'] == 'test'):
            with Image.open(fixture_root / row['image_path']) as im:
                im = im.convert('RGB')
                core.cache_rgb(im.tobytes(), im.width, im.height, received_at=float(i) + 1.)
            req = {'request_id': 'C-MOCK-REQ', 'capture_id': f'C-MOCK-CAP-{i+1}'}
            result = core.handle_request(json.dumps(req), now=float(i) + 1.2)
            if result is None or result['request_id'] != req['request_id'] or result['capture_id'] != req['capture_id']:
                raise AssertionError('C_MOCK_INFERENCE_CONTRACT_MISMATCH')
            outputs.append(result)
        record.update(training_status='MOCK_ONLY_COMPLETE',
                      checkpoints_sha256={phase: hashlib.sha256(path.read_bytes()).hexdigest()
                                         for phase, path in checkpoints.items()},
                      model_evaluation=json.loads(eval_path.read_text()),
                      ros_free_inference_mock_only=outputs,
                      production_runtime_mock_rejected=True)
    output = target / 'c_pipeline_result_MOCK_ONLY.json'
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('C_B_MOCK_ONLY_PIPELINE_PASS ' + json.dumps({
        'contract_gate': record['contract_gate'], 'training': record['training_status'],
        'production_mock_rejected': record.get('production_runtime_mock_rejected'),
        'result_file': str(output)}, sort_keys=True))
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--b-script', type=Path, required=True,
                   help='Read-only B checkout ai/scripts/prepare_dataset.py')
    p.add_argument('--b-ref', default='1bfc19eabe07f2a0ea8c5c8ba3509491c9dd217d')
    p.add_argument('--output', type=Path, default=Path('/tmp/smartdish-c-mock-only'))
    p.add_argument('--epochs', type=int, default=1)
    p.add_argument('--contract-only', action='store_true', help='Check B data split without torch')
    args = p.parse_args()
    if args.epochs < 1:
        p.error('--epochs must be positive')
    orchestrate(args)


if __name__ == '__main__':
    main()
