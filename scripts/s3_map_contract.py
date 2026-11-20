"""S3 release-map integrity and fixed World->SLAM map-frame contract.

The robot was spawned at (-2.60,-2.20,yaw=0) before the real SLAM run.
SLAM's map frame starts with the robot at (0,0); do not pass World coordinates
from tables.yaml directly to Nav2 map-frame goals.
"""
import hashlib
import json
import math
from pathlib import Path
import yaml

WORLD_PICKUP=(-2.60,-2.20)
WORLD_TABLE3=(2.65,-1.82)
MAP_PICKUP=(0.0,0.0)
MAP_TABLE3=(5.25,0.38)

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_pgm(path):
    raw=Path(path).read_bytes()
    i=0
    def token():
        nonlocal i
        while i<len(raw):
            if raw[i]==35:
                while i<len(raw) and raw[i]!=10:i+=1
            elif raw[i] in (9,10,13,32):i+=1
            else:break
        start=i
        while i<len(raw) and raw[i] not in (9,10,13,32,35):i+=1
        if start==i:raise ValueError('PGM_HEADER_MISSING')
        return raw[start:i].decode('ascii')
    if token()!='P5':raise ValueError('PGM_EXPECTED_BINARY_P5')
    w=int(token());h=int(token());maximum=int(token())
    if maximum!=255 or w<8 or h<8:raise ValueError('PGM_BAD_DIMENSIONS_OR_DEPTH')
    if i>=len(raw) or raw[i] not in (9,10,13,32):
        raise ValueError('PGM_MISSING_PIXEL_SEPARATOR')
    if raw[i]==13 and i+1<len(raw) and raw[i+1]==10:i+=2
    else:i+=1
    pixels=raw[i:]
    if len(pixels)!=w*h:raise ValueError('PGM_PIXEL_LENGTH_MISMATCH')
    return w,h,pixels

def world_to_map(xy):
    return (xy[0]-WORLD_PICKUP[0]+MAP_PICKUP[0],
            xy[1]-WORLD_PICKUP[1]+MAP_PICKUP[1])

def pixel_index(w,h,origin,resolution,xy):
    col=math.floor((xy[0]-origin[0])/resolution)
    grid_row=math.floor((xy[1]-origin[1])/resolution)
    row=h-1-grid_row
    return row*w+col if 0<=col<w and 0<=row<h else None

def nearest_free(w,h,pixels,origin,res,xy,rad_m=.4):
    center=pixel_index(w,h,origin,res,xy)
    if center is None:return None
    row,col=divmod(center,w)
    steps=math.ceil(rad_m/res)
    best=None
    for dy in range(-steps,steps+1):
        for dx in range(-steps,steps+1):
            if dx*dx+dy*dy>(rad_m/res)**2:continue
            xx=col+dx;yy=row+dy
            if xx<0 or xx>=w or yy<0 or yy>=h:continue
            idx=yy*w+xx
            if pixels[idx]>=250:
                dist=dx*dx+dy*dy
                if best is None or dist<best[0]:best=(dist,idx)
    return None if best is None else best[1]

def connected(w,h,pixels,origin,res,from_xy,to_xy):
    from collections import deque
    start=nearest_free(w,h,pixels,origin,res,from_xy)
    goal=nearest_free(w,h,pixels,origin,res,to_xy)
    if start is None or goal is None:return False
    todo=deque([start]);seen={start}
    while todo:
        idx=todo.popleft()
        if idx==goal:return True
        row,col=divmod(idx,w)
        for xx,yy in ((col-1,row),(col+1,row),(col,row-1),(col,row+1)):
            if xx<0 or xx>=w or yy<0 or yy>=h:continue
            nxt=yy*w+xx
            if nxt not in seen and pixels[nxt]>=250:
                seen.add(nxt);todo.append(nxt)
    return False

