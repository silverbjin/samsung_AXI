"""A-PROD-03 opt-in exact-frame capture receipt writer.

The producer must be A's trusted transfer journal, not a ROS result message.
No inference, label, navigation, or implicit profile enablement.
"""
import json
from pathlib import Path
import os
from .product_contract import (
    COMMON, FRAME, ContractError, canonical_json, digest, parse_capture, require,
)

class CaptureStore:
    def __init__(self,root,transfer_journal):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.transfer_journal=transfer_journal

    def _directory(self,request):
        return self.root/digest(request["capture_id"].encode("utf-8"))

    def _load(self,request):
        r,receipt=self.transfer_journal.load_receipt(
            request["request_id"],request["stack_id"],request["transfer_id"])
        require(request["min_sim_stamp_ns"]>=r["event_sim_ns"],"CAPTURE_BEFORE_LOAD")
        return r,receipt

    def reserve(self,request):
        request=parse_capture(canonical_json(request))
        d=self._directory(request)
        if d.exists():
            require((d/"request.json").is_file() and
                    (d/"request.json").read_bytes()==canonical_json(request),
                    "CAPTURE_ID_CONFLICT")
            require((d/"result.json").is_file(),"CAPTURE_RECOVERY_REQUIRED")
            result=json.loads((d/"result.json").read_bytes())
            receipt=(d/"receipt.json").read_bytes()
            require(result.get("receipt_sha256")==digest(receipt),"CAPTURE_RECEIPT_CORRUPT")
            stored=json.loads(receipt)
            require(stored["result"]=={k:v for k,v in result.items() if k!="receipt_sha256"},
                    "CAPTURE_RESULT_DRIFT")
            if result["status"]=="ACK":
                require(digest((d/"frame.rgb").read_bytes())==result["rgb_sha256"] and
                        digest((d/"frame.png").read_bytes())==stored["png_sha256"],
                        "CAPTURE_FILE_CORRUPT")
            return result
        # Single A capture node owns this directory; reject a second capture
        # for the same LOAD, including pending/failed earlier capture.
        for p in self.root.glob("*/request.json"):
            old=json.loads(p.read_bytes())
            require(old.get("transfer_id")!=request["transfer_id"],"CAPTURE_ALREADY_RESERVED")
        self._load(request)
        d.mkdir(exist_ok=False)
        (d/"request.json").write_bytes(canonical_json(request))
        return None

    def complete(self,request,frame,now):
        from PIL import Image
        d=self._directory(request)
        require((d/"request.json").read_bytes()==canonical_json(request)
                and not (d/"result.json").exists(),"CAPTURE_NOT_PENDING")
        load,_=self._load(request)
        require(frame.frame_id==FRAME and frame.stamp_ns>request["min_sim_stamp_ns"]
                and 0<=now-frame.received_at<=2. and len(frame.rgb)==640*480*3
                and digest(frame.rgb)==frame.rgb_sha256,"FRAME_INVALID")
        raw=d/"frame.rgb";png=d/"frame.png"
        with raw.open("xb") as f:f.write(frame.rgb)
        if png.exists():raise ContractError("CAPTURE_PNG_ALREADY_EXISTS")
        Image.frombytes("RGB",(640,480),frame.rgb).save(png)
        result={k:request[k] for k in COMMON|{"capture_id"}}
        result.update(status="ACK",reason="",image_stamp_ns=frame.stamp_ns,
                      frame_id=frame.frame_id,rgb_sha256=frame.rgb_sha256,
                      width=640,height=480,encoding=frame.encoding)
        receipt={"result":result,"load_receipt_sha256":load["receipt_sha256"],
                 "min_sim_stamp_ns":request["min_sim_stamp_ns"],"png_sha256":digest(png.read_bytes()),
                 "rgb_file":"frame.rgb","png_file":"frame.png"}
        return self._finish(d,result,receipt)

    def fail(self,request,reason):
        d=self._directory(request)
        require((d/"request.json").read_bytes()==canonical_json(request)
                and not (d/"result.json").exists(),"CAPTURE_NOT_PENDING")
        result={k:request[k] for k in COMMON|{"capture_id"}}
        # Failure has no image. Null image values are an explicit candidate
        # pending D/E confirmation; product activation remains blocked.
        result.update(status="FAILED",reason=reason,image_stamp_ns=None,frame_id=None,
                      rgb_sha256=None,width=None,height=None,encoding=None)
        return self._finish(d,result,{"result":result})

    def _finish(self,d,result,receipt):
        raw=canonical_json(receipt)
        with (d/"receipt.json").open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
        result=dict(result,receipt_sha256=digest(raw))
        with (d/"result.json").open("xb") as f:
            f.write(canonical_json(result));f.flush();os.fsync(f.fileno())
        return result
