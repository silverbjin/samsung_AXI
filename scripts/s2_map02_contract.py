"""S2-MAP-02 fixed CI survey route and quality gates (not a Nav2 planner).

World coordinates below are sourced from restaurant.sdf / WORLD_LAYOUT.md.
No synthetic occupancy cells or fixture maps are generated.
"""
import math
from collections import deque
from pathlib import Path
import xml.etree.ElementTree as ET

START=(-2.60,-2.20)
TABLE3_APPROACH=(2.65,-1.82)
# Counter clearance, north chairs, table_5 and human_proxy kept away from the route.
SURVEY=(
    (-2.60,-2.20),(-2.60,-0.60),(-3.75,-0.60),(-3.75,3.91),
    (3.85,3.91),(3.85,1.20),(1.30,1.20),(1.30,-2.12),
    (3.85,-2.12),(3.85,-2.55),(3.85,-2.12),(1.30,-2.12),(-2.60,-2.12)
)

# S2-MAP-03: additional line-of-sight vantage points around occluding tables.
# Candidate ONLY; the released S2-MAP-02 SURVEY is unchanged.
OBSERVATION_SURVEY=(
    (-2.60,-2.20),(-2.60,-0.60),(-1.90,-0.60),(-1.90,1.40),
    (-3.75,1.40),(-3.75,-0.60),(-3.75,3.91),
    (-1.45,3.91),(-1.45,1.80),(-1.45,3.91),
    (1.40,3.91),(1.40,1.20),(1.40,3.91),
    (3.85,3.91),(3.85,1.20),(3.10,1.20),(3.10,-1.40),
    (0.00,-1.40),(0.00,-0.40),(1.30,-0.40),(1.30,-1.40),
    (1.30,1.20),(1.30,-2.12),
    (3.85,-2.12),(3.85,-2.55),(3.85,-2.12),(1.30,-2.12),(-2.60,-2.12)
)

CLEARANCE=0.27

def route_length(route=SURVEY):
    return sum(math.dist(a,b) for a,b in zip(route,route[1:]))

def boxes_from_sdf(path):
    root=ET.parse(path).getroot()
    boxes=[]
    for model in root.findall('.//world/model'):
        name=model.attrib['name']
        if name in ('floor',):continue
        pose=[float(x) for x in (model.findtext('pose') or '0 0 0 0 0 0').split()]
        col=model.find('./link/collision')
        if col is None: continue
        size=col.findtext('geometry/box/size')
        radius=col.findtext('geometry/cylinder/radius')
        if size:
            sx,sy,_=(float(v) for v in size.split())
            boxes.append((name,pose[0],pose[1],sx/2,sy/2,0.0))
        elif radius:
            boxes.append((name,pose[0],pose[1],0.0,0.0,float(radius)))
    return boxes

def route_clearance(world_file,route=SURVEY,clearance=CLEARANCE):
    obstacles=boxes_from_sdf(world_file)
    violations=[]
    for a,b in zip(route,route[1:]):
        steps=max(2,math.ceil(math.dist(a,b)/.035))
        for i in range(steps+1):
            x=a[0]+(b[0]-a[0])*i/steps;y=a[1]+(b[1]-a[1])*i/steps
            for name,cx,cy,hx,hy,r in obstacles:
                if r:
                    distance=math.hypot(x-cx,y-cy)-r
                else:
                    distance=math.hypot(max(abs(x-cx)-hx,0),max(abs(y-cy)-hy,0))
                if distance<clearance:
                    violations.append((name,round(x,3),round(y,3),round(distance,3)))
                    break
            if violations:return violations
    return violations

def yaw_from_quat(z,w):
    return math.atan2(2*z*w,1-2*z*z)

def from_world_to_odom(world_point,start_odom):
    """Robot spawned at START with yaw=0 in Gazebo; odom start may be (0,0)."""
    dx=world_point[0]-START[0];dy=world_point[1]-START[1]
    x0,y0,yaw=start_odom
    return (x0+dx*math.cos(yaw)-dy*math.sin(yaw),
            y0+dx*math.sin(yaw)+dy*math.cos(yaw))

def map_coordinates(odom_pt,transform):
    """Transform is the observed TF map -> odom: tx,ty,yaw."""
    tx,ty,yaw=transform
    return (tx+math.cos(yaw)*odom_pt[0]-math.sin(yaw)*odom_pt[1],
            ty+math.sin(yaw)*odom_pt[0]+math.cos(yaw)*odom_pt[1])

