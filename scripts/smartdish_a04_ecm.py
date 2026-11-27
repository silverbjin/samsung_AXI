"""Exact-step actual Gazebo geometry + positive contacts, never infer silence as zero."""
import csv,math,json
NAMES=('waffle_pi','smartdish_product_dish_00','smartdish_product_dish_01','smartdish_product_dish_02')

def normq(q):
    n=math.sqrt(sum(x*x for x in q))
    if not .985<n<1.015:raise ValueError('INVALID_QUATERNION')
    return tuple(x/n for x in q)
def up(q):
    x,y,z,w=normq(q)
    return (2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y))
def tilt(q):return math.acos(max(-1.,min(1.,up(q)[2])))
def qinverse_rotate(q,v):
    x,y,z,w=normq(q);x,y,z=-x,-y,-z
    cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    qv=(x,y,z);t=tuple(2*x for x in cross(qv,v));c=cross(qv,t)
    return tuple(v[i]+w*t[i]+c[i] for i in range(3))
def relative(robot,dish):
    xyz=qinverse_rotate(robot[4:],tuple(dish[i]-robot[i] for i in range(1,4)))
    a,b=up(robot[4:]),up(dish[4:]);angle=math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(a,b)))))
    return xyz,angle
def read_model(fields):
    if len(fields)!=8:raise ValueError('MODEL_FIELDS')
    ident=int(fields[0]);v=tuple(map(float,fields[1:]))
    if not all(map(math.isfinite,v)):raise ValueError('NONFINITE_MODEL')
    if ident:normq(v[3:])
    return (ident,*v)
def bound(g,robot):
    x,y=robot[1:3];f=g['floor'];r=math.sqrt(2)*.29+1.15*math.sin(tilt(robot[4:]))+.01
    d=min(x-f['lo'][0],f['hi'][0]-x,y-f['lo'][1],f['hi'][1]-y)
    for c in g['obstacles']:
        lo,hi=c['lo'],c['hi'];d=min(d,math.hypot(max(lo[0]-x,x-hi[0],0),max(lo[1]-y,y-hi[1],0)))
    return d-r
def dish_mast_bound(g,xyz,angle):
    r=.245+.0185*math.sin(angle);zext=.0185+.245*math.sin(angle);x,y,z=xyz
    minimum=None
    for c in g['robot_collisions']:
        if c['link']=='smartdish_product_tray' and c['collision']=='platform_collision':continue
        lo,hi=c['lo'],c['hi']
        if z+zext<lo[2] or z-zext>hi[2]:continue
        d=math.hypot(max(lo[0]-x,x-hi[0],0),max(lo[1]-y,y-hi[1],0))-r
        minimum=d if minimum is None else min(minimum,d)
    return minimum

