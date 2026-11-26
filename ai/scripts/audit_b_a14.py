#!/usr/bin/env python3
"""B A14 intake: authenticated, offline review only; never produce training labels."""
import argparse,csv,hashlib,io,json,math,re,tarfile
from collections import defaultdict
from pathlib import Path,PurePosixPath
import xml.etree.ElementTree as ET
from PIL import Image,ImageStat

OWNER='3eb140934b814278ccd55a15f1229330426354ca5f2c3966117bca51623b997f'
PINS={'ST-02':('194db1429899775174096e24cde2e785feecda6b','4f4328e6d40ba2936467f4f462364869c2f5662a6d71565d05a9961d4ab4342f'),
      'UN-01':('7c6e950653384cf7c9ac8af58ea849281886a468','05a54b9befb278ce22e7c5b03d9734714e4368e46661bac27817f539a66f265a')}
def need(ok,reason):
    if not ok: raise ValueError(reason)
def sha(b):return hashlib.sha256(b).hexdigest()
def archive(data,expected):
    need(sha(data)==expected,'ARCHIVE_SHA')
    files={};total=0
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
        for m in t:
            n=m.name;p=PurePosixPath(n);total+=m.size
            need(m.isfile() and not p.is_absolute() and p.as_posix()==n and '..' not in p.parts and '\\' not in n and n not in files and 'approval_ledger.jsonl' not in p.parts,'UNSAFE_MEMBER')
            need(0<=m.size<=128*1024*1024 and total<=128*1024*1024 and len(files)<500,'ARCHIVE_LIMIT')
            files[n]=t.extractfile(m).read()
    sums=files.pop('SHA256SUMS');listed={}
    for line in sums.decode().splitlines():
        h,n=line.split('  ',1);need(re.fullmatch('[0-9a-f]{64}',h) and n not in listed,'MANIFEST_FORMAT');listed[n]=h
    need(bool(files) and listed=={n:sha(v) for n,v in files.items()},'MANIFEST_HASH')
    return files

def xyz(d):
    v=tuple(d[k] for k in ('x','y','z'));need(all(type(x) in (float,int) and math.isfinite(x) for x in v),'NONFINITE_POSITION');return v

def track(rows,t0,end,half_width,half_depth):
    ts=[r['sim_time_ns'] for r in rows];need(all(type(t) is int for t in ts) and all(a<b for a,b in zip(ts,ts[1:])),'POSE_TIME')
    pts=[xyz(r['relative']['translation_m']) for r in rows]
    for i,r in enumerate(rows):
        need(r['world_frame_id']=='world' and r['tray_frame_id']=='tray_platform/body' and r['stamp_source']=='ROS_TF_HEADER_STAMP' and r['transform_mode']=='DYNAMIC_DISH_VS_STATIC_TRAY','POSE_FRAME')
        q=r['relative']['quaternion'];need(all(math.isfinite(q[k]) for k in ('w','x','y','z')) and abs(math.sqrt(sum(q[k]**2 for k in ('w','x','y','z')))-1)<.02,'QUATERNION')
        vel=r['velocity'];need(vel['frame_id']=='tray_platform/body','VELOCITY_FRAME')
        if i==0:need(vel['provenance']=='UNAVAILABLE_FIRST_SAMPLE','VELOCITY_FIRST')
        else:
            dt=(ts[i]-ts[i-1])/1e9;need(vel['provenance']=='DERIVED_POSE_FINITE_DIFFERENCE' and abs(vel['dt_seconds']-dt)<1e-9,'VELOCITY_TIME')
            need(math.dist(xyz(vel['linear_m_s']),tuple((a-b)/dt for a,b in zip(pts[i],pts[i-1])))<1e-7,'VELOCITY_VALUE');xyz(vel['angular_rad_s'])
    pre=[i for i,t in enumerate(ts) if t<=t0];post=[i for i,t in enumerate(ts) if t>=t0];need(len(pre)>=2 and len(post)>=2 and ts[-1]<=end,'POSE_COVERAGE')
    i,j=pre[-1],post[0];gap=max(b-a for a,b in zip(ts,ts[1:]));a=pts[i];b=pts[j];outside=abs(a[0])>half_width or abs(a[1])>half_depth
    return dict(samples=len(rows),first_ns=ts[0],last_ns=ts[-1],max_gap_ns=gap,t0_exact=ts[i]==t0,t0_before_ns=ts[i],t0_after_ns=ts[j],pre_t0_center_m=a,post_t0_first_center_m=b,pre_t0_vertical_velocity_m_s=rows[i]['velocity']['linear_m_s']['z'],pre_t0_center_outside_tray=outside,pre_t0_delta_z_m=a[2]-pts[0][2],full_sample_path_m=sum(math.dist(x,y) for x,y in zip(pts,pts[1:])),post_t0_sample_path_m=sum(math.dist(x,y) for x,y in zip(pts[j:],pts[j+1:])),post_t0_sample_span_s=(ts[-1]-ts[j])/1e9,unobserved_end_tail_ns=end-ts[-1],post_t0_sample_drop_m=b[2]-pts[-1][2],last_center_m=pts[-1])

