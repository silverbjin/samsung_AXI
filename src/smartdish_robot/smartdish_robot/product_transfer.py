"""Product transfer controller: actual A-owned backend, trusted nav receipt.

Call from A's dedicated runtime loop, NOT from a ROS subscription callback.
No new public topics or fake Nav2 result. E supplies the approved wiring
and timing; the default five-second deadline remains fail-closed.
"""
from pathlib import Path
import time
from .product_contract import (
    COMMON, ContractError, TransactionJournal, canonical_json, digest,
    parse_transfer, require,
)
from .product_gazebo_backend import GazeboEntityServices, DISH_NAMES

class ProductTransferController:
    def __init__(self,nav,physics,scene,world_dir,evidence_dir,source_sha,
                 *,timeout_s=5.,clock=time.monotonic,run_id=None):
        require(type(timeout_s) in (int,float) and 0<timeout_s<=30.,"TRANSFER_TIMEOUT_INVALID")
        require(isinstance(source_sha,str) and len(source_sha)==40 and
                all(c in "0123456789abcdef" for c in source_sha),"SOURCE_SHA")
        self.nav=nav;self.physics=physics;self.scene=scene
        self.world_dir=Path(world_dir);self.root=Path(evidence_dir)
        self.root.mkdir(parents=True,exist_ok=True)
        self.journal=TransactionJournal(self.root/"transfers")
        self.clock=clock;self.timeout=timeout_s;self.source_sha=source_sha
        self.run_id=run_id or scene["run_id"]
        self.initial=None;self.loaded_ids=None;self.load_request=None
        self.stage="UNARMED";self.active=False;self.locked=self.journal.locked
        self.arrival_at=None;self.arrival_uuid=None

    def arm_verified(self):
        require(not self.locked and not self.active and self.stage=="UNARMED"
                and self.nav.active is None,"ARM_LOCKED")
        if self.journal.path.exists():
            # Recovery/restart needs operator and a new mission run.
            raise ContractError("EXISTING_TRANSFER_JOURNAL_RECOVERY_REQUIRED")
        require(self.scene["scenario"] in ("stacked","empty"),"SCENE_INVALID")
        services=GazeboEntityServices(self.root/"startup",timeout_s=2.)
        obs=self.physics.initial_observation(services,self.scene)
        self.physics.wait_stop()
        require(obs["robot_entity_id"] is not None,"ROBOT_ENTITY_MISSING")
        self.initial=obs;self.stage="TABLE" if obs["table_count"]==3 else "EMPTY"
        receipt={"kind":"ACTUAL_STARTUP_ENTITY_AND_STOP","source_sha":self.source_sha,
                 "run_id":self.run_id,"world_sha256":self.scene["world_sha256"],
                 "observation":obs}
        path=self.root/"startup"/"ready.json"
        with path.open("xb") as f:f.write(canonical_json(receipt))
        return receipt|{"receipt_sha256":digest(path.read_bytes())}

    def note_arrival(self):
        # Only the in-process nav boundary can provide this receipt.
        receipt=self.nav.last_receipt
        require(receipt is not None and receipt["terminal_status"]=="SUCCEEDED"
                and receipt["stop_verified"] is True and self.nav.active is None,
                "NAV_TERMINAL_STOP_NOT_PROVEN")
        if self.arrival_uuid!=receipt["goal_uuid"]:
            self.arrival_uuid=receipt["goal_uuid"];self.arrival_at=self.clock()
        return receipt

    def can_start_leg(self,request):
        if self.locked or self.active or self.journal.locked or self.nav.locked:
            return False
        leg=request.get("leg")
        return ((leg=="TO_TABLE" and self.stage in ("TABLE","EMPTY") and self.arrival_uuid is None)
                or (leg=="TO_RETURN" and self.stage=="ON_ROBOT"
                    and self.load_request is not None and request.get("request_id")==self.load_request)
                or (leg=="TO_HOME" and self.stage=="RETURNED"
                    and request.get("request_id")==self.load_request))

    def run(self,request):
        req=parse_transfer(canonical_json(request))
        require(not self.active,"TRANSFER_BUSY")
        require(req["stack_id"]==self.scene["stack_id"],"STACK_ID_MISMATCH")
        # Duplicate ACK/FAILED replay does not repeat any physical operation.
        old=self.journal.begin(req)
        if old is not None:return old
        self.active=True;deadline=self.clock()+self.timeout
        old_guard=self.physics.guard
        services=None
        def check():
            require(self.clock()<deadline,"TRANSFER_DEADLINE")
            require(self.nav.active is None and not self.nav.locked and not self.locked,
                    "TRANSFER_NAV_OR_RUNTIME_LOCKED")
        self.physics.guard=check
        base={k:req[k] for k in COMMON|{"operation"}}
        evidence={"kind":"ACTUAL_NAV2_TERMINAL_AND_GAZEBO_"+req["operation"],
                  "source_sha":self.source_sha,"run_id":self.run_id,
                  "world_id":"restaurant","world_sha256":self.scene["world_sha256"]}
        try:
            check()
            receipt=self.note_arrival()
            require(receipt["request_id"]==req["request_id"] and
                    receipt["destination_id"]==req["destination_id"],"ARRIVAL_ID_MISMATCH")
            wait=10. if req["operation"]=="LOAD" else 5.
            require(self.clock()-self.arrival_at>=wait,"TRANSFER_BEFORE_WAIT")
            evidence["navigation"]=receipt
            self.physics.wait_stop()
            check()
            # Hash the external ID for a path; never interpolate it as a path.
            services=GazeboEntityServices(self.root/"physical"/digest(req["transfer_id"].encode()),timeout_s=2.)
            if req["operation"]=="LOAD":
                require(self.stage in ("TABLE","EMPTY"),"LOAD_STAGE")
                require(self.initial is not None and self.initial["table_count"]==3,"EMPTY_TABLE")
                obs,elapsed=self.physics.load(self.world_dir,self.scene,services,
                                               self.initial["fixture_entity_id"])
                ids=obs["entity_ids"];event=obs["event_sim_ns"]
                location="ON_ROBOT";tray_count=3
                evidence.update(observation=obs,elapsed_s=elapsed)
            else:
                require(self.stage=="ON_ROBOT" and self.load_request==req["request_id"]
                        and self.loaded_ids is not None,"UNLOAD_STAGE")
                obs,elapsed=self.physics.unload(services,self.loaded_ids)
                ids=obs["removed_entity_ids"];event=obs["event_sim_ns"]
                require(ids==self.loaded_ids,"UNLOAD_ENTITY_ID_DRIFT")
                location="RETURNED";tray_count=0
                evidence.update(observation=obs,elapsed_s=elapsed)
            check()
            log=services.root/"gazebo_service_calls.jsonl"
            require(log.is_file(),"SERVICE_EVIDENCE_MISSING")
            evidence["service_calls_sha256"]=digest(log.read_bytes())
            evidence["service_receipt_dir"]=services.root.relative_to(self.root).as_posix()
            # ROS control IDs are strings; raw Gazebo numeric IDs stay in evidence.
            result=base|{"status":"ACK","reason":"","entity_ids":[str(i) for i in ids],
                         "location":location,"tray_count":tray_count,"table_count":0,
                         "event_sim_ns":event}
            result=self.journal.finish(req,result,evidence)
            self.stage=location
            if req["operation"]=="LOAD":
                self.loaded_ids=ids;self.load_request=req["request_id"]
            # A late commit is never sent as a valid product ACK.
            if self.clock()>=deadline:
                self.locked=True
                raise ContractError("TRANSFER_RECEIPT_LATE_NO_ACK")
            return result
        except Exception as exc:
            self.locked=True;self.stage="UNKNOWN"
            evidence["first_error"]=repr(exc)
            if services:
                log=services.root/"gazebo_service_calls.jsonl"
                if log.exists():evidence["service_calls_sha256"]=digest(log.read_bytes())
            # Unknown partial physical state: never fabricate counts or publish ACK.
            # Keep pending journal locked if failure receipt cannot be committed.
            if self.journal.locked:
                result=base|{"status":"FAILED","reason":str(exc),"entity_ids":[],
                             "location":"UNKNOWN","tray_count":None,"table_count":None,
                             "event_sim_ns":self.physics.clock[-1] if self.physics.clock else None}
                return self.journal.finish(req,result,evidence)
            raise
        finally:
            self.physics.guard=old_guard;self.active=False
