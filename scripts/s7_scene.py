#!/usr/bin/env python3
"""S7 static startup dish scene: opt-in generated world, never rewrite S5 map.

S7 starts with dishes already on TABLE_3. It reuses the S6 fixture geometry,
which previously was spawned only after reaching the table.
"""
import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from s6_scene import FIXTURE_WORLD_XY, TABLE3_WORLD_XY, fixture_sdf

SCENARIOS=('stacked','empty')
NAME='s6_stacked_dishes'

def validate_world(world,scenario):
    if scenario not in SCENARIOS:raise ValueError('S7_INVALID_SCENARIO')
    root=world if isinstance(world,ET.Element) else ET.fromstring(world)
    worlds=root.findall('./world')
    if len(worlds)!=1 or worlds[0].get('name')!='restaurant':
        raise ValueError('S7_EXPECTED_RESTAURANT_WORLD')
    w=worlds[0]
    table=w.find("./model[@name='table_3']")
    if table is None:raise ValueError('S7_TABLE3_MISSING')
    pose=[float(x) for x in table.findtext('pose','').split()]
    if len(pose)<2 or abs(pose[0]-TABLE3_WORLD_XY[0])>.001 or abs(pose[1]-TABLE3_WORLD_XY[1])>.001:
        raise ValueError('S7_TABLE3_COORDINATE_DRIFT')
    models=w.findall("./model[@name='"+NAME+"']")
    expect=1 if scenario=='stacked' else 0
    if len(models)!=expect:raise ValueError('S7_FIXTURE_COUNT_MISMATCH')
    if models:
        m=models[0]
        if m.findtext('static')!='true':raise ValueError('S7_DISH_NOT_STATIC')
        p=[float(x) for x in m.findtext('pose','').split()]
        if len(p)!=6 or abs(p[0]-FIXTURE_WORLD_XY[0])>.001 or abs(p[1]-FIXTURE_WORLD_XY[1])>.001:
            raise ValueError('S7_FIXTURE_POSE_MISMATCH')
        if len(m.findall('./link/visual'))!=6:raise ValueError('S7_DISH_VISUAL_COUNT_MISMATCH')
    return root

def build_world(original,scenario):
    if scenario not in SCENARIOS:raise ValueError('S7_INVALID_SCENARIO')
    root=ET.fromstring(original)
    # Verify the base world is the original empty restaurant. Never duplicate.
    validate_world(root,'empty')
    if scenario=='stacked':
        w=root.find('./world')
        dish=ET.fromstring(fixture_sdf()).find('./model')
        if dish is None:raise ValueError('S7_DISH_SDF_MISSING')
        pos=ET.Element('pose')
        pos.text=f'{FIXTURE_WORLD_XY[0]} {FIXTURE_WORLD_XY[1]} 0 0 0 0'
        dish.insert(0,pos)
        w.append(dish)
    validate_world(root,scenario)
    return '<?xml version="1.0"?>\n'+ET.tostring(root,encoding='unicode')+'\n'

def generate(source,out,scenario):
    source,out=Path(source),Path(out)
    if not source.is_file():raise ValueError('S7_WORLD_SOURCE_MISSING')
    original=source.read_text(encoding='utf-8')
    rendered=build_world(original,scenario)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(rendered,encoding='utf-8')
    validate_world(out.read_text(encoding='utf-8'),scenario)
    record={'schema':1,'scenario':scenario,'world_name':'restaurant',
            'fixture_count':int(scenario=='stacked'),'spawn_stage':'WORLD_FILE_AT_GAZEBO_START',
            'source_sha256':hashlib.sha256(original.encode()).hexdigest(),
            'world_sha256':hashlib.sha256(rendered.encode()).hexdigest(),
            'source_file':str(source),'output_file':str(out),
            'goal_sent':False}
    (out.parent/(out.stem+'.manifest.json')).write_text(
        json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print('S7_STARTUP_WORLD_GENERATED_NO_GOAL='+scenario+' '+record['world_sha256'],flush=True)
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--scenario',choices=SCENARIOS,required=True)
    a=p.parse_args()
    generate(a.source,a.out,a.scenario)
