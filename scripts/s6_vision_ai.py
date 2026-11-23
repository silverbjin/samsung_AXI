#!/usr/bin/env python3
"""S6 compact supervised image classifier for controlled Gazebo dish fixtures.

A learned two-prototype RGB feature model, NOT a general object detector.
Training must use actual labeled camera PPMs. No synthetic PASS or retraining
inside navigation; a missing/ambiguous model returns UNKNOWN and blocks return.
"""
import argparse,hashlib,json,math
from pathlib import Path

LABELS=('NOT_STACKED','STACKED')
GRID=6
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
    """Spatial color and chroma features, normalized 0..1.

    Grid color aggregates retain crude dish position; blues distinguish the
    pale/blue ceramic rim from the dark-brown tabletop. No Depth is used.
    """
    if len(rgb)!=w*h*3 or w<16 or h<16:raise ValueError('S6_RGB_DIMENSIONS')
    cells=GRID*GRID
    sums=[[0.,0.,0.,0.,0.] for _ in range(cells)]
    counts=[0 for _ in range(cells)]
    for y in range(h):
        by=min(GRID-1,y*GRID//h)
        for x in range(w):
            bx=min(GRID-1,x*GRID//w)
            cell=by*GRID+bx
            i=(y*w+x)*3
            r,g,b=rgb[i],rgb[i+1],rgb[i+2]
            sums[cell][0]+=r/255
            sums[cell][1]+=g/255
            sums[cell][2]+=b/255
            sums[cell][3]+=float(b>r*1.30 and b>g*1.10 and b>75)
            sums[cell][4]+=float(r>165 and g>165 and b>175)
            counts[cell]+=1
    return [round(v/max(1,counts[c]),6)
            for c in range(cells) for v in sums[c]]

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
    model={'schema':1,'algorithm':'supervised_two_prototype_rgb_grid',
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
        model.get('algorithm')!='supervised_two_prototype_rgb_grid'):
        raise ValueError('S6_UNVERIFIED_MODEL_SCHEMA')
    c=model.get('classes',{})
    if not all(label in c and len(c[label])==GRID*GRID*5 for label in LABELS):
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
    confidence=max(0.,min(1.,min(closeness,margin)))
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
