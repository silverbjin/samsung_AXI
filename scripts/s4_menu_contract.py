"""S4 integration evidence-only primitives. No planner or motor control."""
import math
from pathlib import Path

NORMAL_LIMIT=0.23
SOUP_LIMIT=0.11
MAX_EXCESS_MPS=0.07

def percentile(values, fraction):
    ordered=sorted(float(v) for v in values)
    if not ordered:raise ValueError('S4_EMPTY_REAL_ODOM_SAMPLES')
    index=(len(ordered)-1)*fraction
    low=int(math.floor(index)); high=int(math.ceil(index))
    return ordered[low]+(ordered[high]-ordered[low])*(index-low)

def measured_speed(label, samples):
    valid=[abs(float(v)) for v in samples if math.isfinite(v) and abs(v)>=0.045]
    if len(valid)<8:
        raise ValueError('S4_'+label+'_INSUFFICIENT_MOVING_ODOM_SAMPLES_'+str(len(valid)))
    return {'menu':label,'sample_count':len(valid),
            'median_mps':round(percentile(valid,.5),4),
            'p75_mps':round(percentile(valid,.75),4),
            'p95_mps':round(percentile(valid,.95),4),
            'max_mps':round(max(valid),4)}

def compare_speeds(normal,soup):
    """Fail on non-applied limit, same speed, or speed beyond cap tolerance."""
    n=normal['p75_mps'];s=soup['p75_mps']
    if n<.14 or s<.065:
        raise ValueError('S4_ACTUAL_SPEED_TOO_LOW_TO_COMPARE')
    if n-s<.04 or n/s<1.35:
        raise ValueError('S4_SOUP_NOT_MEASURABLY_SLOWER')
    if normal['p95_mps']>NORMAL_LIMIT+MAX_EXCESS_MPS:
        raise ValueError('S4_NORMAL_OVER_LIMIT')
    if soup['p95_mps']>SOUP_LIMIT+MAX_EXCESS_MPS:
        raise ValueError('S4_SOUP_OVER_LIMIT')
    return {'normal':normal,'soup':soup,'p75_delta_mps':round(n-s,4),
            'p75_ratio_normal_to_soup':round(n/s,3)}

def fixture_sdf():
    """A passive physical Gazebo cylinder; all test sensor data are real."""
    return """<?xml version="1.0"?>
<sdf version="1.8"><model name="s4_collision_fixture">
  <static>true</static><link name="body">
    <collision name="c"><geometry><cylinder>
      <radius>0.14</radius><length>0.50</length>
    </cylinder></geometry></collision>
    <visual name="v"><geometry><cylinder>
      <radius>0.14</radius><length>0.50</length>
    </cylinder></geometry></visual>
  </link></model></sdf>
"""

def front_obstacle_points(scan,limit=.65):
    if scan is None:return 0
    count=0
    for i,d in enumerate(scan.ranges):
        angle=math.atan2(math.sin(scan.angle_min+i*scan.angle_increment),
                         math.cos(scan.angle_min+i*scan.angle_increment))
        if abs(angle)<.48 and math.isfinite(d) and scan.range_min<=d<=min(scan.range_max,limit):
            count+=1
    return count
