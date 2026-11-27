"""Real Owner C inference only. Uses installed C model_runtime, no double or test image."""
import argparse,hashlib,json,os,sys,time
from collections import OrderedDict
from pathlib import Path
from smartdish_e_product_owner_scope import require_owner,MODEL_VERSION,MODEL_SHA,MODEL_SCOPE,model_receipt

def write_json(path,body):
    with path.open("x") as f:json.dump(body,f,sort_keys=True,allow_nan=False);f.write("\n")
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True);p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--pin",required=True);p.add_argument("--run-id",required=True);a=p.parse_args()
    require_owner(a.pin,a.run_id)
    import rclpy
    from rclpy.parameter import Parameter
    from rclpy.executors import ExternalShutdownException
    from smartdish_ai.product_stability_inference_node import ProductStabilityInferenceNode
    from smartdish_ai.model_runtime import load_predictor,OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256
    if OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256!=MODEL_SHA:raise RuntimeError("E_OWNER_C_PIN_DRIFT")
    meta=dict(scope=MODEL_SCOPE,private_model_loaded=True,checkpoint_sha256=MODEL_SHA,
              model_version=MODEL_VERSION,test4_opened=False,general_product_approved=False)
    class RealObservedC(ProductStabilityInferenceNode):
        def __init__(self):
            self.raw=OrderedDict();self.real=None
            def load(path,**kwargs):
                if path!=a.checkpoint or path.is_symlink() or sha(path.read_bytes())!=MODEL_SHA or kwargs!={"owner_gazebo_integration":True}:
                    raise RuntimeError("E_OWNER_MODEL_PIN")
                self.real,version=load_predictor(path,**kwargs)
                if version!=MODEL_VERSION:raise RuntimeError("E_OWNER_VERSION")
                import torch,torchvision,numpy,PIL
                site=Path(os.environ["SMARTDISH_E_C_SITE_PACKAGES"]).resolve()
                versions={"torch":"2.5.1+cpu","torchvision":"0.20.1+cpu","numpy":"1.26.4","PIL":"10.2.0"}
                for module in (torch,torchvision,numpy,PIL):
                    if not Path(module.__file__).resolve().is_relative_to(site) or module.__version__!=versions[module.__name__]:
                        raise RuntimeError("E_OWNER_C_RUNTIME_ORIGIN")
                if torch.version.cuda is not None:raise RuntimeError("E_OWNER_C_CPU_REQUIRED")
                self.versions=versions
                return self.predict,version
            super().__init__(parameter_overrides=[Parameter("owner_gazebo_integration",value=True),
                 Parameter("model_path",value=str(a.checkpoint))],predictor_loader=load)
            if self.core.predictor is None or self.core.model_version!=MODEL_VERSION or self.real is None:
                raise RuntimeError("E_OWNER_ACTUAL_MODEL_NOT_LOADED")
            tmp=a.out/"owner_c_loaded.tmp";write_json(tmp,meta|{"versions":self.versions,"bytes":a.checkpoint.stat().st_size})
            os.replace(tmp,a.out/"owner_c_loaded.json")
        def _image(self,msg):
            stamp=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
            if stamp not in self.raw:
                self.raw[stamp]=(bytes(msg.data),dict(image_stamp_ns=stamp,frame_id=msg.header.frame_id,
                    width=msg.width,height=msg.height,encoding=msg.encoding,step=msg.step,is_bigendian=msg.is_bigendian))
                while len(self.raw)>16:self.raw.popitem(last=False)
            super()._image(msg)
        def predict(self,rgb,w,h):
            req=self.core.pending["request"];raw,raw_meta=self.raw[req["image_stamp_ns"]]
            if (w,h)!=(640,480) or sha(rgb)!=req["rgb_sha256"]:raise RuntimeError("E_OWNER_RGB")
            status,confidence=self.real(rgb,w,h)
            with (a.out/"c_input.rgb").open("xb") as f:f.write(rgb)
            with (a.out/"c_input_ros_bytes.bin").open("xb") as f:f.write(raw)
            write_json(a.out/"c_predictor_receipt.json",meta|dict(invocation_count=1,request=req,raw_metadata=raw_meta,
                rgb_sha256=sha(rgb),raw_sha256=sha(raw),steady_s=time.monotonic(),prediction={"status":status,"confidence":confidence}))
            return status,confidence
    rclpy.init();node=None
    try:
        node=RealObservedC();rclpy.spin(node)
    except (KeyboardInterrupt,ExternalShutdownException):pass
    finally:
        if node is not None:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=="__main__":main()