def grid_index(grid,x,y):
    origin=grid.info.origin
    yaw=yaw_from_quat(origin.orientation.z,origin.orientation.w)
    dx=x-origin.position.x;dy=y-origin.position.y
    gx=math.cos(yaw)*dx+math.sin(yaw)*dy
    gy=-math.sin(yaw)*dx+math.cos(yaw)*dy
    col=round(gx/grid.info.resolution);row=round(gy/grid.info.resolution)
    if 0<=col<grid.info.width and 0<=row<grid.info.height:
        return row*grid.info.width+col
    return None

def coverage(grid):
    w=grid.info.width;h=grid.info.height;r=grid.info.resolution
    data=grid.data
    if w<8 or h<8 or r<=0 or len(data)!=w*h:
        raise ValueError('MAP_DIMENSIONS_INVALID')
    known=[i for i,v in enumerate(data) if v>=0]
    free=sum(0<=v<=25 for v in data)
    occupied=sum(v>=65 for v in data)
    if not known:raise ValueError('MAP_EMPTY')
    cols=[v%w for v in known];rows=[v//w for v in known]
    report=dict(width=w,height=h,resolution=r,known=len(known),free=free,
                occupied=occupied,known_span_x_m=(max(cols)-min(cols))*r,
                known_span_y_m=(max(rows)-min(rows))*r)
    # MVP evidence thresholds measured on real OccupancyGrid, never on a static SDF.
    if free<1500 or occupied<120 or len(known)<2400:
        raise ValueError('MAP_INSUFFICIENT_FREE_OCCUPIED_EVIDENCE:'+str(report))
    if report['known_span_x_m']<7.0 or report['known_span_y_m']<6.0:
        raise ValueError('MAP_SPATIAL_EXTENT_INSUFFICIENT:'+str(report))
    return report

def nearest_free(grid,point,rad_m=.85):
    w=grid.info.width;h=grid.info.height;r=grid.info.resolution
    idx=grid_index(grid,*point)
    if idx is None:return None
    row,col=divmod(idx,w)
    radius=math.ceil(rad_m/r)
    best=None
    for dy in range(-radius,radius+1):
        for dx in range(-radius,radius+1):
            if (dx*dx+dy*dy)*r*r>rad_m*rad_m:continue
            cy=row+dy;cx=col+dx
            if 0<=cx<w and 0<=cy<h and 0<=grid.data[cy*w+cx]<=25:
                d=dx*dx+dy*dy
                if best is None or d<best[0]:best=(d,cy*w+cx)
    return None if best is None else best[1]

def free_path_connected(grid,start_xy,goal_xy):
    start=nearest_free(grid,start_xy)
    goal=nearest_free(grid,goal_xy)
    if start is None or goal is None:return False
    w=grid.info.width;h=grid.info.height
    todo=deque([start]);seen={start}
    while todo:
        i=todo.popleft()
        if i==goal:return True
        y,x=divmod(i,w)
        for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if not (0<=nx<w and 0<=ny<h):continue
            v=ny*w+nx
            if v not in seen and 0<=grid.data[v]<=25:
                seen.add(v);todo.append(v)
    return False


def front_sector_clearance(scan,sector=.40):
    """Return closest front obstacle or range_max on documented +inf no-return.

    Fail closed on NaNs, zero, stale/absent scan (caller's freshness check),
    or too many invalid beams; do not invent clear rays.
    """
    finite=[];inf_clear=0;invalid=0;count=0
    for i,d in enumerate(scan.ranges):
        az=math.atan2(math.sin(scan.angle_min+i*scan.angle_increment),
                      math.cos(scan.angle_min+i*scan.angle_increment))
        if abs(az)>sector:continue
        count+=1
        if math.isfinite(d) and scan.range_min<=d<=scan.range_max:
            finite.append(d)
        elif math.isinf(d) and d>0:
            inf_clear+=1
        else:
            invalid+=1
    meta=dict(beams=count,finite=len(finite),positive_inf=inf_clear,invalid=invalid)
    usable=len(finite)+inf_clear
    if count<10 or usable/count<.80:
        return 0.0,meta
    if finite:
        return min(finite),meta
    if inf_clear>=10 and scan.range_max>.4:
        return scan.range_max,meta
    return 0.0,meta
