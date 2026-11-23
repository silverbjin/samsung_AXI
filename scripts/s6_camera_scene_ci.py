#!/usr/bin/env python3
"""S6-00/CAMERA-01: actual Gazebo images, NO Nav2 Goal or fake Vision AI."""
import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path

def rgb_bytes(msg):
    if msg.encoding not in ('rgb8','bgr8'):
        raise RuntimeError('S6_IMAGE_ENCODING_UNSUPPORTED:'+str(msg.encoding))
    if msg.width<16 or msg.height<16 or msg.step<msg.width*3:
        raise RuntimeError('S6_IMAGE_INVALID_SHAPE')
    raw=bytes(msg.data)
    if len(raw)<msg.step*msg.height:raise RuntimeError('S6_IMAGE_TRUNCATED')
    data=b''.join(raw[y*msg.step:y*msg.step+msg.width*3]
                  for y in range(msg.height))
    if msg.encoding=='bgr8':
        data=bytes(v for i in range(0,len(data),3)
                   for v in (data[i+2],data[i+1],data[i]))
    return data

def diff_fraction(a,b):
    if len(a)!=len(b) or len(a)%3:raise ValueError('S6_RGB_FRAME_SIZE_MISMATCH')
    changed=sum(
        (abs(a[i]-b[i])+abs(a[i+1]-b[i+1])+abs(a[i+2]-b[i+2]))>45
        for i in range(0,len(a),3))
    return changed/(len(a)//3)

def save_ppm(path,w,h,rgb):
    path.write_bytes(f'P6\n{w} {h}\n255\n'.encode()+rgb)

def cleanup(proc):
    if proc.poll() is None:
        os.killpg(proc.pid,signal.SIGINT)
        try:proc.wait(timeout=12)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait()

def run(args):
    from s6_scene import write_fixture,FIXTURE_WORLD_XY
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image,LaserScan
    args.out.mkdir(parents=True,exist_ok=True)
    cmd=['ros2','launch','restaurant_bringup','world.launch.py',
         'gui:=false','robot_sdf:='+str(args.robot_sdf.resolve()),
         'bridge_config:='+str(args.bridge.resolve()),
         'spawn_x:=2.65','spawn_y:=-1.82','spawn_yaw:=-1.57079632679']
    with (args.out/'gazebo.log').open('w') as log:
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,
                              env=os.environ.copy(),start_new_session=True)
        node=None;started=False
        try:
            rclpy.init();started=True
            node=rclpy.create_node('s6_camera_scene_evidence')
            scan_count=[0];frames=[]
            def scan_cb(m):
                if m.ranges:scan_count[0]+=1
            subscan=node.create_subscription(LaserScan,'/scan',scan_cb,qos_profile_sensor_data)
            def wait(test,seconds,label):
                until=time.monotonic()+seconds
                while time.monotonic()<until:
                    if proc.poll() is not None:
                        raise RuntimeError('S6_GAZEBO_LAUNCH_EXITED:'+str(proc.returncode))
                    rclpy.spin_once(node,timeout_sec=.4)
                    if test():return
                raise RuntimeError('S6_TIMEOUT_'+label)
            wait(lambda:scan_count[0]>=4,120,'SCAN')
            before=node.count_subscribers('/restaurant/rgbd/image')
            if before:raise RuntimeError('S6_PREARRIVAL_IMAGE_SUBSCRIBER_NOT_ZERO')
            def image_cb(m):
                if m.width and m.height and m.data:
                    frames.append((time.monotonic(),m))
                    if len(frames)>12:del frames[:-12]
            subscriber=node.create_subscription(Image,'/restaurant/rgbd/image',
                                                image_cb,qos_profile_sensor_data)
            wait(lambda:len(frames)>=3,30,'EMPTY_RGB_IMAGE')
            _,empty=frames[-1]
            a=rgb_bytes(empty)
            old=rgb_bytes(frames[-2][1])
            empty_noise=diff_fraction(a,old)
            save_ppm(args.out/'empty.ppm',empty.width,empty.height,a)
            fixture=args.out/'stacked_dishes.sdf'
            write_fixture(fixture)
            created=subprocess.run(
                ['ros2','run','ros_gz_sim','create','-name','s6_stacked_dishes',
                 '-file',str(fixture),'-x',str(FIXTURE_WORLD_XY[0]),
                 '-y',str(FIXTURE_WORLD_XY[1]),'-z','0'],
                capture_output=True,text=True,timeout=30)
            if created.returncode or 'entity creation successful' not in (
                     created.stdout+created.stderr).lower():
                raise RuntimeError('S6_DISH_FIXTURE_SPAWN_FAIL:'+
                                   repr((created.stdout+created.stderr)[-450:]))
            fixture_t=time.monotonic();best=None
            until=time.monotonic()+20
            while time.monotonic()<until:
                rclpy.spin_once(node,timeout_sec=.4)
                for t,msg in frames[-4:]:
                    if t<fixture_t+.5 or msg.width!=empty.width or msg.height!=empty.height:
                        continue
                    b=rgb_bytes(msg)
                    d=diff_fraction(a,b)
                    if best is None or d>best[0]:best=(d,t,b)
                if best and best[0]>.003 and best[0]>empty_noise+.002:
                    break
            if best is None:raise RuntimeError('S6_STACKED_RGB_FRAME_MISSING')
            delta,_,b=best
            save_ppm(args.out/'stacked.ppm',empty.width,empty.height,b)
            node.destroy_subscription(subscriber)
            wait(lambda:node.count_subscribers('/restaurant/rgbd/image')==0,
                 4,'RGB_SUBSCRIBER_TEARDOWN')
            topics=dict(node.get_topic_names_and_types())
            if ('/restaurant/rgbd/depth_image' in topics or
                    '/restaurant/rgbd/points' in topics):
                raise RuntimeError('S6_DEPTH_OR_POINTS_BRIDGE_LEAK')
            record={'real_gazebo':True,'goal_sent':False,
                    'image_subscribers_pre_arrival':before,
                    'image_subscription_released':True,
                    'laser_scan_count':scan_count[0],
                    'width':empty.width,'height':empty.height,
                    'empty_image_sha256':hashlib.sha256(a).hexdigest(),
                    'stacked_image_sha256':hashlib.sha256(b).hexdigest(),
                    'background_changed_fraction':round(empty_noise,6),
                    'fixture_changed_fraction':round(delta,6),
                    'fixture_visible':bool(delta>.003 and delta>empty_noise+.002),
                    'vision_ai_inference':'NOT_RUN',
                    'gazebo_renderer_idle':'NOT_VERIFIED'}
            (args.out/'s6_scene_evidence.json').write_text(
                json.dumps(record,indent=2,sort_keys=True)+'\n')
            if not record['fixture_visible']:
                raise RuntimeError('S6_00_REAL_RGB_DISHES_NOT_VISIBLE:'+str(delta))
            print('S6_00_REAL_GAZEBO_DISH_VISIBLE_PASS PIXEL_CHANGE='+str(round(delta,5)),flush=True)
            print('S6_CAMERA_01_LAZY_RGB_REQUEST_PASS_NO_GOAL',flush=True)
        finally:
            if node:node.destroy_node()
            if started and rclpy.ok():rclpy.shutdown()
            cleanup(proc)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('robot-sdf','bridge','out'):
        p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