def verify_ticks(tick_path,pair_path,legs,geom,categorize,mission_mode="both"):
    pair_map={}
    with open(pair_path) as f:
        for r in csv.DictReader(f,delimiter='\t'):
            key=(int(r['id1']),int(r['id2']))
            if key in pair_map:raise ValueError('DUPLICATE_PAIR_ID')
            pair_map[key]=(r['name1'],r['name2'])
    phases=[]
    for leg in legs:
        if leg.get('status')!='SUCCEEDED':continue
        phases.append(dict(phase=leg['mission']+'_'+leg['leg'],start=int(leg['start_sim_ns']),end=int(leg['end_sim_ns']),ids=leg['loaded_entity_ids'] or [],samples=0,first=None,last=None,previous_iteration=None,max_gap_ns=0,minimum_clearance_m=None,max_center_m=0.,max_z_error_m=0.,max_tilt_rad=0.,minimum_mast_clearance_m=None,positive_support_steps=0,positive_tray_steps=0,unexpected_pairs=[],errors=[]))
    def err(p,k):
        if k not in p['errors']:p['errors'].append(k)
    with open(tick_path) as f:
        reader=csv.reader(f,delimiter='\t');header=next(reader)
        expected=['sim_ns','iteration','dt_ns','contact_components','pair_count','pairs']+[n+'_'+k for n in NAMES for k in ('id','x','y','z','qx','qy','qz','qw')]
        if header!=expected:raise ValueError('ECM_HEADER')
        previous=None;robot_id=None;idx=0
        for fields in reader:
            if len(fields)!=38:raise ValueError('ECM_TICK_TRUNCATED_OR_OVERFLOW')
            stamp,it,dt,count,pc=map(int,fields[:5])
            if dt<=0 or dt>2_000_000 or (previous and (stamp<=previous[0] or it<=previous[1])):raise ValueError('ECM_TICK_ORDER_OR_DT')
            previous=(stamp,it)
            while idx<len(phases) and stamp>phases[idx]['end']:idx+=1
            if idx>=len(phases):continue
            p=phases[idx]
            if stamp<p['start']:continue
            if p['last'] is not None:
                gap=stamp-p['last'];p['max_gap_ns']=max(p['max_gap_ns'],gap)
                if it!=p['previous_iteration']+1 or gap!=dt:err(p,'ECM_STEP_GAP')
            else:p['first']=stamp
            p['last']=stamp;p['previous_iteration']=it;p['samples']+=1
            robot=read_model(fields[6:14]);dishes=[read_model(fields[14+i*8:22+i*8]) for i in range(3)]
            if not robot[0]:err(p,'ROBOT_MISSING');continue
            if robot_id is None:robot_id=robot[0]
            if robot_id!=robot[0]:err(p,'ROBOT_ID_DRIFT')
            if [x[0] for x in dishes if x[0]]!=p['ids']:err(p,'DISH_ID_DRIFT')
            clear=bound(geom,robot);p['minimum_clearance_m']=clear if p['minimum_clearance_m'] is None else min(clear,p['minimum_clearance_m'])
            if clear<=.05:err(p,'ENVIRONMENT_SEPARATION')
            for i,dish in enumerate(dishes):
                if not dish[0]:continue
                xyz,angle=relative(robot,dish);center=math.hypot(*xyz[:2]);zerr=abs(xyz[2]-(.445+.037*(i+.5)))
                p['max_center_m']=max(p['max_center_m'],center);p['max_z_error_m']=max(p['max_z_error_m'],zerr);p['max_tilt_rad']=max(p['max_tilt_rad'],angle)
                if center>.015 or zerr>.02 or angle>.035:err(p,'DISH_RELATIVE_POSE')
                mast=dish_mast_bound(geom,xyz,angle)
                if mast is not None:
                    p['minimum_mast_clearance_m']=mast if p['minimum_mast_clearance_m'] is None else min(mast,p['minimum_mast_clearance_m'])
                    if mast<=0:err(p,'DISH_MAST_SEPARATION')
            keys=[] if fields[5]=='-' else [tuple(map(int,x.split(':'))) for x in fields[5].split(';')]
            if len(keys)!=pc or len(set(keys))!=pc:err(p,'CONTACT_PAIR_COUNT')
            cats=[]
            for key in keys:
                if key not in pair_map:err(p,'UNKNOWN_CONTACT_ID');continue
                a,b=pair_map[key];cat=categorize({},a,b);cats.append(cat)
                if cat in ('UNEXPECTED','UNIDENTIFIED'):
                    if len(p['unexpected_pairs'])<50 and (a,b) not in p['unexpected_pairs']:p['unexpected_pairs'].append((a,b))
                    err(p,'UNEXPECTED_CONTACT_OBSERVED')
            if count<=0:err(p,'CONTACT_COMPONENTS_NOT_OBSERVED')
            p['positive_support_steps']+=int('GROUND_SUPPORT' in cats)
            p['positive_tray_steps']+=int('TRAY_DISH' in cats)
    for p in phases:
        if p['samples']<2 or p['first'] is None or p['first']-p['start']>2_000_000 or p['end']-p['last']>2_000_000:err(p,'ECM_WINDOW_NOT_COVERED')
        if not p['positive_support_steps']:err(p,'GROUND_SUPPORT_NOT_OBSERVED')
        if p['ids'] and not p['positive_tray_steps']:err(p,'TRAY_SUPPORT_NOT_OBSERVED')
        p['pass']=not p['errors']
    expected_count={"both":6,"loaded":3,"shutdown":1}.get(mission_mode)
    if mission_mode not in ("both","loaded","shutdown"):raise ValueError("INVALID_MISSION_MODE")
    expected_names=["a04-loaded_"+leg for leg in ("TO_TABLE","TO_RETURN","TO_HOME")]
    if mission_mode=="both":expected_names=["a04-empty_"+leg for leg in ("TO_TABLE","TO_RETURN","TO_HOME")]+expected_names
    if mission_mode=="shutdown":expected_names=["a04-shutdown_TO_TABLE"]
    phase_names=[p["phase"] for p in phases]
    return {'scope':'READ_ONLY_ECM_EVERY_PHYSICS_STEP_GEOMETRIC_SEPARATION_AND_POSITIVE_CONTACTS',
        'mission_mode':mission_mode,'completed_leg_count':len(phases),'phases':phases,
        'pass':len(phases)==expected_count and phase_names==expected_names and all(p['pass'] for p in phases),
        'negative_contact_inferred_from_silence':False}

def dynamics(path):
    phases={}
    with open(path) as f:
        for line in f:
            row=json.loads(line);p=phases.setdefault(row['phase'],{'samples':0,'max_linear_mps':0.,'max_angular_radps':0.,'max_linear_accel_mps2':0.,'max_angular_accel_radps2':0.,'last':None})
            t=row['odom_stamp_ns'];v=row['odom_linear_mps'];w=row['odom_angular_radps']
            last=p['last']
            if last and t<=last[0]:continue
            if last:
                dt=(t-last[0])/1e9
                p['max_linear_accel_mps2']=max(p['max_linear_accel_mps2'],abs(v-last[1])/dt)
                p['max_angular_accel_radps2']=max(p['max_angular_accel_radps2'],abs(w-last[2])/dt)
            p['last']=(t,v,w);p['samples']+=1
            p['max_linear_mps']=max(p['max_linear_mps'],v);p['max_angular_radps']=max(p['max_angular_radps'],w)
    for p in phases.values():p.pop('last')
    return {'scope':'DERIVED_ACTUAL_ODOM_MAGNITUDE_FINITE_DIFFERENCE_NOT_COMMAND_LIMIT_PROOF','phases':phases}