def contacts(ecm,ros,topics,start,end):
    pairs=lambda p:tuple(sorted(p))
    raw=defaultdict(set);callbacks=0
    for r in ros:
        callbacks+=1;need(r['topic'] in topics and r['timestamp_source']=='ROS_CONTACT_HEADER_STAMP','ROS_CONTACT_SCHEMA')
        raw[(r['topic'],r['sim_time_ns'])].update(pairs((p['collision1_id'],p['collision2_id'])) for p in r['contacts'])
    grouped=defaultdict(list)
    for r in csv.DictReader(io.StringIO(ecm.decode()),delimiter='\t'):
        t=int(r['sim_ns'])
        if start<t<=end:grouped[r['topic']].append(r)
    need(set(grouped)==set(topics),'ECM_TOPICS');out={}
    for topic,rows in grouped.items():
        need(len(rows)==(end-start)//1000000 and all(int(r['sim_ns'])==start+(i+1)*1000000 and int(r['dt_ns'])==1000000 and r['present']=='1' and r['armed']=='1' and r['late_control']=='0' and r['post_state'] in ('NO_CHANGE','PERIODIC') for i,r in enumerate(rows)),'ECM_STEP_REFRESH')
        need(len({(r['sensor_id'],r['collision_id'],r['model'],r['sensor'],r['collision']) for r in rows})==1 and all(int(b['iteration'])==int(a['iteration'])+1 for a,b in zip(rows,rows[1:])),'ECM_ID_OR_ITERATION')
        pos=matched=0
        for r in rows:
            ps={pairs(tuple(map(int,s.split(':')))) for s in r['pairs'].split(';') if s};need(bool(ps)==(int(r['count'])>0),'ECM_PAIR_COUNT')
            pos+=bool(ps);matched+=bool(ps and ps==raw[(topic,int(r['sim_ns']))])
        out[topic]=dict(steps=len(rows),positive_steps=pos,empty_steps=len(rows)-pos,matched_positive_steps=matched,unmatched_positive_steps=pos-matched)
    return {'refresh_rows':sum(x['steps'] for x in out.values()),'raw_callbacks':callbacks,'transport':out,'scope':'COMPONENT_REFRESH_AND_EXACT_POSITIVE_MATCH_ONLY'}

def scene_audit(data,scene,pin,digest):
    f=archive(data,digest);prefix='trial_0001/'
    def b(n):return f[prefix+n]
    def j(n):return json.loads(b(n))
    def jl(n):return [json.loads(x) for x in b(n).splitlines()]
    q,s,c,g,h,cam,summary,cleanup=[j(n) for n in ('a14_gt_candidate.json','scenario.scenario.json','capture_metadata.json','geometry_layout.json','r02_3_health_result.json','camera_pose_metadata.json','trial_summary.json','process_cleanup.json')]
    need(q['source_sha']==h['source_sha']==summary['source_sha']==cleanup['source_sha']==cam['source_git_sha']==json.loads(f['source_manifest.json'])['source_sha']==pin,'SOURCE_PIN')
    need(q['scene_id']==s['scene_id']==g['scene_id']==h['scene_id']==summary['scene_id']==cleanup['scenario_id']==scene and q['trial_id']==s['trial_id']==c['trial_id']==g['trial_id']==summary['trial_id'] and q['stack_id']==s['stack_id'] and q['seed']==s['seed']==g['seed']==summary['seed'],'IDENTITY')
    need(q['human_approved'] is False and h['human_approved'] is False and q['ground_truth']=='NOT_OPERATOR_APPROVED' and q['rule_candidate']=='UNKNOWN' and q['label_status']=='REVIEW_REQUIRED' and c['label'] is None,'GT_BOUNDARY')
    need(q['physics_profile']==g['physics_profile']==s['a14_profile']=='STATIC_GRAVITY','PROFILE')
    t0,start,end=q['rgb_t0_sim_time_ns'],q['observation_start_ns'],q['observation_end_ns'];need(t0==c['stamp_ns']==h['capture_ns']==summary['capture_stamp_ns']<start==h['start_ns']<end==h['end_ns'] and end-start>=10_000_000_000,'WINDOW')
    need(c['pre_observation_capture'] is True and c['pre_observation_spawn_sim_ns']<t0,'CAPTURE_PHASE')
    for name,expected in [('tray_rgb.png',q['rgb_image_sha256']),('physics_observations.jsonl',q['original_a13_physics_sha256']),('scenario.sdf',q['world_sdf_sha256']),('camera_pose_metadata.json',q['camera_pose_metadata_sha256']),('ecm_contact_steps.tsv',h['ecm_sha256']),('r02_3_ros_contacts.jsonl',h['raw_ros_sha256']),('r02_3_clock_samples.json',h['clock_samples_sha256']),('sensor_preflight.sdf',h['runtime_world_sha256'])]+[(n+('.json' if n=='r02_3_health_result' else '.jsonl'),v) for n,v in q['evidence_sha256'].items()]:need(sha(b(name))==expected,'LINKED_HASH_'+name)
    need(c['image_sha256']==q['rgb_image_sha256'] and c['encoding']=='rgb8','RGB_METADATA')
    with Image.open(io.BytesIO(b('tray_rgb.png'))) as im:
        im.load();need(im.format=='PNG' and im.mode=='RGB' and im.size==(640,480),'RGB_FORMAT');stat=ImageStat.Stat(im);image=dict(size=list(im.size),pixel_sha256=sha(im.tobytes()),mean_brightness=sum(stat.mean)/3,std_brightness=sum(stat.stddev)/3)
    sensor=ET.fromstring(b('sensor_preflight.sdf')).find('.//sensor[@name="smartdish_tray_rgb"]');need(sensor is not None and sensor.findtext('pose')==cam['camera_pose_configuration'] and sensor.findtext('camera/image/width')=='640' and sensor.findtext('camera/image/height')=='480','CAMERA_CONFIG')
    tray={};by=defaultdict(list)
    for tr in jl('tray_pose_timeline.jsonl'):
        t=tr['sim_time_ns'];need(t not in tray or tray[t]==tr,'TRAY_DUPLICATE_CONFLICT');tray[t]=tr
        need(all(abs(tr['pose'][k]-v)<1e-8 for k,v in [('qx',0),('qy',0),('qz',0),('qw',1)]),'STATIC_TRAY_ORIENTATION')
    for r in jl('physics_observations_v2.jsonl'):
        tr=tray[r['sim_time_ns']];need(tr['transform_mode']=='STATIC_TRAY' and tr['world_sdf_sha256']==q['world_sdf_sha256'],'TRAY_POSE')
        need(math.dist(xyz(r['relative']['translation_m']),tuple(a-b for a,b in zip(xyz(r['pose']),xyz(tr['pose']))))<1e-8,'RELATIVE_TRANSLATION');by[r['entity']].append(r)
    need(set(by)=={d['name'] for d in g['dishes']}=={d['name'] for d in s['initial_dishes']},'DISH_SET')
    metrics={k:track(v,t0,end,g['geometry']['tray_width_m']/2,g['geometry']['tray_depth_m']/2) for k,v in by.items()}
    for k,v in metrics.items():need(abs(v['full_sample_path_m']-q['per_dish'][k]['cumulative_relative_distance_m'])<1e-8,'A_PATH_RECOMPUTE')
    health=contacts(b('ecm_contact_steps.tsv'),jl('r02_3_ros_contacts.jsonl'),s['a14_contact_topics'],start,end);need(health['transport']==h['transport'] and h['integration_evidence_pass'] is True and h['production_contact_health']=='HOLD','A_CONTACT_RECOMPUTE')
    issues=['STATIC_CAMERA_TF_NOT_MEASURED','NO_EXACT_T0_POSE','PRODUCTION_CONTACT_HEALTH_HOLD','GT_NOT_APPROVED','NO_GEOMETRY_FAMILY_OR_LAYOUT_ID']
    if any(v['pre_t0_center_outside_tray'] for v in metrics.values()):issues.append('PRE_T0_CENTER_OUTSIDE_TRAY')
    if any(v['pre_t0_delta_z_m']<-.01 for v in metrics.values()):issues.append('PRE_T0_DOWNWARD_MOTION_DIAGNOSTIC_GT_NOT_INFERRED')
    if any(v['unobserved_end_tail_ns']>0 for v in metrics.values()):issues.append('POSE_TAIL_NOT_COVERED')
    return dict(issues=issues,scene_id=scene,source_sha=pin,archive_sha256=digest,manifest_count=len(f),trial_id=s['trial_id'],stack_id=s['stack_id'],seed=s['seed'],image=image,capture_ns=t0,observation_s=(end-start)/1e9,camera_scope=cam['dynamic_camera_tf_status'],geometry_family_id=g['geometry_family_id'],physical_layout_id=g['physical_layout_id'],physics_profile=q['physics_profile'],metrics=metrics,contact=health,observation=q['observation'],gui=summary['gui_verdict'],cleanup_exit_codes=[x['returncode_after_cleanup'] for x in cleanup['owned_processes']],production_contact_health='HOLD',rule_candidate='UNKNOWN',human_approved=False,training_eligible=False)

def audit(data):
    f=archive(data,OWNER);out=[]
    for scene,(pin,digest) in PINS.items():out.append(scene_audit(f[scene+'/production_raw.tar.gz'],scene,pin,digest))
    need(len({s['trial_id'] for s in out})==len(out),'DUPLICATE_TRIAL')
    return dict(schema=1,scope='OWNER_STATIC_GRAVITY_REVIEW_ONLY',owner_sha256=OWNER,owner_manifest_count=len(f),scenes=out,exact_pixel_duplicate=len({s['image']['pixel_sha256'] for s in out})!=len(out),gates={'B-Q01':'PASS','B-Q02':'HOLD','B-Q03':'HOLD','B-Q04':'HOLD','B-Q05':'HOLD','B-Q06':'HOLD','B-Q07':'HOLD'},gate_reasons={'B-Q01':'Pinned outer and nested source/archive/linked hashes verified','B-Q02':'Static camera config only; t0 pose not exact; UN-01 already outside tray and falling','B-Q03':'Relative pose/derived velocity/component refresh verified; full contact health HOLD and pose tail missing','B-Q04':'No human approval; rule candidate UNKNOWN','B-Q05':'Two smoke scenes, one static environment, no geometry family IDs; obvious shortcut','B-Q06':'No exact pixel duplicates in two scenes only; no independent group split','B-Q07':'No approved manifest or split; post-t0 physics is review only'},approved_count=0,training_ready=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--owner',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    need(a.owner.is_file() and not a.owner.is_symlink() and a.owner.stat().st_size<=128*1024*1024,'INPUT_FILE')
    result=audit(a.owner.read_bytes())
    with a.out.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print('B_A14_REVIEW_COMPLETE_GT_HOLD')
if __name__=='__main__':main()
