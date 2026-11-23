#!/usr/bin/env python3
"""S6 compact supervised image classifier for controlled Gazebo dish fixtures.

A learned two-prototype RGB feature model, NOT a general object detector.
Training must use actual labeled camera PPMs. No synthetic PASS or retraining
inside navigation; a missing/ambiguous model returns UNKNOWN and blocks return.
"""
import argparse,hashlib,json,math
from pathlib import Path

LABELS=('NOT_STACKED','STACKED')
FEATURES=3
def read_ppm(path):
    raw=Path(path).read_bytes()
    if not raw.startswith(b'P6\n'):raise ValueError('S6_MODEL_REQUIRES_BINARY_RGB_PPM')
    parts=raw.split(b'\n',3)
    if len(parts)!=4 or parts[2].strip()!=b'255':
        raise ValueError('S6_UNSUPPORTED_PPM_HEADER')
    w,h=(int(x) for x in parts[1].split())
    data=parts[3]
    if w<16 or h<16 or len(data)!=w*h*3:
        raise ValueError('S6_INVALID_TRAINING_RGB_SHAPE')
    return (w,h,data)

def features(rgb,w,h):
    """Three learned plate-stack cues: blue rim area, horizontal layer runs, height.

    Spatially robust to small Nav2 stopping pose differences. Only trained
    for a synthetic blue-rim dish fixture; other dish colors remain UNKNOWN.
    """
    if len(rgb)!=w*h*3 or w<16 or h<16:raise ValueError('S6_RGB_DIMENSIONS')
    rows=[]
    blue_count=0
    min_row=None;max_row=None
    per_row_threshold=max(4,int(w*.02))
    for y in range(15,h-15):
        row_count=0
        for x in range(8,w-8):
            i=(y*w+x)*3
            r,g,b=rgb[i],rgb[i+1],rgb[i+2]
            if b>r*1.30 and b>g*1.10 and b>75:
                row_count+=1
                blue_count+=1
                min_row=y if min_row is None else min(min_row,y)
                max_row=y if max_row is None else max(max_row,y)
        if row_count>=per_row_threshold:rows.append(y)
    runs=0
    last=None
    for y in rows:
        if last is None or y-last>1:runs+=1
        last=y
    return [round(blue_count/(w*h),6),
            round(min(4,runs)/4,6),
            round((max_row-min_row)/h,6) if min_row is not None else 0.]

def distance(a,b):
    if len(a)!=len(b):raise ValueError('S6_MODEL_VECTOR_SHAPE_MISMATCH')
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def train(empty_path,stacked_path,out_path):
    empty=read_ppm(empty_path);stack=read_ppm(stacked_path)
    if empty[:2]!=stack[:2]:raise ValueError('S6_TRAIN_IMAGE_SIZE_MISMATCH')
    f0=features(empty[2],*empty[:2])
    f1=features(stack[2],*stack[:2])
    d=distance(f0,f1)
    if d<.025:raise ValueError('S6_TRAIN_CLASSES_NOT_VISUALLY_SEPARABLE')
    model={'schema':1,'algorithm':'supervised_two_prototype_rgb_layers',
           'classes':{'NOT_STACKED':f0,'STACKED':f1},
           'input_width':empty[0],'input_height':empty[1],
           'interclass_distance':round(d,8),
           # Strict distance and class margin: fail closed under camera shift.
           'max_distance':round(d*.45,8),
           'min_margin':.25,
           'training_examples':{
             'NOT_STACKED':hashlib.sha256(empty[2]).hexdigest(),
             'STACKED':hashlib.sha256(stack[2]).hexdigest()
           },
           'training_limitations':'One real Gazebo viewpoint per class; no independent generalization evidence.'}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True)
    Path(out_path).write_text(json.dumps(model,indent=2)+'\n')
    return model

def validate(model):
    if (model.get('schema')!=1 or
        model.get('algorithm')!='supervised_two_prototype_rgb_layers'):
        raise ValueError('S6_UNVERIFIED_MODEL_SCHEMA')
    c=model.get('classes',{})
    if not all(label in c and len(c[label])==FEATURES for label in LABELS):
        raise ValueError('S6_MISSING_MODEL_CLASS')
    if not 0<model.get('max_distance',0)<model.get('interclass_distance',0):
        raise ValueError('S6_UNSAFE_MODEL_DISTANCE')
    return model

def infer(model,raw,w,h):
    validate(model)
    if (w,h)!=(model['input_width'],model['input_height']):
        return {'result':'UNKNOWN','confidence':0.,'reason':'IMAGE_SHAPE_CHANGED'}
    x=features(raw,w,h)
    d={label:distance(x,model['classes'][label]) for label in LABELS}
    near=min(d,key=d.get);far=max(d,key=d.get)
    closeness=1.-d[near]/max(1e-8,model['interclass_distance'])
    margin=(d[far]-d[near])/max(d[far]+d[near],1e-8)
    confidence=max(0.,min(1.,closeness))
    if d[near]>model['max_distance'] or margin<model['min_margin']:
        return {'result':'UNKNOWN','confidence':round(confidence,4),
                'reason':'LOW_SIMILARITY_OR_AMBIGUOUS'}
    return {'result':near,'confidence':round(confidence,4),
            'reason':'REAL_RGB_MODEL_INFERENCE',
            'nearest_distance':round(d[near],6)}

def accept_return(prediction,arrival_ok,stopped,frames_fresh):
    """One narrow authorization boundary; Vision never writes to cmd_vel."""
    return bool(arrival_ok and stopped and frames_fresh and
                prediction.get('result')=='STACKED' and
                prediction.get('reason')=='REAL_RGB_MODEL_INFERENCE' and
                prediction.get('confidence',0)>=.5)

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='action',required=True)
    t=sub.add_parser('train')
    t.add_argument('--empty',type=Path,required=True)
    t.add_argument('--stacked',type=Path,required=True)
    t.add_argument('--out',type=Path,required=True)
    s=sub.add_parser('predict')
    s.add_argument('--model',type=Path,required=True)
    s.add_argument('--ppm',type=Path,required=True)
    args=p.parse_args()
    if args.action=='train':
        model=train(args.empty,args.stacked,args.out)
        print('S6_VISION_REAL_RGB_MODEL_TRAINED INTERCLASS_DISTANCE='+
              str(model['interclass_distance']))
    else:
        model=json.loads(args.model.read_text())
        w,h,raw=read_ppm(args.ppm)
        print(json.dumps(infer(model,raw,w,h),sort_keys=True))
if __name__=='__main__':main()
