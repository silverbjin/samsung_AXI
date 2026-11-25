#!/usr/bin/env python3
"""B-10 fail-closed, read-only A13 TAR provenance verifier (no extraction via tarfile.extractall)."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

SOURCE_SHA = '6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df'
ARCHIVE_SHA = 'bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e'
EXPECTED_SCENES = ('ST-01','ST-02','UN-01','UN-02')
SHA_PATTERN = re.compile(r'^[0-9a-f]{64}$')
MAX_MEMBERS, MAX_MEMBER, MAX_TOTAL = 512, 160 * 1024 * 1024, 600 * 1024 * 1024

class EvidenceError(ValueError):
    pass


def fail(code):
    raise EvidenceError(code)


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def safe_name(name):
    p = PurePosixPath(name)
    if (not name or name.startswith('/') or '\\' in name or '\x00' in name
            or p.is_absolute() or name.startswith('./') or any(x in ('.','..','') for x in name.split('/'))
            or ':' in name.split('/')[0]):
        fail('B10_ARCHIVE_UNSAFE_PATH')
    return str(p)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (UnicodeError, ValueError, OSError) as exc:
        raise EvidenceError('B10_JSON_INVALID ' + path.name) from exc


def check_trial(root, name, source_sha):
    from PIL import Image
    folder=root/name
    necessary=('scenario.scenario.json','tray_rgb.png','capture_metadata.json',
               'initial_state.json','physics_observations.jsonl',
               'final_state.json','trial_summary.json','process_cleanup.json')
    for filename in necessary:
        if not (folder/filename).is_file() or not (folder/filename).stat().st_size:
            fail('B10_TRIAL_FILE_MISSING '+name+'/'+filename)
    trial=load_json(folder/'trial_summary.json')
    cap=load_json(folder/'capture_metadata.json')
    scene=load_json(folder/'scenario.scenario.json')
    initial=load_json(folder/'initial_state.json')
    final=load_json(folder/'final_state.json')
    cleanup=load_json(folder/'process_cleanup.json')
    if (trial.get('source_sha')!=source_sha or trial.get('scene_id') not in EXPECTED_SCENES
            or trial.get('trial_id')!=scene.get('trial_id') or trial.get('seed')!=scene.get('seed')):
        fail('B10_TRIAL_PROVENANCE_MISMATCH '+name)
    if (trial.get('image_received_count',len(trial.get('image_stamp_samples',[])))!=len(trial.get('image_stamp_samples',[]))
            or trial.get('sensor_physics_verdict')!='PASS' or trial.get('gui_verdict')!='PASS'
            or trial.get('gui_active_during_physics') is not True
            or cleanup.get('all_owned_processes_stopped') is not True):
        fail('B10_TRIAL_NOT_ACCEPTED '+name)
    if (trial.get('label')!='REVIEW_REQUIRED' or trial.get('ground_truth')!='NOT_OPERATOR_APPROVED'
            or cap.get('ground_truth')!='NOT_OBSERVED'):
        fail('B10_UNAPPROVED_LABEL_CHANGED '+name)
    if (trial.get('image_sha256')!=sha256(folder/'tray_rgb.png')
            or cap.get('image_sha256')!=trial['image_sha256']):
        fail('B10_IMAGE_SHA_MISMATCH '+name)
    physics=folder/'physics_observations.jsonl'
    if (trial.get('physics_sha256')!=sha256(physics)
            or trial.get('physics_size_bytes')!=physics.stat().st_size):
        fail('B10_PHYSICS_SHA_MISMATCH '+name)
    try:
        with Image.open(folder/'tray_rgb.png') as image:
            image.verify()
        with Image.open(folder/'tray_rgb.png') as image:
            if image.format!='PNG' or image.mode!='RGB' or image.size!=(640,480):
                fail('B10_PNG_FORMAT_MISMATCH '+name)
    except (OSError, SyntaxError) as exc:
        raise EvidenceError('B10_PNG_CORRUPT '+name) from exc
    stamp=trial.get('capture_stamp_ns'); pose=trial.get('pose_at_capture_ns')
    start=trial.get('observation_start_ns'); end=trial.get('observation_end_ns')
    stamps=trial.get('image_stamp_samples')
    if (any(type(v)!=int for v in (stamp,pose,start,end)) or stamp<=0
            or start<stamp or end-start<9_000_000_000 or abs(stamp-pose)>250_000_000
            or not isinstance(stamps,list) or len(stamps)<3
            or any(type(v)!=int or v<=0 for v in stamps)
            or any(a>=b for a,b in zip(stamps,stamps[1:]))
            or stamps[0]>start):
        fail('B10_TEMPORAL_CONTRACT_FAIL '+name)
    if (not isinstance(initial.get('dishes'),dict) or
            not isinstance(final.get('dishes'),dict) or
            set(initial['dishes'])!=set(final['dishes'])):
        fail('B10_DISH_ENTITY_MISMATCH '+name)
    if trial.get('motion',{}).get('observation') not in ('HELD_OBSERVED','FALL_OBSERVED','INDETERMINATE'):
        fail('B10_PHYSICS_OBSERVATION_INVALID '+name)
    return trial


def inspect_stage(stage:Path, expected_sha=SOURCE_SHA, expected_count=88):
    names={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
    mandatory={'summary.json','source_manifest.json','deployment_gate_manifest.json','SHA256SUMS'}
    if not mandatory<=names:
        fail('B10_MANIFEST_REQUIRED_MISSING')
    s=load_json(stage/'summary.json'); src=load_json(stage/'source_manifest.json')
    gate=load_json(stage/'deployment_gate_manifest.json')
    if (s.get('mode')!='batch' or s.get('gui') is not True
            or s.get('verdict')!='GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS'
            or s.get('first_error') is not None or s.get('source_sha')!=expected_sha
            or src.get('source_sha')!=expected_sha or gate.get('source_sha')!=expected_sha
            or gate.get('status')!='REAL_WSLG_SMOKE_PASS'
            or gate.get('gui_preflight',{}).get('verdict')!='GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR'
            or gate.get('smoke',{}).get('verdict')!='REAL_WSLG_SMOKE_PASS'
            or not SHA_PATTERN.fullmatch(str(gate.get('smoke',{}).get('archive_sha256','')))):
        fail('B10_A13_RELEASE_MANIFEST_MISMATCH')
    entries=[]; seen=set()
    for line in (stage/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        if '  ' not in line:
            fail('B10_SHA256SUMS_INVALID')
        sig, name=line.split('  ',1)
        safe_name(name)
        if not SHA_PATTERN.fullmatch(sig) or name in seen:
            fail('B10_SHA256SUMS_DUPLICATE_OR_INVALID')
        seen.add(name);entries.append((sig,name))
    if expected_count is not None and len(entries)!=expected_count:
        fail('B10_INTERNAL_COUNT_MISMATCH')
    if seen != names-{'SHA256SUMS'}:
        fail('B10_INTERNAL_FILE_SET_MISMATCH')
    for sig,name in entries:
        if sha256(stage/name)!=sig:
            fail('B10_INTERNAL_SHA_MISMATCH '+name)
    trials=s.get('trials')
    if not isinstance(trials,list) or len(trials)!=4:
        fail('B10_TRIAL_COUNT_MISMATCH')
    output=[]
    for i,listed in enumerate(trials,1):
        trial=check_trial(stage,f'trial_{i:04d}',expected_sha)
        if (listed!=trial or trial.get('scene_id')!=EXPECTED_SCENES[i-1]
                or listed.get('source_sha')!=expected_sha):
            fail('B10_TRIAL_SUMMARY_MISMATCH')
        output.append(trial)
    return {'status':'B_REAL_EVIDENCE_IMPORT_PASS','source_sha':expected_sha,
            'verified_files':len(entries),'trial_count':len(output),
            'scenes':[x['scene_id'] for x in output],'trials':output,
            'ground_truth_approved':False}


def import_archive(archive:Path, output:Path, expected_sha=SOURCE_SHA,
                   expected_archive=ARCHIVE_SHA, expected_count=88):
    """Verify before publishing. Private output must not exist; preserve archive byte-for-byte."""
    archive=Path(archive).expanduser().resolve();output=Path(output).expanduser().resolve()
    if not archive.is_file():
        fail('A13_ARCHIVE_BYTES_NOT_AVAILABLE')
    if output.exists():
        fail('B10_NO_OVERWRITE_OUTPUT')
    if not SHA_PATTERN.fullmatch(expected_archive) or sha256(archive)!=expected_archive:
        fail('B10_ARCHIVE_SHA_MISMATCH')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.b-a13-import-',dir=output.parent) as temp:
        stage=Path(temp)
        try:
            with tarfile.open(archive,'r:gz') as tar:
                infos=[]
                for info in tar:
                    if len(infos)>=MAX_MEMBERS:
                        fail('B10_ARCHIVE_MEMBER_LIMIT')
                    infos.append(info)
                names=set();total=0
                for info in infos:
                    name=safe_name(info.name)
                    if name in names:
                        fail('B10_ARCHIVE_DUPLICATE_MEMBER')
                    names.add(name)
                    if not info.isfile():
                        fail('B10_ARCHIVE_LINK_OR_SPECIAL_FORBIDDEN')
                    if info.size<=0 or info.size>MAX_MEMBER:
                        fail('B10_ARCHIVE_MEMBER_SIZE_INVALID')
                    total+=info.size
                    if total>MAX_TOTAL:
                        fail('B10_ARCHIVE_TOTAL_SIZE_LIMIT')
                for info in infos:
                    dest=stage/info.name
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    read=tar.extractfile(info)
                    if read is None:
                        fail('B10_ARCHIVE_MEMBER_MISSING')
                    count=0
                    with dest.open('xb') as out:
                        for part in iter(lambda:read.read(1024*1024),b''):
                            count+=len(part)
                            if count>info.size:fail('B10_ARCHIVE_STREAM_OVERFLOW')
                            out.write(part)
                    if count!=info.size:
                        fail('B10_ARCHIVE_TRUNCATED_MEMBER')
        except (tarfile.TarError,EOFError,OSError) as exc:
            raise EvidenceError('B10_ARCHIVE_MALFORMED') from exc
        report=inspect_stage(stage,expected_sha,expected_count)
        report['archive_sha256']=expected_archive
        for p in stage.rglob('*'):
            if p.is_file():p.chmod(0o444)
        # Only verified evidence is promoted to the private workspace.
        os.rename(stage,output)
        return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-archive-sha256',default=ARCHIVE_SHA)
    p.add_argument('--expected-source-sha',default=SOURCE_SHA)
    p.add_argument('--expected-members',type=int,default=88)
    args=p.parse_args()
    try:
        report=import_archive(args.archive,args.output,args.expected_source_sha,
                              args.expected_archive_sha256,args.expected_members)
        print('SMARTDISH_B_A13_ARCHIVE_SHA_PASS')
        print('SMARTDISH_B_A13_INTERNAL_HASH_PASS verified='+str(report['verified_files']))
        print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    except EvidenceError as exc:
        print('B_EVIDENCE_IMPORT_BLOCKED '+str(exc))
        raise SystemExit(2)

if __name__=='__main__':
    main()
