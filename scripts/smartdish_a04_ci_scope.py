"""A04 exact incremental CI scope: do not repeat immutable PASS on docs commits."""
import argparse,subprocess

def classify(paths):
    static=False;motion=False
    for p in paths:
        if p in ("scripts/smartdish_a04_clearance.py","tests/test_smartdish_a04_clearance.py","scripts/smartdish_product_scene.py","scripts/smartdish_product_robot.py","scripts/s6_scene.py","scripts/s7_scene.py","scripts/smartdish_tray_camera.py") or p.startswith(("maps/","src/restaurant_world/")):
            static=True
        if p.startswith(("scripts/smartdish_a04_","tests/test_smartdish_a04_","src/restaurant_bringup/","src/smartdish_robot/")) and p!="scripts/smartdish_a04_ci_scope.py" and p!="tests/test_smartdish_a04_ci_scope.py":
            motion=True
        if p in ("scripts/prepare_nav2_params.py","scripts/smartdish_product_startup_probe.py"):motion=True
    # Motion always executes its own exact same-session actual NO_GOAL gate.
    # The original-map negative and previous candidate planning proof stay immutable.
    return {"geometry":static,"no-goal":False,"motion":static or motion}

def main():
    p=argparse.ArgumentParser();p.add_argument("--before",default="");p.add_argument("--head",required=True)
    p.add_argument("--kind",choices=("geometry","no-goal","motion"),required=True)
    p.add_argument("--force",action="store_true");a=p.parse_args()
    try:
        if not a.before or a.before=="0"*40:raise ValueError("NO_BASE")
        paths=subprocess.check_output(["git","diff","--name-only",a.before,a.head,"--"],text=True).splitlines()
        run=classify(paths)[a.kind]
        print("scope="+",".join(paths))
    except (ValueError,subprocess.CalledProcessError):
        # No valid before SHA: conservatively do required static and moving
        # verification; do not duplicate no-goal already included in moving.
        run=a.kind!="no-goal"
        print("scope=BASE_UNAVAILABLE_CONSERVATIVE")
    print("run="+str(a.force or run).lower())
if __name__=="__main__":main()
