#!/usr/bin/env python3
"""B-11 extract *unapproved* RGB/pose/physics candidates and SVG/HTML review material."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
import math
from collections import defaultdict
from pathlib import Path

from import_a13_evidence import EvidenceError, inspect_stage, load_json, sha256, SOURCE_SHA

COLUMNS = ('candidate_id','scene_id','stack_id','trial_id','source_scene_id','seed',
           'source_archive_sha256','source_git_sha','source_image_path','source_image_sha256',
           'physics_path','physics_sha256','physics_size_bytes',
           'width','height','encoding','capture_stamp_ns','pose_at_capture_ns',
           'observation_start_ns','observation_end_ns','pose_samples','dish_count',
           'observation','suggested_label','temporal_review','label_status')


def numeric(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
        raise EvidenceError('B11_NONFINITE_POSE')
    return float(v)


def position(p):
    return [numeric(p[k]) for k in ('x','y','z')]


def pose_quality(p):
    position(p)
    q=[numeric(p[k]) for k in ('qx','qy','qz','qw')]
    if abs(sum(x*x for x in q)-1)>0.08:
        raise EvidenceError('B11_INVALID_QUATERNION')
    numeric(p['tilt_deg'])


def trace_audit(path:Path, entities:set, start_ns:int, end_ns:int):
    series=defaultdict(list)
    for i,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        try: row=json.loads(line)
        except (ValueError,TypeError) as exc:
            raise EvidenceError('B11_JSONL_CORRUPT line='+str(i)) from exc
        if not isinstance(row,dict) or row.get('entity') not in entities:
            raise EvidenceError('B11_UNEXPECTED_ENTITY line='+str(i))
        t=row.get('sim_ns');pose=row.get('pose')
        if type(t)!=int or t<=0 or not isinstance(pose,dict):
            raise EvidenceError('B11_TRACE_INVALID line='+str(i))
        pose_quality(pose)
        name=row['entity']
        if series[name] and t<=series[name][-1]['sim_ns']:
            raise EvidenceError('B11_ENTITY_TIME_REWIND '+name)
        if t>end_ns+500_000_000:
            raise EvidenceError('B11_TRACE_FUTURE_TIMESTAMP')
        series[name].append(row)
    if set(series)!=entities:
        raise EvidenceError('B11_MISSING_DISH_ENTITY')
    if any(not any(start_ns<=x['sim_ns']<=end_ns+500_000_000 for x in events)
           for events in series.values()):
        raise EvidenceError('B11_NO_POST_CAPTURE_PHYSICS')
    return dict(series)


def group_key(scene:dict):
    """Same initial physical geometry yields same group across trial id and minor seed jitter."""
    dishes=scene.get('initial_dishes')
    if not isinstance(dishes,list) or not dishes:
        raise EvidenceError('B11_INITIAL_GEOMETRY_MISSING')
    canonical=[]
    for dish in dishes:
        canonical.append({k:(round(numeric(dish[k]),2) if k!='name' else dish[k])
                          for k in ('name','x','y','z','roll','pitch','radius_m','thickness_m')})
    raw=json.dumps(sorted(canonical,key=lambda x:x['name']),sort_keys=True).encode()
    return 'stack-'+hashlib.sha256(raw).hexdigest()[:16]


def audit_trial(root:Path, trial_name:str, archive_sha:str):
    folder=root/trial_name
    s=load_json(folder/'trial_summary.json')
    scene=load_json(folder/'scenario.scenario.json')
    initial=load_json(folder/'initial_state.json')
    final=load_json(folder/'final_state.json')
    if s.get('trial_id')!=scene.get('trial_id'):
        raise EvidenceError('B11_TRIAL_ID_MISMATCH')
    init=initial.get('dishes',{});last=final.get('dishes',{})
    if set(init)!=set(last) or len(init) not in (2,3):
        raise EvidenceError('B11_DISH_ENTITY_MISMATCH')
    for n in init:
        pose_quality(init[n]);pose_quality(last[n])
    series=trace_audit(folder/'physics_observations.jsonl',set(init),
                       s['observation_start_ns'],s['observation_end_ns'])
    if sum(len(x) for x in series.values())!=s.get('pose_sample_count',sum(len(x) for x in series.values())):
        raise EvidenceError('B11_POSE_SAMPLE_COUNT_MISMATCH')
    configured={x['name']:x for x in scene.get('initial_dishes',[])}
    prefall='PASS'
    if set(configured)!=set(init):
        prefall='TEMPORAL_REVIEW_REQUIRED'
    else:
        top=numeric(scene.get('platform',{}).get('top_z_m',0.57))
        for n in init:
            if numeric(configured[n]['z'])-numeric(init[n]['z'])>0.24 or numeric(init[n]['z'])<top-0.08:
                prefall='TEMPORAL_REVIEW_REQUIRED'
    # A's accepted timing permits 250ms, while latest observed delta was 50ms.
    if abs(s['capture_stamp_ns']-s['pose_at_capture_ns'])>250_000_000:
        prefall='TEMPORAL_REVIEW_REQUIRED'
    observed=s['motion']['observation']
    suggestion={'HELD_OBSERVED':'STABLE','FALL_OBSERVED':'UNSTABLE'}.get(observed)
    if s['observation_end_ns']-s['observation_start_ns']<10_000_000_000:
        prefall='TEMPORAL_REVIEW_REQUIRED'
    if prefall!='PASS' or observed=='INDETERMINATE':
        suggestion='REVIEW_REQUIRED'
    stack=group_key(scene)
    cid='B13-'+hashlib.sha256((archive_sha+'|'+trial_name+'|'+s['image_sha256']).encode()).hexdigest()[:20]
    metrics=[]
    for n in sorted(init):
        x0,y0,z0=position(init[n]); x1,y1,z1=position(last[n])
        metrics.append({'entity':n,'vertical_drop_m_derived':round(z0-z1,4),
                        'xy_displacement_m_derived':round(math.hypot(x1-x0,y1-y0),4),
                        'initial_pose':init[n],'final_pose':last[n],
                        'observed_motion':next((x for x in s['motion']['per_dish'] if x['name']==n),None)})
    result={'candidate_id':cid,'scene_id':'b-'+stack,'stack_id':stack,
            'trial_id':s['trial_id'],'source_scene_id':s['scene_id'],'seed':s['seed'],
            'source_archive_sha256':archive_sha,'source_git_sha':s['source_sha'],
            'source_image_path':f'{trial_name}/tray_rgb.png',
            'source_image_sha256':s['image_sha256'],
            'physics_path':f'{trial_name}/physics_observations.jsonl',
            'physics_sha256':s['physics_sha256'],'physics_size_bytes':s['physics_size_bytes'],
            'width':s['width'],'height':s['height'],'encoding':s['encoding'],
            'capture_stamp_ns':s['capture_stamp_ns'],'pose_at_capture_ns':s['pose_at_capture_ns'],
            'observation_start_ns':s['observation_start_ns'],
            'observation_end_ns':s['observation_end_ns'],
            'pose_samples':sum(len(v) for v in series.values()),'dish_count':len(init),
            'observation':observed,'suggested_label':suggestion,
            'temporal_review':prefall,'label_status':'REVIEW_REQUIRED'}
    detail={'candidate':result,'metrics':metrics,'trace':series,
            'capture_metadata':load_json(folder/'capture_metadata.json'),
            'initial_state':initial,'final_state':final}
    return detail


def make_svg(series, key, mark_ns, start_ns, end_ns, title):
    W,H=720,260; pad=45
    vals=[numeric(r['pose'][key]) for rows in series.values() for r in rows] if key!='xy' else []
    colors=['#146c94','#b64244','#32855c']
    coords=[]
    for i,(entity,rows) in enumerate(sorted(series.items())):
        for r in rows:
            coords.append((r['sim_ns']/1e9, numeric(r['pose']['x' if key=='xy' else key]),
                           numeric(r['pose']['y']) if key=='xy' else 0))
    if not coords:return '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="260"/>'
    xvals=[c[1] for c in coords] if key=='xy' else [c[0] for c in coords]
    yvals=[c[2] for c in coords] if key=='xy' else [c[1] for c in coords]
    xmin,xmax=min(xvals),max(xvals);ymin,ymax=min(yvals),max(yvals)
    if xmin==xmax:xmin-=.1;xmax+=.1
    if ymin==ymax:ymin-=.1;ymax+=.1
    xscale=lambda x:pad+(x-xmin)/(xmax-xmin)*(W-2*pad)
    yscale=lambda y:H-pad-(y-ymin)/(ymax-ymin)*(H-2*pad)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="30" y="22" font-family="sans-serif" font-size="16">{html.escape(title)}</text>',
           f'<path d="M{pad} {pad} V{H-pad} H{W-pad}" fill="none" stroke="#666"/>']
    for i,(name,rows) in enumerate(sorted(series.items())):
        pts=' '.join(f'{xscale(numeric(r["pose"]["x"]) if key=="xy" else r["sim_ns"]/1e9):.1f},{yscale(numeric(r["pose"]["y"]) if key=="xy" else numeric(r["pose"][key])):.1f}' for r in rows)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{colors[i%3]}" stroke-width="1.7"/>')
        parts.append(f'<text x="{W-140}" y="{40+20*i}" fill="{colors[i%3]}" font-family="sans-serif">{html.escape(name)}</text>')
    if key!='xy':
        for t,lab,col in ((mark_ns,'RGB capture','#e06e00'),(start_ns,'Observation start','#6a39ae'),(end_ns,'End','#888')):
            x=xscale(t/1e9);parts.append(f'<path d="M{x:.1f} {pad} V{H-pad}" stroke="{col}" stroke-dasharray="4,3"/>')
    parts.append('</svg>');return ''.join(parts)


def create_review(root:Path, out:Path, archive_sha:str, source_sha=SOURCE_SHA,expected_members=88):
    if out.exists():raise EvidenceError('B11_REVIEW_NO_OVERWRITE')
    receipt=inspect_stage(root,source_sha,expected_members)
    details=[]
    for i in range(1,5):
        details.append(audit_trial(root,f'trial_{i:04d}',archive_sha))
    out.mkdir(parents=True)
    (out/'plots').mkdir()
    with (out/'candidate_manifest.csv').open('w',encoding='utf-8',newline='') as fp:
        writer=csv.DictWriter(fp,fieldnames=COLUMNS);writer.writeheader()
        for d in details:writer.writerow(d['candidate'])
    cards=[]
    for d in details:
        c=d['candidate'];ident=c['candidate_id'];series=d['trace']
        graphs=[]
        for key,label in [('z','Z position (m)'),('tilt_deg','Tilt degrees'),('xy','XY trajectory (m)')]:
            fn=f'{ident}_{key}.svg'
            (out/'plots'/fn).write_text(make_svg(series,key,c['capture_stamp_ns'],c['observation_start_ns'],
                                    c['observation_end_ns'],label),encoding='utf-8')
            graphs.append(fn)
        metrics='<pre>'+html.escape(json.dumps(d['metrics'],ensure_ascii=False,indent=2))+'</pre>'
        cards.append('<section><h2>'+html.escape(ident)+'</h2><p>'+html.escape(c['source_scene_id'])+
                     ' / '+html.escape(c['observation'])+' / '+html.escape(c['temporal_review'])+
                     '</p><img style="max-width:400px" src="../raw/'+html.escape(c['source_image_path'])+'" />'+
                     ''.join('<img style="max-width:700px;display:block" src="plots/'+x+'"/>' for x in graphs)+
                     metrics+'<p>사람 승인: 결정/사유/사용권을 별도 CLI에 수동 입력하세요.</p></section>')
    html_doc='<html><head><meta charset="utf-8"><title>SmartDish B A13 human review</title></head><body><h1>검토 전용: 자동 승인 금지</h1>'+''.join(cards)+'</body></html>'
    (out/'review.html').write_text(html_doc,encoding='utf-8')
    (out/'evidence_audit.json').write_text(json.dumps({'receipt':receipt,'archive_sha256':archive_sha,
                'candidates':[{'candidate':d['candidate'],'metrics':d['metrics']} for d in details]},ensure_ascii=False,indent=2)+'\n')
    return details


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--archive-sha256',required=True);p.add_argument('--expected-members',type=int,default=88)
    a=p.parse_args()
    try:
        details=create_review(a.raw,a.out,a.archive_sha256,expected_members=a.expected_members)
        print('SMARTDISH_B_REAL_CANDIDATE_EXTRACTION_PASS '+str(len(details)))
        print('SMARTDISH_B_PHYSICS_TRACE_AUDIT_PASS')
        print('SMARTDISH_B_LABEL_REVIEW_PACKAGE_READY '+str(a.out/'review.html'))
    except EvidenceError as exc:
        print('B11_CANDIDATE_EXTRACTION_BLOCKED '+str(exc));raise SystemExit(2)

if __name__=='__main__':main()
