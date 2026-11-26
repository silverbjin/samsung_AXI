#!/usr/bin/env python3
"""SmartDish B-QA03: A15 OWNER-only, read-only physics intake, never GT approval.

Important: Cloud and synthetic fixture evidence are NEVER substituted for OWNER.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import re
import tarfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from PIL import Image, ImageStat

OWNER_SHA = '828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05'
A15_SHA = '65f0fa6fbf140f8fd2553ce2d8fdf3f515918695'
PLATFORM_SHA = 'b8ef3998973a5e33b67ddd5c5b63c3c89b837840'
SOURCE = 'OWNER_WSL2_A15'
SCENES = ('L15-01', 'L15-02', 'L15-03', 'L15-04')
INNER_SHA = {
 'L15-01':'99dd1d75880f6c9c14b9149da71f70c098b8234a1292c03cf353a162cb0edb77',
 'L15-02':'e22d124764777d1e0bf3c8024557cc00d134d9804425840d6eccddf1c224ec97',
 'L15-03':'fb1dc964c436fb725c1f3f78579dca150b950e1637e9b58014c78a09942e2f25',
 'L15-04':'8c3e1c5569685811f56f501a46b9be596c65707528e6471f3a0d83d2c4662425',
}
EXPECTED_IMAGES = {
 'L15-01':'50eedff06b68a4ec4d1d757cd6963aecedd8f30dbbae1e606bc7836a83d6ad42',
 'L15-02':'807e5ca27f6676e831d83b28e6a8a3c878f0861a577625a1bec1202ee5655dda',
 'L15-03':'05fd7583f730ca444f2fe07be41b6c9aa1b67a417a50999c75b2e321c42fcafe',
 'L15-04':'66d08b531e75d95bde83b11812f58552f1a7ca86f1dbfa84afe6301103b3ddb4',
}
STEP_NS=1_000_000
T0_NS=2_000_000_000
TRIGGER_NS=2_200_000_000
END_NS=12_300_000_000
PULSE_STEPS=500
TORQUE_NM=.12
NAMES=('dish_01','dish_02','tray_platform','camera')
REQUIRED_INNER={'a15_design.json','capture.json','initial_validity.json','verdict.json',
 'scenario.sdf','tray_rgb_t0.png','poses.tsv','trigger.tsv','ecm_contact_steps.tsv',
 'ros_contacts.jsonl','clock_rgb_trace.json'}
HEX64=re.compile(r'^[0-9a-f]{64}$')

class QAError(ValueError): pass

def need(value,code):
    if not value: raise QAError('B_A15_'+code)

def sha(data):return hashlib.sha256(data).hexdigest()

def json_bytes(data,code):
    try:return json.loads(data)
    except (ValueError,UnicodeDecodeError,TypeError) as e:raise QAError('B_A15_'+code) from e

def verify_sidecar(data:bytes,sidecar:bytes,filename:str,expected:str):
    need(sha(data)==expected,'OWNER_OR_INNER_SHA_MISMATCH')
    try: lines=sidecar.decode('utf8').splitlines()
    except UnicodeError as e:raise QAError('B_A15_SIDECAR_ENCODING') from e
    need(len(lines)==1,'SIDECAR_FORMAT')
    m=re.fullmatch(r'([0-9a-f]{64})  ([^\n\r]+)',lines[0])
    need(m is not None and m.group(1)==expected and m.group(2)==filename,'SIDECAR_MISMATCH')

def read_tar(data:bytes,expected:str, *, inner=False):
    """Bounded secure tar read + exact internal manifest. No extractall or links."""
    need(len(data)<400*1024*1024,'COMPRESSED_SIZE_LIMIT')
    need(sha(data)==expected,'ARCHIVE_SHA_MISMATCH')
    files={}; size=0
    try:
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
            for member in tar:
                name=member.name
                p=PurePosixPath(name)
                need(name and not p.is_absolute() and p.as_posix()==name
                     and not any(seg in ('','..','.') for seg in name.split('/'))
                     and '\\' not in name and '\x00' not in name and ':' not in name.split('/')[0], 'TAR_PATH_UNSAFE')
                need(member.isfile() and name not in files and 'approval_ledger.jsonl' not in name.lower(), 'TAR_LINK_DUPLICATE_OR_APPROVAL')
                need(member.size>=0 and member.size<=300*1024*1024,'TAR_MEMBER_LIMIT')
                size+=member.size
                need(size<=800*1024*1024 and len(files)<60,'TAR_TOTAL_LIMIT')
                reader=tar.extractfile(member)
                need(reader is not None,'TAR_READ')
                body=reader.read(member.size+1)
                need(len(body)==member.size,'TAR_SIZE_MISMATCH')
                files[name]=body
    except (tarfile.TarError,OSError,EOFError) as e:
        raise QAError('B_A15_TAR_CORRUPT') from e
    need('SHA256SUMS' in files,'TAR_SHA256SUMS_MISSING')
    manifest=files.pop('SHA256SUMS')
    try:lines=manifest.decode('utf8').splitlines()
    except UnicodeError as e:raise QAError('B_A15_MANIFEST_ENCODING') from e
    hashes={}
    for line in lines:
        m=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        need(m is not None,'MANIFEST_FORMAT')
        filename=m.group(2)
        need(filename not in hashes,'MANIFEST_DUPLICATE')
        hashes[filename]=m.group(1)
    need(hashes=={name:sha(content) for name,content in files.items()},'MANIFEST_CONTENT_SHA')
    need(len(hashes)==(16 if inner else 15),'MANIFEST_COUNT')
    if inner:
        need(REQUIRED_INNER<=set(files),'INNER_REQUIRED_FILE_MISSING')
        need(all('/' not in name for name in files),'INNER_PATH_UNEXPECTED')
    else:
        must={'batch_status.json'}|{f'{scene}/{name}' for scene in SCENES for name in ('a15_raw.tar.gz','a15_raw.tar.gz.sha256')}
        need(must<=set(files),'OUTER_REQUIRED_MISSING')
        need(all(name in must or (re.fullmatch(r'[A-Za-z0-9_\-]+\.log',name) is not None) for name in files),'OUTER_UNLISTED_FILE')
    return files

def xyz(row):
    return tuple(row[k] for k in ('x','y','z'))

def norm_q(row):
    vals=tuple(row[k] for k in ('qx','qy','qz','qw'))
    need(all(math.isfinite(x) for x in vals),'QUATERNION_NONFINITE')
    n=math.sqrt(sum(x*x for x in vals));need(.98<=n<=1.02,'QUATERNION_NORM')
    return tuple(x/n for x in vals)

def q_mul(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)

def q_inv(q):return (-q[0],-q[1],-q[2],q[3])

def rotate(q,v):return q_mul(q_mul(q,(*v,0.)),q_inv(q))[:3]

def relative(tray,dish):
    qt=q_inv(norm_q(tray));q=q_mul(qt,norm_q(dish))
    p=rotate(qt,tuple(a-b for a,b in zip(xyz(dish),xyz(tray))))
    return p,q

def angle(q1,q2):return 2*math.acos(min(1.,abs(sum(a*b for a,b in zip(q1,q2)))))

def read_pose_grid(tsv:bytes,initial:dict,t0=T0_NS,end=END_NS):
    try:fp=io.StringIO(tsv.decode('utf8'))
    except UnicodeError as e:raise QAError('B_A15_POSE_ENCODING') from e
    tracks=defaultdict(dict);ids={}
    for i,r in enumerate(csv.DictReader(fp,delimiter='\t')):
        need(i<100000,'POSE_ROW_LIMIT')
        try:
            t=int(r['sim_ns']); name=r['entity']; eid=int(r['entity_id']); iteration=int(r['iteration'])
            pos={k:float(r[k]) for k in ('x','y','z','qx','qy','qz','qw')}
        except (KeyError,TypeError,ValueError) as e:raise QAError('B_A15_POSE_SCHEMA') from e
        need(name in NAMES and t>0 and t%STEP_NS==0 and eid>0 and t not in tracks[name],'POSE_TIME_ENTITY_DUPLICATE')
        need(all(math.isfinite(v) for v in pos.values()),'POSE_NONFINITE')
        norm_q(pos)
        need(ids.setdefault(name,eid)==eid,'POSE_ENTITY_ID_DRIFT')
        tracks[name][t]=(iteration,pos)
    need(set(tracks)==set(NAMES) and len(set(ids.values()))==4,'POSE_ENTITY_SET')
    for t in range(t0-200_000_000,end+1,STEP_NS):
        need(all(t in tracks[name] for name in NAMES),'POSE_1MS_GRID_GAP')
        iterations={tracks[name][t][0] for name in NAMES}
        need(len(iterations)==1,'POSE_ITERATION_SKEW')
        if t>t0-200_000_000:
            need(tracks['tray_platform'][t][0]==tracks['tray_platform'][t-STEP_NS][0]+1,'POSE_ITERATION_GAP')
    tray0=tracks['tray_platform'][t0][1]
    for t in range(t0,end+1,STEP_NS):
        need(all(abs(tracks['tray_platform'][t][1][k]-v)<1e-8 for k,v in tray0.items()),'TRAY_MOVED_WRONG_PROFILE')
    result={}
    for dish in ('dish_01','dish_02'):
        p0,q0=relative(tray0,tracks[dish][t0][1])
        settle_max=0.;settle_rotate=0.
        for t in range(t0-200_000_000,t0+1,STEP_NS):
            p,q=relative(tracks['tray_platform'][t][1],tracks[dish][t][1])
            settle_max=max(settle_max,math.dist(p,p0))
            settle_rotate=max(settle_rotate,angle(q,q0))
        need(settle_max<=.002+1e-9 and settle_rotate<=.05+1e-8,'PRE_T0_NOT_SETTLED')
        meta=next(x for x in initial['initial_dishes'] if x['name']==dish)
        rad=math.hypot(meta['radius_m'],meta['thickness_m']/2)
        need(abs(p0[0])+rad<=initial['platform']['width_m']/2+1e-8 and
             abs(p0[1])+rad<=initial['platform']['depth_m']/2+1e-8,'INITIAL_OUTSIDE_TRAY')
        prev=None;cum=0.;m=0.;a=0.;min_z=1e9;last=None;onset=None
        for t in range(t0,end+1,STEP_NS):
            p,q=relative(tracks['tray_platform'][t][1],tracks[dish][t][1])
            if prev is not None:cum+=math.dist(p,prev)
            d=math.dist(p0,p);m=max(m,d)
            a=max(a,angle(q0,q));min_z=min(min_z,p[2]);last=p
            if onset is None and t>=TRIGGER_NS and d>.002:onset=t
            prev=p
        result[dish]={'samples':(end-t0)//STEP_NS+1,'settle_max_displacement_m':settle_max,
                      'settle_max_rotation_rad':settle_rotate,'cumulative_relative_path_m':cum,
                      'max_relative_displacement_m':m,'net_relative_displacement_m':math.dist(p0,last),
                      'max_rotation_rad':a,'min_z_m':min_z,'observed_motion_onset_diagnostic_ns':onset,
                      'final_relative_xyz_m':last}
    return result

def read_trigger(body:bytes):
    rows=list(csv.DictReader(io.StringIO(body.decode('utf8')),delimiter='\t'))
    need(len(rows)==PULSE_STEPS,'TRIGGER_COUNT')
    link=None;last_iter=None
    for i,r in enumerate(rows):
        t=int(r['sim_ns']);iteration=int(r['iteration']);torque=float(r['torque_y_nm']);lk=int(r['link_id'])
        need(t==TRIGGER_NS+i*STEP_NS and lk>0 and abs(torque-TORQUE_NM)<1e-12,'TRIGGER_STEP_OR_VALUE')
        if link is None:link=lk
        need(link==lk and (last_iter is None or iteration==last_iter+1),'TRIGGER_LINK_OR_ITERATION')
        last_iter=iteration
    return {'steps':len(rows),'start_ns':TRIGGER_NS,'last_ns':TRIGGER_NS+(PULSE_STEPS-1)*STEP_NS,
            'torque_y_nm_command':TORQUE_NM,'scope':'COMMAND_NOT_MEASURED_WRENCH'}

def pair(a,b):return tuple(sorted((int(a),int(b))))

def read_contact(body:bytes,rosbody:bytes,topics:list[str],start=T0_NS,end=END_NS):
    expected=(end-start)//STEP_NS
    seen=defaultdict(dict);positive=defaultdict(dict);identities={};raw_counts=0;rospairs=defaultdict(set)
    for line in rosbody.splitlines():
        if not line.strip():continue
        r=json_bytes(line,'ROS_CONTACT_JSON');raw_counts+=1
        need(raw_counts<=200000,'ROS_CONTACT_LIMIT')
        t=int(r['sim_time_ns']);topic=r['topic'];need(topic in topics,'ROS_CONTACT_TOPIC')
        if not start<t<=end:continue
        need(r.get('timestamp_source')=='ROS_CONTACT_HEADER_STAMP','ROS_CONTACT_STAMP')
        for p in r.get('contacts',[]):rospairs[(topic,t)].add(pair(p['collision1_id'],p['collision2_id']))
    reader=csv.DictReader(io.StringIO(body.decode('utf8')),delimiter='\t')
    for n,r in enumerate(reader):
        need(n<100000,'ECM_ROW_LIMIT')
        need(r['sim_ns']!='OVERFLOW','ECM_OVERFLOW')
        t=int(r['sim_ns']);topic=r['topic'];need(topic in topics,'ECM_TOPIC')
        if not start<t<=end:continue
        need(t not in seen[topic] and t%STEP_NS==0,'ECM_DUPLICATE_OR_TIME')
        need(r['present']=='1' and r['armed']=='1' and r['late_control']=='0' and
             int(r['dt_ns'])==STEP_NS and r['post_state'] in ('PERIODIC','NO_CHANGE'),'ECM_REFRESH')
        identity=(int(r['sensor_id']),int(r['collision_id']),r['model'],r['sensor'],r['collision'])
        need(identity[0]>0 and identity[1]>0 and identities.setdefault(topic,identity)==identity,'ECM_ID_DRIFT')
        ps={pair(*x.split(':')) for x in r['pairs'].split(';') if x}
        need(len(ps)==int(r['count']) and all(identity[1] in p for p in ps),'ECM_PAIR_COUNT_ID')
        seen[topic][t]=int(r['iteration'])
        if ps:positive[topic][t]=ps
    need(set(seen)==set(topics),'ECM_TOPIC_COVERAGE')
    stats={}
    for topic in topics:
        times=sorted(seen[topic]);need(len(times)==expected,'ECM_WINDOW_LENGTH')
        need(times[0]==start+STEP_NS and times[-1]==end,'ECM_WINDOW_BOUNDARY')
        need(all(t==start+(i+1)*STEP_NS for i,t in enumerate(times)),'ECM_STEP_GAP')
        need(all(seen[topic][b]==seen[topic][a]+1 for a,b in zip(times,times[1:])),'ECM_ITERATION_GAP')
        matches=sum(ps<=rospairs.get((topic,t),set()) for t,ps in positive[topic].items())
        stats[topic]={'steps':len(times),'positive_steps':len(positive[topic]),
                      'empty_steps':len(times)-len(positive[topic]),
                      'matched_positive_steps':matches,'unmatched_positive_steps':len(positive[topic])-matches}
    return {'component_refresh_rows':sum(x['steps'] for x in stats.values()),
            'ros_callbacks':raw_counts,'positive_same_stamp_subset_stats':stats,
            'full_ros_delivery_proven':False,'engine_geometry_registration_proven':False,
            'production_contact_health':'HOLD'}


def geometry_provenance(design:dict):
    dishes=design['initial_dishes']
    need(len(dishes)==2 and [d['name'] for d in dishes]==['dish_01','dish_02'],'DISH_GEOMETRY_SET')
    family_basis={'shape':'cylinder_stack_2',
                  'dimensions':[[d['radius_m'],d['thickness_m']] for d in dishes],
                  'mass':dishes[0]['mass_kg'],'mu':dishes[0]['friction_mu']}
    need(all(d['mass_kg']==family_basis['mass'] and d['friction_mu']==family_basis['mu'] for d in dishes),'MASS_FRICTION_DRIFT')
    family=sha(json.dumps(family_basis,sort_keys=True,separators=(',',':')).encode())
    layout=sha(json.dumps({'family':family,'centers':[[d[k] for k in ('x','y','z')] for d in dishes]},
                          sort_keys=True,separators=(',',':')).encode())
    need(family==design['geometry_family_id'] and layout==design['physical_layout_id'],'GEOMETRY_FAMILY_LAYOUT_HASH_MISMATCH')
    return {'geometry_family_id':family,'physical_layout_id':layout}

def visibility_geometry(pose_bytes:bytes,initial:dict,info:dict,t0=T0_NS):
    """Independently recompute conservative cuboid frustum; not an occlusion mask."""
    observations={}
    for row in csv.DictReader(io.StringIO(pose_bytes.decode('utf8')),delimiter='\t'):
        if int(row['sim_ns'])==t0 and row['entity'] in ('camera','dish_01','dish_02'):
            observations[row['entity']]={k:float(row[k]) for k in ('x','y','z','qx','qy','qz','qw')}
    need(len(observations)==3,'CAMERA_EXACT_T0_POSES_MISSING')
    cam=observations['camera'];cq=q_inv(norm_q(cam));origin=xyz(cam)
    fx,fy,cx,cy=(info['k'][0],info['k'][4],info['k'][2],info['k'][5])
    out={}
    for d in initial['initial_dishes']:
        rad=math.hypot(d['radius_m'],d['thickness_m']/2)
        pos=xyz(observations[d['name']]);pixels=[]
        for dx in (-rad,rad):
            for dy in (-rad,rad):
                for dz in (-rad,rad):
                    local=rotate(cq,tuple(pos[i]+v-origin[i] for i,v in enumerate((dx,dy,dz))))
                    need(local[0]>.05,'CAMERA_DEPTH_NOT_POSITIVE')
                    pixels.append((cx-fx*local[1]/local[0],cy-fy*local[2]/local[0]))
        bounds=[min(x for x,y in pixels),min(y for x,y in pixels),max(x for x,y in pixels),max(y for x,y in pixels)]
        need(0<=bounds[0]<=bounds[2]<640 and 0<=bounds[1]<=bounds[3]<480,'CAMERA_FOV_OUTSIDE')
        recorded=initial.get('dishes',{}).get(d['name'],{}).get('conservative_projected_bbox_px',[])
        need(len(recorded)==4 and all(abs(x-y)<1e-4 for x,y in zip(recorded,bounds)),'CAMERA_FOV_RECALC_MISMATCH')
        out[d['name']]=bounds
    return out

def validate_sdf(body:bytes,design:dict):
    import xml.etree.ElementTree as ET
    try:root=ET.fromstring(body)
    except ET.ParseError as e:raise QAError('B_A15_SDF_XML_INVALID') from e
    sensor=root.find('.//sensor[@name="smartdish_tray_rgb"]')
    need(sensor is not None and sensor.get('type')=='camera','CAMERA_SDF_SENSOR_NOT_FOUND')
    need(sensor.findtext('camera/image/width')=='640' and sensor.findtext('camera/image/height')=='480', 'CAMERA_SDF_IMAGE_SIZE')
    topics={x.findtext('contact/topic') for x in root.findall('.//sensor[@type="contact"]')}
    need(topics==set(design['contact_topics']),'CONTACT_SDF_TOPIC_SET')
    return {'camera_sdf_config_verified':True,'contact_sdf_topics_verified':len(topics)}

def ahash(image):
    pic=image.convert('L').resize((8,8));pix=list(pic.getdata());avg=sum(pix)/64
    return ''.join('1' if v>=avg else '0' for v in pix)

def scene_audit(files,scene):
    design=json_bytes(files['a15_design.json'],'DESIGN_JSON')
    capture=json_bytes(files['capture.json'],'CAPTURE_JSON')
    initial=json_bytes(files['initial_validity.json'],'INITIAL_JSON')
    verdict=json_bytes(files['verdict.json'],'VERDICT_JSON')
    clock=json_bytes(files['clock_rgb_trace.json'],'CLOCK_JSON')
    need(design.get('scene_id')==scene and verdict.get('scene_id')==scene,'SCENE_ID_DRIFT')
    need(design.get('source_sha')==verdict.get('source_sha')==A15_SHA,'SOURCE_SHA_DRIFT')
    need(design.get('physics_profile')=='STATIC_TRAY_COMMON_TORQUE_PILOT','PROFILE_DRIFT')
    need(design.get('ground_truth')=='NOT_OPERATOR_APPROVED' and design.get('human_approved') is False and
         design.get('rule_candidate')=='UNKNOWN' and verdict.get('human_approved') is False and
         verdict.get('ground_truth')=='UNKNOWN_HOLD','GT_AUTO_APPROVAL_FORBIDDEN')
    need(design['stack_id']==design['physical_layout_id'] and bool(design['geometry_family_id']) and
         bool(design['physical_layout_id']) and design['environment_profile_id']=='A15_STATIC_TRAY_OVERHEAD_V1','GEOMETRY_IDENTITIES')
    need(design['world_sha256']==sha(files['scenario.sdf']),'WORLD_SDF_SHA')
    geometry=geometry_provenance(design)
    sdf=validate_sdf(files['scenario.sdf'],design)
    need(design['trigger']['start_ns']==TRIGGER_NS and design['trigger']['duration_ns']==PULSE_STEPS*STEP_NS and
         design['trigger']['torque_nm']==[0,TORQUE_NM,0] and design['trigger']['frame']=='world','TRIGGER_DESIGN')
    need(design['end_ns']==END_NS and design['step_ns']==STEP_NS,'CLOCK_PROFILE')
    need(capture['image_sha256']==sha(files['tray_rgb_t0.png'])==EXPECTED_IMAGES[scene],'PNG_SHA')
    info=capture['camera_info']; t0=int(capture['stamp_ns'])
    need(t0==T0_NS and info['stamp_ns']==t0 and info['width']==640 and info['height']==480 and
         len(info['k'])==9 and info['k'][0]>0 and info['k'][4]>0 and capture['encoding']=='rgb8','RGB_CAMERA_INFO_T0')
    need(verdict.get('data_verdict')=='PASS' and verdict.get('all_owned_stopped') is True,'PRODUCER_DATA_PASS')
    need(verdict.get('cleanup')=='FAIL' and any(x.get('role')=='server' and x.get('returncode')==-11 for x in verdict['processes']),'CLEANUP_FAIL_SEPARATE')
    need(verdict.get('production_contact_health')=='HOLD','CONTACT_HEALTH_MUST_HOLD')
    need(initial.get('capture_ns')==t0 and initial.get('occlusion_review_required') is True and
         initial.get('camera_info_skew_ns')==0,'INITIAL_REVIEW_METADATA')
    need(t0 in clock['frame_stamps'] and max(clock['frame_stamps'])>TRIGGER_NS,'RGB_TIMELINE')
    with Image.open(io.BytesIO(files['tray_rgb_t0.png'])) as image:
        image.load();need(image.format=='PNG' and image.mode=='RGB' and image.size==(640,480),'PNG_FORMAT')
        pixel_hash=sha(image.tobytes());stat=ImageStat.Stat(image);perceptual=ahash(image)
        brightness=sum(stat.mean)/3
    metrics=read_pose_grid(files['poses.tsv'],design,t0=t0)
    visible_bounds=visibility_geometry(files['poses.tsv'],design,info,t0=t0)
    need(all(initial['support'][key]['exact_t0_positive'] is True for key in ('tray_platform__dish_01','dish_01__dish_02')),'INITIAL_SUPPORT_REPORT_NOT_EXACT')
    for d,m in metrics.items():
        emitted=verdict['metrics'][d]
        for computed,producer in [('cumulative_relative_path_m','cumulative_relative_path_m'),
                                  ('max_relative_displacement_m','max_relative_displacement_m'),
                                  ('net_relative_displacement_m','net_relative_displacement_m'),
                                  ('max_rotation_rad','max_rotation_rad')]:
            need(abs(m[computed]-emitted[producer])<2e-7,'METRIC_RECOMPUTE_MISMATCH')
        need(abs(m['settle_max_displacement_m']-initial['dishes'][d]['settle_max_displacement_m'])<2e-7,'SETTLE_RECOMPUTE')
    trigger=read_trigger(files['trigger.tsv'])
    contact=read_contact(files['ecm_contact_steps.tsv'],files['ros_contacts.jsonl'],design['contact_topics'])
    need(contact['ros_callbacks']==verdict['raw_ros_callbacks'],'ROS_CALLBACK_COUNT_DRIFT')
    need(contact['component_refresh_rows']==len(design['contact_topics'])*((END_NS-T0_NS)//STEP_NS),'ECM_COUNT_DRIFT')
    for topic,st in contact['positive_same_stamp_subset_stats'].items():
        reported=verdict['transport'][topic]
        for k in ('steps','positive_steps','matched_positive_steps','empty_steps','unmatched_positive_steps'):
            need(st[k]==reported[k],'ROS_ECM_CROSSCHECK_MISMATCH')
    return {'scene_id':scene,'source_sha':A15_SHA,'archive_sha256':INNER_SHA[scene],
            'trial_id':design['trial_id'],'seed':design['seed'],'stack_id':design['stack_id'],
            'geometry_family_id':design['geometry_family_id'],'physical_layout_id':design['physical_layout_id'],
            'environment_profile_id':design['environment_profile_id'],'image_sha256':capture['image_sha256'],
            'pixel_sha256':pixel_hash,'image_mean_brightness_255':round(brightness,6),'image_ahash64':perceptual,
            'capture_ns':t0,'rgb_resolution':[640,480], 'camera_info_skew_ns':0,
            'geometry_digest_recomputed':geometry,'sdf_config_audit':sdf,
            'conservative_fov_bounds_px':visible_bounds,
            'metrics':metrics,'trigger':trigger,'contact':contact,'gui':verdict['gui'],
            'cleanup':'FAIL','server_rc':-11,'production_contact_health':'HOLD',
            'occlusion_review_required':True,'human_approved':False,'training_eligible':False,
            'ground_truth':'NOT_OPERATOR_APPROVED','rule_candidate':'UNKNOWN',
            'review_status':'REVIEW_REQUIRED'}

def audit_owner(outer:bytes,sidecar:bytes, *, owner_pin=OWNER_SHA, inner_pins=INNER_SHA, expected_images=EXPECTED_IMAGES):
    """Only production wrapper calls this with immutable exact Owner pins."""
    verify_sidecar(outer,sidecar,'a15_pilot_evidence.tar.gz',owner_pin)
    contents=read_tar(outer,owner_pin)
    batch=json_bytes(contents['batch_status.json'],'BATCH_STATUS_JSON')
    need(batch['source_sha']==A15_SHA and batch['exit_code']==0 and
         batch['human_approved'] is False and batch['ground_truth']=='UNKNOWN_HOLD','BATCH_PROVENANCE_GT')
    scenes=[]
    for name in SCENES:
        raw=contents[f'{name}/a15_raw.tar.gz']; side=contents[f'{name}/a15_raw.tar.gz.sha256']
        verify_sidecar(raw,side,'a15_raw.tar.gz',inner_pins[name])
        files=read_tar(raw,inner_pins[name],inner=True)
        scenes.append(scene_audit(files,name))
        need(batch['scenes'][name]['data_verdict']=='PASS','BATCH_SCENE_VERDICT')
    need(len({s['trial_id'] for s in scenes})==4 and len({s['physical_layout_id'] for s in scenes})==4,'LAYOUT_TRIAL_UNIQUENESS')
    fam=defaultdict(list)
    for item in scenes:fam[item['geometry_family_id']].append(item)
    need(len(fam)==2 and sorted(len(v) for v in fam.values())==[2,2],'FAMILY_DIVERSITY_DRIFT')
    need(len({x['pixel_sha256'] for x in scenes})==4 and len({x['image_sha256'] for x in scenes})==4,'EXACT_IMAGE_DUPLICATE')
    near=[]
    for i,x in enumerate(scenes):
        for y in scenes[i+1:]:
            n=sum(a!=b for a,b in zip(x['image_ahash64'],y['image_ahash64']))
            if n<=8:near.append({'pair':[x['scene_id'],y['scene_id']],'ahash_hamming':n,'status':'HUMAN_REVIEW_ONLY'})
    gates={f'B-Q0{i}':'HOLD' for i in range(1,8)};gates['B-Q01']='PASS'
    reasons={
      'B-Q01':['OWNER_RAW_SHA_OUTER_15_AND_INNER_64_VERIFIED','PINNED_OWNER_PROVENANCE'],
      'B-Q02':['RGB_T0_CAMERA_INFO_AND_SUPPORTED_INITIAL_LOADED_PASS','OCCLUSION_HUMAN_QA_REQUIRED','TOP_CAMERA_ONLY'],
      'B-Q03':['POSE_1MS_TRAY_RELATIVE_AND_COMMON_TORQUE_RECOMPUTED','CONTACT_FULL_DELIVERY_AND_ENGINE_REGISTRATION_UNPROVEN','PRODUCTION_CONTACT_HEALTH_HOLD','CLEANUP_FAIL_SEPARATE'],
      'B-Q04':['HUMAN_APPROVED_ZERO','GROUND_TRUTH_UNKNOWN_HOLD'],
      'B-Q05':['ONLY_TWO_GEOMETRY_FAMILIES_FOUR_LAYOUTS','CENTER_OFFSET_SHORTCUT_AND_SINGLE_ENVIRONMENT'],
      'B-Q06':['NO_APPROVED_GROUPED_TRAIN_VAL_TEST','CLOUD_OWNER_SAME_LAYOUT_NOT_INDEPENDENT','NEAR_DUPLICATE_MANUAL_REVIEW'],
      'B-Q07':['NO_OPERATOR_APPROVED_MANIFEST','POST_T0_PHYSICS_FOR_REVIEW_ONLY']}
    return {'schema':1,'scope':'B_QA03_A15_OWNER_RAW_INDEPENDENT_REVIEW_ONLY',
      'actual_owner_raw_directly_recomputed':True,'source_class':SOURCE,'owner_sha256':owner_pin,
      'a15_source_sha':A15_SHA,'platform_baseline_sha':PLATFORM_SHA,
      'outer_manifest_verified':15,'inner_manifests_verified':64,'scenes':scenes,
      'source_independent_family_count':len(fam),'independent_layout_count':4,
      'near_duplicate_review_candidates':near,'cloud_owner_distinct_independent_samples':False,
      'gates':gates,'gate_reasons':reasons,'approved_count':0,'human_approved':False,
      'training_eligible':False,'train_split_exported':False,'model_training_executed':False,
      'product_approval':False,'owner_data_verdict':'PASS', 'owner_gui_verdict':'PASS',
      'owner_cleanup_verdict':'FAIL','contact_production_health':'HOLD',
      'rule_candidate':'UNKNOWN','gt_status':'UNKNOWN_HOLD','note':'No approved 0.015m threshold, no scene-name label inference; exact t0 RGB only future C input.'}

def owner_missing_report():
    return {'schema':1,'scope':'B_QA03_OWNER_RAW_REQUIRED','actual_owner_raw_directly_recomputed':False,
            'source_class':'OWNER_RAW_NOT_AVAILABLE','expected_owner_sha256':OWNER_SHA,
            'gates':{f'B-Q0{i}':'HOLD' for i in range(1,8)},
            'approved_count':0,'training_eligible':False,'train_split_exported':False,
            'model_training_executed':False,'product_approval':False,
            'reason':'B_A15_OWNER_RAW_ARCHIVE_NOT_ATTACHED_OR_NOT_ACCESSIBLE',
            'reference_owner_report_only':True,'reference_not_recomputed':True}

def initial_support(body:bytes,validity:dict,t0=T0_NS):
    window=[]; ids={}
    for r in csv.DictReader(io.StringIO(body.decode('utf8')),delimiter='\t'):
        if r['sim_ns']=='OVERFLOW':raise QAError('B_A15_ECM_OVERFLOW')
        t=int(r['sim_ns'])
        if not t0-50_000_000<=t<=t0:continue
        need(r['present']=='1' and r['armed']=='1','INITIAL_SUPPORT_SENSOR_MISSING')
        cid=int(r['collision_id'])
        need(cid>0 and ids.setdefault(r['model'],cid)==cid,'INITIAL_SUPPORT_ID_DRIFT')
        window.append((t,{pair(*x.split(':')) for x in r['pairs'].split(';') if x}))
    need({'tray_platform','dish_01','dish_02'}<=set(ids),'INITIAL_SUPPORT_ENTITIES')
    for a,b in [('tray_platform','dish_01'),('dish_01','dish_02')]:
        pairid=pair(ids[a],ids[b])
        exact=any(t==t0 and pairid in pairs for t,pairs in window)
        recorded=validity['support'][a+'__'+b]
        need(exact and recorded['exact_t0_positive'] is True and recorded['last_positive_ns']==t0,
             'INITIAL_SUPPORT_EXACT_T0_NOT_PROVEN')
    return {'at_t0_exact_positive_support_pairs':2,'scope':'ECM_COMPONENT_POSITIVE_PAIR_ONLY'}

# Embed the extra evidence in the scene-level record without changing approval scope.
_scene_audit_core=scene_audit
def scene_audit(files,scene):
    result=_scene_audit_core(files,scene)
    result['initial_support']=initial_support(files['ecm_contact_steps.tsv'],
                                                json_bytes(files['initial_validity.json'],'INITIAL_JSON'))
    return result


def review_rows(result):
    """Publicly safe per-scene review worksheet; no decision/label auto-population."""
    if not result.get('actual_owner_raw_directly_recomputed'):return []
    return [{'scene_id':s['scene_id'],'geometry_family_id':s['geometry_family_id'],
             'physical_layout_id':s['physical_layout_id'],'source_image_sha256':s['image_sha256'],
             't0_ns':s['capture_ns'],'observed_dish_02_max_path_m':s['metrics']['dish_02']['cumulative_relative_path_m'],
             'observed_dish_02_max_displacement_m':s['metrics']['dish_02']['max_relative_displacement_m'],
             'visual_occlusion_verified':'','contact_health':'HOLD',
             'human_decision':'','reviewer_id':'','review_reason':'','license_status':'',
             'ground_truth':'NOT_OPERATOR_APPROVED','training_eligible':'false'} for s in result['scenes']]