def validate_release(repo):
    repo=Path(repo)
    root=repo/'maps'
    manifest=json.loads((root/'restaurant_map_manifest.json').read_text())
    quality=json.loads((root/'restaurant_map_quality.json').read_text())
    if manifest['ci_run']!='44551726313':
        raise ValueError('S3_RELEASE_SOURCE_RUN_UNEXPECTED')
    if manifest['source_workflow_sha']!='c6271134c86484154b0df02772e03b981724e15a':
        raise ValueError('S3_RELEASE_SOURCE_SHA_UNEXPECTED')
    if sha256(repo/'src/restaurant_world/worlds/restaurant.sdf')!=manifest['world_sha256']:
        raise ValueError('S3_WORLD_SHA_MISMATCH')
    for name,expected in manifest['files'].items():
        if sha256(root/name)!=expected:raise ValueError('S3_'+name+'_SHA_MISMATCH')
    if quality['map_yaml_sha256']!=manifest['files']['restaurant_map.yaml']:
        raise ValueError('S3_MAP_YAML_CUSTODY_MISMATCH')
    if quality['map_image_sha256']!=manifest['files']['restaurant_map.pgm']:
        raise ValueError('S3_MAP_PGM_CUSTODY_MISMATCH')
    if quality['map']['route_waypoints']!=12 or not quality['map']['pickup_free_connected_to_table3']:
        raise ValueError('S3_MAP_QA_NOT_PASS')
    meta=yaml.safe_load((root/'restaurant_map.yaml').read_text())
    if meta['image']!='restaurant_map.pgm' or meta['mode']!='trinary':
        raise ValueError('S3_MAP_FORMAT_INVALID')
    w,h,pixels=read_pgm(root/'restaurant_map.pgm')
    if w!=quality['map']['width'] or h!=quality['map']['height']:
        raise ValueError('S3_MAP_DIMENSIONS_VS_QA_MISMATCH')
    p=world_to_map(WORLD_PICKUP)
    t=world_to_map(WORLD_TABLE3)
    if math.dist(p,MAP_PICKUP)>.001 or math.dist(t,MAP_TABLE3)>.001:
        raise ValueError('S3_MAP_FRAME_CONTRACT_INVALID')
    origin=meta['origin'];res=float(meta['resolution'])
    if not connected(w,h,pixels,origin,res,p,t):
        raise ValueError('S3_PICKUP_TABLE3_FREE_SPACE_DISCONNECTED')
    return {'release_run':manifest['ci_run'],'width':w,'height':h,
            'pickup_map_xy':p,'table3_map_xy':t,
            'pgm_sha256':manifest['files']['restaurant_map.pgm'],
            'free_connected':True}

if __name__=='__main__':
    import sys
    print('RESTAURANT_S3_SAVED_MAP_FRAME_STATIC_PASS',
          json.dumps(validate_release(sys.argv[1] if len(sys.argv)>1 else '.')))


def validate_s2_map03_candidate(repo):
    """Independent candidate custody; never weakens original S2/S3 release."""
    repo=Path(repo);root=repo/'maps/candidates/s2_map03'
    manifest=json.loads((root/'restaurant_map_manifest.json').read_text())
    quality=json.loads((root/'restaurant_map_quality.json').read_text())
    if manifest['source_ci_run']!='44664079567' or manifest['source_sha']!='ea78fe457e7cfc88754a88f788e08eabd098d766':
        raise ValueError('MAP03_UNEXPECTED_REAL_GAZEBO_SOURCE')
    for name,digest in manifest['files'].items():
        if sha256(root/name)!=digest:
            raise ValueError('MAP03_FILE_HASH_CHANGED_'+name)
    if quality['map_image_sha256']!=manifest['files']['restaurant_map.pgm']:
        raise ValueError('MAP03_IMAGE_CUSTODY_MISMATCH')
    if quality['map_yaml_sha256']!=manifest['files']['restaurant_map.yaml']:
        raise ValueError('MAP03_YAML_CUSTODY_MISMATCH')
    if sha256(repo/'src/restaurant_world/worlds/restaurant.sdf')!=quality['world_sha256']:
        raise ValueError('MAP03_WORLD_CHANGED')
    metric=quality['map']
    if (metric['route_waypoints']!=27 or metric['known']<30394 or
            metric['known_fraction']<.81 or not metric['pickup_free_connected_to_table3']):
        raise ValueError('MAP03_QUALITY_NOT_PROVEN')
    meta=yaml.safe_load((root/'restaurant_map.yaml').read_text())
    if meta['image']!='restaurant_map.pgm' or meta['mode']!='trinary':
        raise ValueError('MAP03_METADATA_INVALID')
    w,h,pixels=read_pgm(root/'restaurant_map.pgm')
    if (w,h)!=(metric['width'],metric['height']):
        raise ValueError('MAP03_DIMENSIONS_CHANGED')
    if not connected(w,h,pixels,meta['origin'],float(meta['resolution']),MAP_PICKUP,MAP_TABLE3):
        raise ValueError('MAP03_PICKUP_TO_TABLE3_DISCONNECTED')
    return {'release_run':manifest['source_ci_run'],'width':w,'height':h,
            'pickup_map_xy':MAP_PICKUP,'table3_map_xy':MAP_TABLE3,
            'pgm_sha256':manifest['files']['restaurant_map.pgm'],'free_connected':True}
