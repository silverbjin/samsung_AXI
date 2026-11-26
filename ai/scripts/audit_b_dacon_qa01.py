#!/usr/bin/env python3
"""B-DATA-QA-01: offline, read-only evidence audit against user-supplied DACON baseline v1.0.

PASS means the *specific gate* is proven, not that the dataset is released.
Never generates labels, approves data, trains a model, or treats 0.015 m as policy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import tarfile
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from PIL import Image, ImageStat, ImageOps

A13_SHA = 'bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e'
A13_SOURCE_SHA = '6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df'
BASELINE_ID = 'SMARTDISH_B_DACON_DATA_QUALITY_BASELINE_20261125_KO_v1.0'
SCENES = {'ST-01','ST-02','UN-01','UN-02'}
FIELDS = ('candidate_id','source_scene_id','trial_id','seed','stack_id',
          'suggested_label','label_status','source_image_path','source_image_sha256',
          'physics_path','physics_sha256','source_archive_sha256','source_git_sha',
          'capture_stamp_ns','pose_at_capture_ns','observation_start_ns',
          'observation_end_ns','width','height','encoding')
MAX_MEMBER_BYTES = 160*1024*1024
MAX_TOTAL_BYTES = 600*1024*1024

class QAError(ValueError): pass

def sha_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def safe_file(root: Path, rel: str) -> Path:
    if not isinstance(rel,str) or not rel or '\\' in rel or '\x00' in rel:
        raise QAError('B_QA_UNSAFE_RELATIVE_PATH')
    p=PurePosixPath(rel)
    if p.is_absolute() or any(x in ('','.','..') for x in rel.split('/')) or ':' in rel.split('/')[0]:
        raise QAError('B_QA_UNSAFE_RELATIVE_PATH')
    path=root.joinpath(*p.parts)
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise QAError('B_QA_FILE_NOT_REGULAR_OR_MISSING '+rel)
    return path

def verified_archive(path: Path) -> dict:
    """Verify full A13 TAR without extracting. Never accepts a diagnostic subset as Q01."""
    if not path.is_file() or path.is_symlink():
        raise QAError('B_Q01_ORIGINAL_TAR_NOT_FOUND')
    digest = sha_file(path)
    if digest != A13_SHA:
        raise QAError('B_Q01_ORIGINAL_ARCHIVE_SHA_MISMATCH')
    seen = {}; total = 0
    try:
        with tarfile.open(path, 'r:gz') as t:
            for m in t:
                n=m.name
                if n.startswith('/') or any(x in ('','.','..') for x in n.split('/')) or '\\' in n or n in seen or not m.isfile():
                    raise QAError('B_Q01_TAR_MEMBER_UNSAFE')
                if m.size<0 or m.size>MAX_MEMBER_BYTES: raise QAError('B_Q01_MEMBER_TOO_LARGE')
                total+=m.size
                if total>MAX_TOTAL_BYTES or len(seen)>512: raise QAError('B_Q01_ARCHIVE_LIMIT')
                h=hashlib.sha256(); stream=t.extractfile(m)
                if stream is None: raise QAError('B_Q01_TAR_FILE_UNREADABLE')
                if n=='SHA256SUMS': sums=stream.read(m.size)
                else:
                    for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
                    seen[n]=h.hexdigest()
    except (tarfile.TarError, OSError, EOFError) as exc: raise QAError('B_Q01_ARCHIVE_CORRUPT') from exc
    try:
        listed={}
        for line in sums.decode('utf-8').splitlines():
            match=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
            if not match or match.group(2) in listed: raise QAError('B_Q01_SUMS_INVALID')
            listed[match.group(2)] = match.group(1)
    except (UnicodeError,UnboundLocalError) as exc: raise QAError('B_Q01_SUMS_MISSING') from exc
    if seen != listed: raise QAError('B_Q01_INTERNAL_SHA_MISMATCH')
    return {'source_archive_sha256':digest,'verified_members':len(seen),'status':'PASS','_member_sha256':seen}

def load_csv(path: Path) -> list[dict]:
    with path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        rows=list(reader)
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):
            raise QAError('B_QA_CSV_SCHEMA_INVALID')
    return rows

def load_json(path: Path):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError, OSError) as exc: raise QAError('B_QA_JSON_INVALID '+path.name) from exc

def image_stats(path: Path) -> dict:
    try:
        with Image.open(path) as image:
            image.load()
            if image.format!='PNG' or image.mode!='RGB' or image.size!=(640,480):
                raise QAError('B_Q02_INPUT_FORMAT_MISMATCH')
            stat=ImageStat.Stat(image)
            gray=ImageOps.grayscale(image).resize((8,8), Image.Resampling.BILINEAR)
            values=list(gray.get_flattened_data() if hasattr(gray,'get_flattened_data') else gray.getdata());mean=sum(values)/64
            phash=''.join('1' if x>mean else '0' for x in values)
            return {'width':image.width,'height':image.height,'mode':image.mode,
                    'mean_brightness_0_255':round(sum(stat.mean)/3,3),
                    'std_brightness_0_255':round(sum(stat.stddev)/3,3),
                    'pixel_sha256':sha_bytes(image.tobytes()),'ahash64':phash}
    except (OSError, ValueError) as exc: raise QAError('B_Q02_IMAGE_DECODE_FAILED') from exc

def distance(a,b): return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))

def finite_pose(p):
    if not isinstance(p,dict):raise QAError('B_Q03_POSE_MISSING')
    v=[]
    for key in ('x','y','z'):
        n=p.get(key)
        if isinstance(n,bool) or not isinstance(n,(float,int)) or not math.isfinite(n):
            raise QAError('B_Q03_NONFINITE_POSITION')
        v.append(float(n))
    return v

def trace_metrics(path: Path, observation_start_ns: int, capture_ns:int) -> dict:
    """World-frame-only movement diagnostics, NOT tray-relative GT evidence."""
    series=defaultdict(list)
    for line in path.read_text(encoding='utf-8').splitlines():
        try:row=json.loads(line)
        except (ValueError,TypeError) as exc:raise QAError('B_Q03_TRACE_JSON_INVALID') from exc
        ts=row.get('sim_ns');name=row.get('entity')
        if type(ts)!=int or ts<0 or not isinstance(name,str) or not name.startswith('dish_'):
            raise QAError('B_Q03_TRACE_SCHEMA_INVALID')
        point=finite_pose(row.get('pose'))
        if series[name] and series[name][-1][0]>=ts:raise QAError('B_Q03_TIME_NONMONOTONIC')
        series[name].append((ts,point,row))
    if not series:raise QAError('B_Q03_TRACE_EMPTY')
    out=[]; all_gaps=[]
    for name,events in sorted(series.items()):
        post=[e for e in events if e[0]>=capture_ns]
        if len(post)<2:raise QAError('B_Q03_POST_CAPTURE_INSUFFICIENT')
        pts=[e[1] for e in post]
        cum=sum(distance(a,b) for a,b in zip(pts,pts[1:]))
        gaps=[(b[0]-a[0])/1e9 for a,b in zip(post,post[1:])]
        all_gaps.extend(gaps)
        out.append({'entity':name,'samples_total':len(events),'post_capture_samples':len(post),
                    'first_post_s':post[0][0]/1e9,'last_post_s':post[-1][0]/1e9,
                    'cumulative_world_m':round(cum,6),'net_world_m':round(distance(pts[0],pts[-1]),6),
                    'max_inter_sample_gap_s':round(max(gaps),6),
                    'has_tray_relative_pose':all('tray_relative_pose' in e[2] for e in post),
                    'has_velocity':all('velocity' in e[2] for e in post),
                    'has_contact':all('contact' in e[2] for e in post)})
    return {'entities':out,'max_cumulative_world_m':max(x['cumulative_world_m'] for x in out),
            'max_gap_s':max(all_gaps),'has_tray_relative_pose':all(x['has_tray_relative_pose'] for x in out),
            'has_velocity':all(x['has_velocity'] for x in out),
            'has_contact':all(x['has_contact'] for x in out),
            'movement_frame':'WORLD_DIAGNOSTIC_ONLY','observation_start_s':observation_start_ns/1e9}

def verified_camera_sdf_members(archive:Path, member_sha256:dict) -> dict[str,bytes]:
    """Return camera configuration from the already SHA-verified *full* A13 TAR.

    B15/B12R diagnostic subsets intentionally omit SDF. They must not trigger
    a false claim that A never captured the camera's configured sensor pose.
    Individual SDF bytes are checked against the same verified A13 member index.
    """
    names=[f'trial_{n:04d}/sensor_preflight.sdf' for n in range(1,5)]
    output={}
    try:
        with tarfile.open(archive,'r:gz') as stream:
            for name in names:
                expected=member_sha256.get(name)
                if not expected:
                    continue
                member=stream.getmember(name)
                if not member.isfile() or not 0 < member.size <= 2*1024*1024:
                    raise QAError('B_Q02_CAMERA_SDF_MEMBER_INVALID '+name)
                handle=stream.extractfile(member)
                if handle is None:
                    raise QAError('B_Q02_CAMERA_SDF_UNREADABLE '+name)
                data=handle.read(member.size+1)
                if len(data)!=member.size or sha_bytes(data)!=expected:
                    raise QAError('B_Q02_CAMERA_SDF_HASH_DRIFT '+name)
                output[name]=data
    except (OSError,tarfile.TarError,KeyError,EOFError) as exc:
        raise QAError('B_Q02_CAMERA_SDF_SOURCE_UNREADABLE') from exc
    return output


def camera_sdf(root:Path, trial:str, authenticated_sdf:bytes|None=None) -> dict:
    """A configuration pose is not a live dynamic TF/calibration measurement."""
    try:
        if authenticated_sdf is not None:
            xml=ET.fromstring(authenticated_sdf)
            origin='VERIFIED_A13_TAR_SENSOR_PREFLIGHT_SDF'
        else:
            path=safe_file(root,f'{trial}/sensor_preflight.sdf')
            xml=ET.parse(path).getroot()
            origin='RAW_SENSOR_PREFLIGHT_SDF_NOT_SOURCE_ARCHIVE_REVERIFIED'
        sensor=xml.find('.//sensor[@name="smartdish_tray_rgb"]')
        if sensor is None:return {'camera_pose_source':'MISSING'}
        image=sensor.find('camera/image')
        pose=sensor.findtext('pose')
        return {'camera_pose_source':origin,'camera_pose_sdf':pose,
                'camera_pose_scope':'STATIC_SENSOR_SDF_LOCAL_POSE_NOT_OBSERVED_DYNAMIC_TF',
                'sdf_width':image.findtext('width') if image is not None else None,
                'sdf_height':image.findtext('height') if image is not None else None,
                'topic_sdf':sensor.findtext('topic'),
                'frame_id_sdf':sensor.findtext('gz_frame_id')}
    except (QAError,ET.ParseError,ValueError):return {'camera_pose_source':'MISSING'}

def review_ledger(path: Path, candidates: set[str]) -> dict:
    if not path.is_file():return {'approved':0,'decisions':0,'pending':len(candidates),'integrity':'NOT_PRESENT'}
    seen=set();counts=Counter()
    for line in path.read_text(encoding='utf-8').splitlines():
        try:row=json.loads(line)
        except ValueError as exc:raise QAError('B_Q04_APPROVAL_LEDGER_INVALID') from exc
        signature=row.pop('record_sha256',None)
        expected=sha_bytes(json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
        if signature!=expected or row.get('candidate_id') not in candidates or row['candidate_id'] in seen:
            raise QAError('B_Q04_APPROVAL_LEDGER_INVALID')
        seen.add(row['candidate_id']);counts[row.get('decision','UNKNOWN')]+=1
        if row.get('decision')=='APPROVED' and (row.get('approved_label') not in ('STABLE','UNSTABLE') or row.get('license_status') not in ('OWNED','AUTHORIZED')):
            raise QAError('B_Q04_APPROVAL_INCOMPLETE')
    return {'approved':counts['APPROVED'],'decisions':len(seen),
            'pending':len(candidates)-len(seen),'integrity':'VERIFIED'}

def csv_write(path:Path, rows:list[dict], fields):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def hash_group_leakage(rows:list[dict]) -> dict:
    """Read-only cross-split collision detection. Near duplicates remain review-required."""
    by_scene=defaultdict(set);by_stack=defaultdict(set);by_sha=defaultdict(set);by_pixel=defaultdict(set)
    for r in rows:
        split=r['split'];by_scene[r['source_scene_id']].add(split);by_stack[r['stack_id']].add(split)
        by_sha[r['source_image_sha256']].add(split)
        if r.get('pixel_sha256'):by_pixel[r['pixel_sha256']].add(split)
    return {'scene_overlaps':sorted(k for k,v in by_scene.items() if len(v)>1),
            'stack_overlaps':sorted(k for k,v in by_stack.items() if len(v)>1),
            'file_sha_overlaps':sorted(k for k,v in by_sha.items() if len(v)>1),
            'pixel_sha_overlaps':sorted(k for k,v in by_pixel.items() if len(v)>1)}

def stage_audit(raw:Path,review:Path,out:Path, *, source_archive:Path|None=None,
                baseline:Path|None=None, split_manifest:Path|None=None,release_manifest:Path|None=None) -> dict:
    """All content is private; only explicit output in a new directory is written."""
    raw=raw.resolve();review=review.resolve();out=out.absolute()
    if not raw.is_dir() or not review.is_dir():raise QAError('B_QA_SOURCE_WORKSPACE_MISSING')
    if out.exists() or out==raw or out==review or out.is_relative_to(raw) or out.is_relative_to(review):
        raise QAError('B_QA_OUTPUT_EXISTS_OR_UNSAFE')
    candidate_file=safe_file(review,'candidate_manifest.csv')
    candidates=load_csv(candidate_file)
    if not candidates or len(candidates)>10000 or len({r.get('candidate_id') for r in candidates})!=len(candidates):
        raise QAError('B_QA_CANDIDATE_SET_INVALID')
    if not set(FIELDS).issubset(candidates[0]):raise QAError('B_QA_CANDIDATE_SCHEMA_INVALID')
    provenance={'status':'HOLD','reason':'B_Q01_ORIGINAL_TAR_NOT_PROVIDED'}
    if source_archive is not None:
        try:provenance=verified_archive(source_archive)
        except QAError as exc: provenance={'status':'HOLD','reason':str(exc)}
    source_member_sha=provenance.pop('_member_sha256',{})
    camera_source_sdf=(verified_camera_sdf_members(source_archive,source_member_sha)
                       if source_archive is not None and provenance['status']=='PASS' else {})
    ledger=review_ledger(review/'approval_ledger.jsonl',{r['candidate_id'] for r in candidates})
    all_samples=[];image_rows=[];physics_rows=[];camera_rows=[];duplicates=[];thumbnail_paths=[]
    errors={x:[] for x in range(1,8)}
    for r in candidates:
        cid=r['candidate_id'];scene=r['source_scene_id'];trial=PurePosixPath(r['source_image_path']).parts[0]
        if not re.fullmatch(r'B13-[0-9a-f]{20}',cid) or r['suggested_label'] not in ('STABLE','UNSTABLE','REVIEW_REQUIRED'):
            raise QAError('B_QA_CANDIDATE_ID_OR_LABEL_INVALID')
        if scene not in SCENES: errors[5].append('B_Q05_UNKNOWN_SCENE')
        if r['source_archive_sha256']!=A13_SHA or r['source_git_sha']!=A13_SOURCE_SHA:
            errors[1].append('B_Q01_PROVENANCE_MISMATCH')
        if r.get('label_status')!='REVIEW_REQUIRED':errors[4].append('B_Q04_CANDIDATE_LABEL_ALREADY_CHANGED')
        image=safe_file(raw,r['source_image_path']);physics=safe_file(raw,r['physics_path'])
        if source_member_sha and (source_member_sha.get(r['source_image_path'])!=r['source_image_sha256'] or
                                  source_member_sha.get(r['physics_path'])!=r['physics_sha256']):
            errors[1].append('B_Q01_CANDIDATE_NOT_BOUND_TO_VERIFIED_TAR')
        if sha_file(image)!=r['source_image_sha256'] or sha_file(physics)!=r['physics_sha256']:
            raise QAError('B_QA_CANDIDATE_SHA_DRIFT '+cid)
        im_stat=image_stats(image)
        if [str(im_stat['width']),str(im_stat['height']),r['encoding']]!=[r['width'],r['height'],'rgb8']:
            errors[2].append('B_Q02_DIMENSION_METADATA_MISMATCH')
        capture=load_json(safe_file(raw,trial+'/capture_metadata.json'))
        ts=load_json(safe_file(raw,trial+'/trial_summary.json'))
        scenario=load_json(safe_file(raw,trial+'/scenario.scenario.json'))
        if ts.get('source_sha')!=A13_SOURCE_SHA or ts.get('scene_id')!=scene or capture.get('stamp_ns')!=int(r['capture_stamp_ns']):
            errors[1].append('B_Q01_TRIAL_METADATA_DRIFT')
        if capture.get('encoding')!='rgb8' or capture.get('width')!=640 or capture.get('height')!=480:
            errors[2].append('B_Q02_CAMERA_METADATA_MISMATCH')
        t0=int(r['capture_stamp_ns']);pose=int(r['pose_at_capture_ns'])
        if t0<=0 or abs(t0-pose)>250_000_000 or int(r['observation_end_ns'])-int(r['observation_start_ns'])<10_000_000_000:
            errors[2].append('B_Q02_TIME_ALIGNMENT_OR_DURATION')
        cam=camera_sdf(raw,trial,camera_source_sdf.get(f'{trial}/sensor_preflight.sdf'))
        if not cam.get('camera_pose_sdf'):errors[2].append('B_Q02_CAMERA_POSE_MISSING')
        elif cam.get('sdf_width')!='640' or cam.get('sdf_height')!='480' or cam.get('topic_sdf')!=capture.get('topic') or cam.get('frame_id_sdf')!=capture.get('frame_id'):
            errors[2].append('B_Q02_CAMERA_SDF_CAPTURE_CONFIG_MISMATCH')
        trace=trace_metrics(physics,int(r['observation_start_ns']),t0)
        if not trace['has_tray_relative_pose'] or not trace['has_velocity'] or not trace['has_contact']:
            errors[3].append('B_Q03_TRAY_RELATIVE_VELOCITY_CONTACT_MISSING')
        img_row={'candidate_id':cid,'scene_id':scene,'suggested_label':r['suggested_label'],
                 'source_image_sha256':r['source_image_sha256'],**im_stat}
        image_rows.append(img_row)
        for entity in trace['entities']:
            physics_rows.append({'candidate_id':cid,'scene_id':scene,**entity})
        camera_rows.append({'candidate_id':cid,'scene_id':scene,'capture_s':t0/1e9,
                            'pose_at_capture_s':pose/1e9,'delta_s':round(abs(t0-pose)/1e9,5),
                            'frame_id':capture.get('frame_id'),'source_topic':capture.get('topic'),
                            **cam})
        all_samples.append({'candidate_id':cid,'source_scene_id':scene,'stack_id':r['stack_id'],
                            'trial_id':r['trial_id'],'suggested_label':r['suggested_label'],
                            'human_label_approved':'UNKNOWN','source_git_sha':r['source_git_sha'],
                            'source_archive_sha256':r['source_archive_sha256'],
                            'image_sha256':r['source_image_sha256'],'pixel_sha256':im_stat['pixel_sha256'],
                            'capture_s':t0/1e9,'last_observed_s':float(r['observation_end_ns'])/1e9,
                            'max_cumulative_world_translation_m_DIAGNOSTIC_ONLY':trace['max_cumulative_world_m'],
                            'world_max_gap_s':trace['max_gap_s']})
        thumbnail_paths.append((cid,scene,image))
    for i,a in enumerate(image_rows):
        for b in image_rows[i+1:]:
            dist=sum(x!=y for x,y in zip(a['ahash64'],b['ahash64']))
            if a['source_image_sha256']==b['source_image_sha256'] or a['pixel_sha256']==b['pixel_sha256'] or dist<=5:
                duplicates.append({'left_id':a['candidate_id'],'right_id':b['candidate_id'],
                                   'exact_file':a['source_image_sha256']==b['source_image_sha256'],
                                   'exact_pixels':a['pixel_sha256']==b['pixel_sha256'],
                                   'ahash_hamming':dist,'verdict':'REVIEW_REQUIRED_NOT_AUTO_DUPLICATE'})
    by_class=Counter(r['suggested_label'] for r in candidates)
    by_scene=Counter(r['source_scene_id'] for r in candidates)
    coverage=[{'scenario':s,'suggested_label':label,'n_candidates':sum(r['source_scene_id']==s and r['suggested_label']==label for r in candidates),
               'environment_profile':'GAZEBO_FIXED_TRAY_RGB_ONLY','geometry_family':'UNANNOTATED',
               'human_label_approved':False} for s in sorted(SCENES) for label in ('STABLE','UNSTABLE')]
    split={'status':'NOT_PRESENT','cross_split_collisions':'NOT_TESTED','near_duplicate_review':'NOT_DONE'}
    if split_manifest is not None:
        if not split_manifest.is_file(): errors[6].append('B_Q06_SPLIT_MANIFEST_MISSING')
        else:
            actual=load_csv(split_manifest)
            required={'candidate_id','split','source_scene_id','stack_id','source_image_sha256'}
            if not actual or not required.issubset(actual[0]):errors[6].append('B_Q06_SPLIT_SCHEMA_MISMATCH')
            else:
                allowed={'train','val','test'}
                if any(r['split'] not in allowed for r in actual):errors[6].append('B_Q06_SPLIT_INVALID')
                seen_pixel={x['candidate_id']:x['pixel_sha256'] for x in image_rows}
                for row in actual:row['pixel_sha256']=seen_pixel.get(row['candidate_id'])
                overlaps=hash_group_leakage(actual)
                split={'status':'PROVIDED','cross_split_collisions':overlaps,'near_duplicate_review':'NOT_DONE'}
                if any(overlaps.values()):errors[6].append('B_Q06_CROSS_SPLIT_LEAKAGE')
    if ledger['approved']<len(candidates):errors[4].append('B_Q04_HUMAN_APPROVAL_INCOMPLETE')
    # An approved human label alone cannot replace a validated independent GT rule.
    errors[4].append('B_Q04_INDEPENDENT_TRAY_RELATIVE_GT_RULE_NOT_VERIFIED')
    errors[3].append('B_Q03_RULE_VERSION_AND_TRAY_DYNAMIC_TRACE_NOT_APPROVED')
    errors[2].append('B_Q02_OCCLUSION_VISUAL_QA_NOT_SIGNED')
    errors[5].append('B_Q05_GEOMETRY_ENVIRONMENT_CROSS_COVERAGE_NOT_DEMONSTRATED')
    advisory=[]
    if len(candidates)<60: advisory.append('B_Q05_PILOT_60_SCENES_NONBINDING_RECOMMENDATION_GAP')
    if split['status']!='PROVIDED':errors[6].append('B_Q06_SPLIT_NOT_PRESENT')
    errors[6].append('B_Q06_NEAR_DUPLICATE_REVIEW_NOT_SIGNED')
    if release_manifest is None or not release_manifest.is_file():errors[7].append('B_Q07_APPROVED_C_RELEASE_NOT_PRESENT')
    if ledger['approved']<len(candidates):errors[7].append('B_Q07_UNAPPROVED_INPUT_FORBIDDEN')
    errors[7].append('B_Q07_MODEL_REPRO_AND_INPUT_GROUND_TRUTH_SEPARATION_NOT_VERIFIED')
    if provenance['status']!='PASS':errors[1].append(provenance.get('reason','B_Q01_PROVENANCE_HOLD'))
    gates={f'B-Q{i:02d}':{'status':'PASS' if not errors[i] else 'HOLD',
                         'reasons':sorted(set(errors[i]))} for i in range(1,8)}
    # Protect upstream release boundary: this QA is a test of data and never emits a train split.
    result={'schema':1,'task':'B-DATA-QA-01','baseline_id':BASELINE_ID,
            'baseline_sha256':sha_file(baseline) if baseline and baseline.is_file() else None,
            'baseline_v1_user_approval':'NOT_YET_APPROVED',
            'data_release_ready':False,'overall':'HOLD' if any(x['status']=='HOLD' for x in gates.values()) else 'REVIEW_REQUIRED',
            'training_executed':False,'automatic_label_approval':False,'human_approval':ledger,
            'candidate_count':len(candidates),'candidate_suggested_counts':dict(by_class),
            'unique_scenarios':len(by_scene),'scene_counts':dict(by_scene),
            'source_archive_audit':provenance,'gates':gates,'nonbinding_advisories':advisory,
            'dacon_comparison':{'image_reference':'384x384 RGB front+top; product raw stays 640x480 single camera',
                                'reference_train_scenes':1000,'reference_dev_scenes':100,'reference_test_scenes':1000,
                                'reference_dev_test_exact_duplicate_note':'100 Dev scenes duplicate 100 Test scenes by front/top hashes per supplied baseline',
                                'source_dacon_audit_zip_independently_reverified':False,
                                'candidate_observation_s':10,
                                'candidate_cumulative_m':0.015,
                                'candidate_threshold_product_approved':False},
            'observability':{'actual_tray_relative_vel_contact':'NOT_AVAILABLE',
                             'world_pose_metrics_are_labels':False,'visual_occlusion_human_review':'PENDING',
                             'camera_sdf_static_pose_not_dynamic_tf':True,
                             'geometry_family_annotation':'NOT_AVAILABLE','temporal_pre_fall':'CHECK_REQUIRED'},
            'split_audit':split,'near_duplicate_pair_count':len(duplicates)}
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.b-qa-stage-',dir=out.parent) as tmp:
        stage=Path(tmp)
        (stage/'qa_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        csv_write(stage/'sample_manifest_qa.csv',all_samples,all_samples[0].keys())
        csv_write(stage/'image_stats.csv',image_rows,image_rows[0].keys())
        csv_write(stage/'physics_trace_metrics.csv',physics_rows,physics_rows[0].keys())
        csv_write(stage/'camera_metadata.csv',camera_rows,camera_rows[0].keys())
        csv_write(stage/'duplicate_summary.csv',duplicates,('left_id','right_id','exact_file','exact_pixels','ahash_hamming','verdict'))
        csv_write(stage/'class_geometry_environment_coverage.csv',coverage,coverage[0].keys())
        csv_write(stage/'split_overlap.csv',[{'kind':k,'values':json.dumps(v)} for k,v in split.get('cross_split_collisions',{}).items()]
                   if isinstance(split.get('cross_split_collisions'),dict) else [],('kind','values'))
        # A product camera contact sheet; not labelled and never auto-approved.
        sheet=Image.new('RGB',(640,560),'white')
        for i,(cid,scene,path) in enumerate(thumbnail_paths[:4]):
            with Image.open(path) as image: thumb=ImageOps.contain(image.convert('RGB'),(315,245))
            x=(i%2)*320; y=(i//2)*280
            sheet.paste(thumb,(x,y))
        sheet.save(stage/'representative_product_camera_4_scenes.png')
        guide='''# B-DATA-QA-01 — DACON 기준 기반 실제 데이터 품질 감사\n\n본 파일은 사람이 정답을 승인한 모델 학습 데이터가 아닙니다.\n\n- `qa_report.json`: B-Q01~07 PASS/HOLD 원장\n- `sample_manifest_qa.csv`: 후보/출처/세계 좌표계 거리(진단 전용)\n- `image_stats.csv`: RGB brightness/file SHA/pixel SHA/near-duplicate aHash\n- `camera_metadata.csv`: 원본 A13 TAR SDF(있는 경우)의 정적 센서 설정 포즈와 t0/pose 시간차; 동적 TF는 별도\n- `physics_trace_metrics.csv`: world pose time/cumulative/net distance (NOT tray-relative)\n- `duplicate_summary.csv`: exact/near candidates, near matches require human review\n- `class_geometry_environment_coverage.csv`: label suggestion x scene x environment, NOT accepted GT\n- `split_overlap.csv`: split provided then cross-split hash/geometry duplicates\n- `representative_product_camera_4_scenes.png`: 제품 단일 카메라 4개 후보 시트\n\nDACON 제안 0.015m는 제품의 최종 GT 임계치가 아니며, 누적 world movement는 tray-relative GT가 아닙니다.\nB-13 approval ledger 및 C 학습은 자동 실행하지 않습니다.\n'''
        (stage/'README_QA_KO.md').write_text(guide,encoding='utf-8')
        sums=[f'{sha_file(f)}  {f.relative_to(stage).as_posix()}' for f in sorted(stage.rglob('*')) if f.is_file()]
        (stage/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
        os.rename(stage,out)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-dir',type=Path,required=True)
    p.add_argument('--review-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-archive',type=Path)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--split-manifest',type=Path)
    p.add_argument('--release-manifest',type=Path)
    args=p.parse_args()
    try:
        result=stage_audit(args.raw_dir,args.review_dir,args.output,source_archive=args.source_archive,
                           baseline=args.baseline,split_manifest=args.split_manifest,
                           release_manifest=args.release_manifest)
    except (QAError,OSError,ValueError,KeyError,TypeError) as exc:
        print('B_DATA_QA01_BLOCKED '+str(exc));raise SystemExit(2)
    print('B_DATA_QA01_AUDIT_COMPLETED '+str(args.output))
    for gate,info in result['gates'].items():
        print(f"{gate}={info['status']}" + (' reasons='+','.join(info['reasons']) if info['reasons'] else ''))
    print('B_DATA_QA01_DATASET_HOLD' if result['overall']=='HOLD' else 'B_DATA_QA01_REVIEW_REQUIRED')

if __name__=='__main__':main()
