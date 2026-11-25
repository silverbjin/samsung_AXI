#!/usr/bin/env python3
"""R02 new production-geometry diagnostic. No old capture replay or label approval.

The same-run Gazebo PostUpdate probe reads actual ContactSensorData without
mutating the ECM. It is NOT a physics-freshness heartbeat. A silent channel
remains HOLD even if an empty component is read on every step.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET

from a14_contact_calibration import call, stop_owned
from a14_production_health_contract import assess, ECM, ROS
from smartdish_tray_world import write_trial, WORLD
from smartdish_a14_physics import configure_sdf

STEP = 1_000_000
SPAN = 2_000_000_000
LIMIT = 100000
SERVER_READY_S = 24
DISCOVERY_S = 16
OBSERVE_S = 38
WALL_S = 95


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')


def jsonl(path, rows):
    Path(path).write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in rows))


def prepare(folder, plugin):
    original = folder/'scenario.sdf'
    config = write_trial('ST-02', 211, original, 'R02_PRODUCTION_PROBE')
    cfg = configure_sdf(original, config)
    root = ET.parse(original).getroot()
    world = root.find('./world')
    expected = {}
    for model in world.findall('model'):
        for link in model.findall('link'):
            for sensor in link.findall('sensor'):
                if sensor.get('type') != 'contact':
                    continue
                topic = sensor.findtext('contact/topic')
                if topic in expected or topic not in cfg['topics']:
                    raise RuntimeError('R02_DUPLICATE_OR_UNKNOWN_SDF_TOPIC')
                expected[topic] = {'model':model.get('name'), 'sensor':sensor.get('name'),
                                   'collision':sensor.findtext('contact/collision')}
    if set(expected) != set(cfg['topics']) or not expected:
        raise RuntimeError('R02_SDF_EXPECTED_TOPICS_MISMATCH')
    dump(folder/'expected_sensors.json', expected)
    p = ET.SubElement(world, 'plugin', filename=str(plugin),
                      name='smartdish::A14ProductionHealth')
    ET.SubElement(p, 'output').text = str((folder/'ecm_contact_steps.tsv').resolve())
    probe = folder/'probe_world.sdf'
    ET.ElementTree(root).write(probe, encoding='utf-8', xml_declaration=True)
    # Verify that the sole world change was the observer plugin.
    verify = ET.parse(probe).getroot()
    vw = verify.find('./world')
    vw.remove(vw.find("./plugin[@name='smartdish::A14ProductionHealth']"))
    if ET.tostring(verify) != ET.tostring(ET.parse(original).getroot()):
        raise RuntimeError('R02_OBSERVER_MUTATED_WORLD')
    import yaml
    bridge = yaml.safe_load(Path(cfg['bridge']).read_text())
    bridge.append(dict(ros_topic_name='/clock', gz_topic_name='/clock',
                       ros_type_name='rosgraph_msgs/msg/Clock', gz_type_name='gz.msgs.Clock',
                       direction='GZ_TO_ROS'))
    bridge_path = folder/'health_bridge.yaml'
    bridge_path.write_text(yaml.safe_dump(bridge, sort_keys=False))
    return expected, probe, bridge_path


def read_ecm(path):
    if not path.is_file():
        raise RuntimeError('R02_ECM_PROBE_OUTPUT_MISSING')
    rows = []
    overflow = False
    with path.open() as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['sim_ns'] == 'OVERFLOW':
                overflow = True
                break
            if len(rows) >= LIMIT:
                overflow = True
                break
            row = {k:r[k] for k in ('topic','model','sensor','collision')}
            row.update({k:int(r[k]) for k in ('sim_ns','iteration','dt_ns','sensor_id','collision_id','count')})
            row['present'] = r['present'] == '1'
            row['source'] = ECM
            row['pairs'] = [list(map(int,x.split(':'))) for x in r['pairs'].split(';') if x]
            rows.append(row)
    return rows, overflow


def archive(folder):
    allowed = ('scenario.sdf','scenario.scenario.json','geometry_layout.json',
               'a14_contact_bridge.yaml','probe_world.sdf','health_bridge.yaml',
               'expected_sensors.json','ecm_contact_steps.tsv','ros_contacts.jsonl',
               'ros_clock.jsonl','gazebo.log','bridge.log','health_result.json')
    files = [folder/n for n in allowed if (folder/n).is_file()]
    sums = folder/'SHA256SUMS'
    sums.write_text(''.join(hash_file(p)+'  '+p.name+'\n' for p in files))
    bundle = folder/'a14_production_health_evidence.tar.gz'
    with tarfile.open(bundle,'w:gz') as f:
        for p in files+[sums]:
            f.add(p,arcname=p.name)
    (folder/(bundle.name+'.sha256')).write_text(hash_file(bundle)+'  '+bundle.name+'\n')
    print('R02_ARCHIVE='+str(bundle),flush=True)
    print('R02_ARCHIVE_SHA256='+hash_file(bundle),flush=True)


def run(sha, plugin, folder):
    root = Path(__file__).resolve().parents[1]
    if not re.fullmatch(r'[0-9a-f]{40}',sha) or subprocess.check_output(
            ['git','-C',str(root),'-c','safe.directory='+str(root),'rev-parse','HEAD'],
            text=True,timeout=8).strip()!=sha:
        raise RuntimeError('R02_SOURCE_SHA_MISMATCH')
    if not plugin.is_file():
        raise RuntimeError('R02_PLUGIN_BINARY_MISSING')
    folder.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    deadline = started+WALL_S
    result = dict(schema=1,source_sha=sha,source_type='REAL_GAZEBO_ECM_AND_ROS',
                  scope='NEW_ST02_PRODUCTION_GEOMETRY_DIAGNOSTIC_NOT_RGB_T0_TRIAL',
                  scene_id='ST-02',seed=211,plugin_sha256=hash_file(plugin),
                  diagnostic_capture_pass=False,production_contact_health='HOLD',
                  rule_candidate='UNKNOWN',label_status='REVIEW_REQUIRED',
                  human_approved=False,ground_truth='NOT_OPERATOR_APPROVED',
                  no_contact_inferred_from_silence=False,first_error=None)
    procs=[]; logs=[]; ros=[]; clocks=[]; overflow=False
    expected={}; discovered={}; node=None; initialized=False
    start=end=None
    env=os.environ.copy()
    env['GZ_PARTITION']='a14_health_'+str(os.getpid())
    env['ROS_DOMAIN_ID']=str(80+os.getpid()%32)
    result.update(gz_partition=env['GZ_PARTITION'],ros_domain_id=env['ROS_DOMAIN_ID'])
    try:
        expected,world,bridge=prepare(folder,plugin)
        result.update(world_sha256=hash_file(folder/'scenario.sdf'),
                      probe_world_sha256=hash_file(world),bridge_sha256=hash_file(bridge))
        os.environ['ROS_DOMAIN_ID']=env['ROS_DOMAIN_ID']
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, ReliabilityPolicy
        from rosgraph_msgs.msg import Clock
        from ros_gz_interfaces.msg import Contacts
        rclpy.init(); initialized=True
        node=Node('a14_production_health_probe')
        qos=QoSProfile(depth=2000,reliability=ReliabilityPolicy.BEST_EFFORT)
        def clock_cb(msg):
            nonlocal overflow
            if len(clocks)>=LIMIT: overflow=True; return
            clocks.append(int(msg.clock.sec)*1_000_000_000+int(msg.clock.nanosec))
        def contact_cb(topic):
            def cb(msg):
                nonlocal overflow
                if len(ros)>=LIMIT: overflow=True; return
                t=int(msg.header.stamp.sec)*1_000_000_000+int(msg.header.stamp.nanosec)
                ros.append(dict(topic=topic,sim_ns=t,source=ROS,
                    pairs=[[int(c.collision1.id),int(c.collision2.id)] for c in msg.contacts]))
            return cb
        node.create_subscription(Clock,'/clock',clock_cb,qos)
        for topic in expected: node.create_subscription(Contacts,topic,contact_cb(topic),qos)
        for name,cmd in (
            ('gazebo',['gz','sim','-s','-v2',str(world)]),
            ('bridge',['ros2','run','ros_gz_bridge','parameter_bridge','--ros-args',
                       '-p','config_file:='+str(bridge)])):
            log=(folder/(name+'.log')).open('w'); logs.append(log)
            procs.append(subprocess.Popen(cmd,env=env,stdin=subprocess.DEVNULL,stdout=log,
                         stderr=subprocess.STDOUT,start_new_session=True))
        def live():
            if any(p.poll() is not None for p in procs):
                raise RuntimeError('R02_OWNED_PROCESS_EXITED')
        until=min(deadline,time.monotonic()+SERVER_READY_S)
        while time.monotonic()<until:
            live()
            if '/world/'+WORLD+'/control' in call(env,['gz','service','-l'],timeout=4)['stdout']:
                break
            rclpy.spin_once(node,timeout_sec=.05)
        else: raise RuntimeError('R02_WORLD_CONTROL_NOT_READY')
        until=min(deadline,time.monotonic()+DISCOVERY_S)
        while time.monotonic()<until:
            live()
            rclpy.spin_once(node,timeout_sec=.05)
            discovered={t:node.count_publishers(t) for t in expected}
            if all(discovered.values()) and node.count_publishers('/clock')>0: break
        else: raise RuntimeError('R02_ROS_DISCOVERY_INCOMPLETE')
        result['publisher_discovery']=discovered
        def control(paused):
            response=call(env,['gz','service','-s','/world/'+WORLD+'/control',
                '--reqtype','gz.msgs.WorldControl','--reptype','gz.msgs.Boolean',
                '--timeout','10000','--req','pause: '+str(paused).lower()],timeout=14)
            if response['returncode'] or 'data: true' not in response['stdout'].lower():
                raise RuntimeError('R02_WORLD_CONTROL_FAILED')
        # New diagnostic window, not the original A14 t0 observation.
        control(False)
        until=min(deadline,time.monotonic()+OBSERVE_S)
        while time.monotonic()<until:
            live()
            rclpy.spin_once(node,timeout_sec=.005)
            if start is None and clocks and clocks[-1]>0:
                start=clocks[-1]
                end=start+SPAN
            if start is not None and clocks[-1]>=end: break
            if overflow: raise RuntimeError('R02_BUFFER_OVERFLOW')
        else: raise RuntimeError('R02_SIM_CLOCK_WINDOW_INCOMPLETE')
        control(True)
        drain_until=min(deadline,time.monotonic()+1)
        while time.monotonic()<drain_until:
            rclpy.spin_once(node,timeout_sec=.005)
    except BaseException as exc:
        result['first_error']=str(exc) or type(exc).__name__
    finally:
        cleanup=[]
        for p in reversed(procs):
            try: stop_owned(p)
            except Exception as exc:
                if not result['first_error']: result['first_error']='R02_CLEANUP_'+str(exc)
            cleanup.append(dict(pid=p.pid,returncode=p.poll(),stopped=p.poll() is not None))
        for log in logs: log.close()
        if node is not None: node.destroy_node()
        if initialized:
            import rclpy
            if rclpy.ok(): rclpy.shutdown()
        result['cleanup']=cleanup
        result['all_owned_processes_stopped']=all(x['stopped'] for x in cleanup)
        jsonl(folder/'ros_contacts.jsonl',ros)
        jsonl(folder/'ros_clock.jsonl',[{'sim_ns':t} for t in clocks])
        if result['first_error'] is None:
            try:
                rows,ecm_overflow=read_ecm(folder/'ecm_contact_steps.tsv')
                result.update(assess(expected,rows,ros,clocks,start,end,STEP,
                              discovered=discovered,overflow=overflow or ecm_overflow))
                if not result['diagnostic_capture_pass']:
                    result['first_error']='R02_ECM_OR_ROS_COVERAGE_INCOMPLETE'
            except Exception as exc: result['first_error']=str(exc) or type(exc).__name__
        if not result['all_owned_processes_stopped'] or result['first_error']:
            result['diagnostic_capture_pass']=False
        result['wall_elapsed_seconds']=round(time.monotonic()-started,3)
        dump(folder/'health_result.json',result)
        archive(folder)
    print('R02_PRODUCTION_CONTACT_HEALTH=HOLD',flush=True)
    print('R02_DIAGNOSTIC_CAPTURE_PASS='+str(result['diagnostic_capture_pass']).lower(),flush=True)
    return 0 if result['diagnostic_capture_pass'] else 1


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--sha',required=True)
    p.add_argument('--plugin',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    a=p.parse_args()
    raise SystemExit(run(a.sha,a.plugin.resolve(),a.out_dir.resolve()))
