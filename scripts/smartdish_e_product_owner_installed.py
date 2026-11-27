"""Verify exact installed bytes for actual product A/C/D, in addition to legacy guard."""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
from smartdish_e_installed_origin import inspect,same_bytes
EXTRA={
 "smartdish_robot":("product_contract","product_runtime","product_navigation","product_goal_gate","product_transfer","product_physics","product_gazebo_backend","product_capture","product_capture_node"),
 "smartdish_ai":("product_stability_inference_node","product_inference","model_runtime"),
 "smartdish_service":("product_recovery_fsm","product_recovery_transport","product_recovery_ui","product_recovery_thresholds","product_admission"),
}
def main():
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--pin",required=True)
    p.add_argument("--install-base",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    result=inspect(a.root,a.pin,a.install_base,list(EXTRA))
    for pkg,mods in EXTRA.items():
        for mod in mods:
            spec=importlib.util.find_spec(pkg+"."+mod)
            if not spec or not spec.origin:raise RuntimeError("E_OWNER_PRODUCT_MODULE_MISSING:"+pkg+"."+mod)
            path=Path(spec.origin);source=a.root/"src"/pkg/pkg/(mod+".py")
            result["records"].append(dict(package=pkg,module=mod,installed_path=str(path),
                sha256=same_bytes(path,source),source_path=str(source)))
    with a.out.open("x") as f:json.dump(result,f,indent=2);f.write("\n")
    print("E_OWNER_PRODUCT_INSTALLED_MODULE_BYTES_MATCH")
if __name__=="__main__":main()
