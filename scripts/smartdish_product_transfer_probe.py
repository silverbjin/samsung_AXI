#!/usr/bin/env python3
"""Actual isolated no-goal LOAD/capture/removal witness for A-PROD-03.

This is NOT a production transfer controller or ACK publisher. The robot stays
stationary; virtual staff acts through real Gazebo services. E/D must approve
the Nav2 UUID/terminal/stop handshake before product requests are connected.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
from xml.etree import ElementTree as ET
from smartdish_product_startup_probe import TRAY_TOPIC

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from smartdish_robot.product_physics import PhysicalOperations
from smartdish_robot.product_gazebo_backend import DISH_NAMES,FIXTURE,GazeboEntityServices

ROBOT="waffle_pi"
POSE_PREFIX="/smartdish/product/gz_pose/"

class TransferProbe(PhysicalOperations):
    def execute(self,out,scene):
        from PIL import Image
        ev={"scope":"CI_NO_GOAL_PHYSICAL_TRANSFER_WITNESS_NOT_PRODUCT_ACK",
            "stack_id":scene["stack_id"],"verdict":"NOT_RUN","first_error":None}
        d=out/"transfer";d.mkdir()
        services=GazeboEntityServices(d,timeout_s=2.)
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        try:
            models=services.scene()
            if scene["scenario"]=="empty":
                if FIXTURE in models or any(n in models for n in DISH_NAMES):
                    raise RuntimeError("EMPTY_TABLE_ENTITY_CONFLICT")
                ev.update(verdict="ACTUAL_EMPTY_TABLE_NO_MUTATION",reason="EMPTY_TABLE")
                return ev
            if FIXTURE not in models or any(n in models for n in DISH_NAMES):
                raise RuntimeError("INITIAL_ENTITY_CONFLICT")
            ev["initial_fixture_entity_id"]=models[FIXTURE]
            obs,elapsed=self.load(out,scene,services,models[FIXTURE])
            ids=obs["entity_ids"]
            ev["load"]=obs
            ev["load_wall_s"]=elapsed
            frame=self.until(lambda:self.cache.select(obs["event_sim_ns"],time.monotonic()),8,"POST_LOAD_RGB_TIMEOUT")
            png=d/"captured.png";raw=d/"captured.rgb"
            Image.frombytes("RGB",(640,480),frame.rgb).save(png);raw.write_bytes(frame.rgb)
            ev["capture"]={"image_stamp_ns":frame.stamp_ns,"frame_id":frame.frame_id,
                           "rgb_sha256":frame.rgb_sha256,"png_sha256":sha(png),
                           "width":640,"height":480,"encoding":frame.encoding,
                           "min_sim_stamp_ns":obs["event_sim_ns"]}
            if sha(raw)!=frame.rgb_sha256:raise RuntimeError("CAPTURE_HASH_DRIFT")
            # The removal receipt is the permitted simulated handover method;
            # this isolated test has no actual DISH_RETURN arrival.
            ev["unload"],ev["unload_wall_s"]=self.unload(services,ids)
            ev["verdict"]="ACTUAL_STATIONARY_LOAD_CAPTURE_REMOVE_OBSERVED"
            return ev
        except BaseException as exc:
            ev["first_error"]=repr(exc);ev["verdict"]="FAIL"
            raise
        finally:
            log=d/"gazebo_service_calls.jsonl"
            if log.exists():ev["service_calls_sha256"]=sha(log)
            (d/"transfer_evidence.json").write_text(json.dumps(ev,sort_keys=True,indent=2)+"\n")
