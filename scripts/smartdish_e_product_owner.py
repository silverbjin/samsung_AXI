"""WSL2 actual private-model product candidate using the shared accepted E runner."""
import argparse,functools
from pathlib import Path
from smartdish_e_product_owner_scope import require_owner
def main():
    p=argparse.ArgumentParser()
    for k in ("out","robot-source","bridge-source","world-source","map","poses","params","observer-plugin","checkpoint"):
        p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--pin",required=True);p.add_argument("--run-id",required=True);a=p.parse_args()
    require_owner(a.pin,a.run_id)
    from smartdish_a04_no_goal import run
    from smartdish_e_product_session import session
    owner=dict(pin=a.pin,run_id=a.run_id,checkpoint=str(a.checkpoint))
    a.mode="candidate";a.motion=True;a.mission="product"
    run(a,product_session=functools.partial(session,owner=owner),owner=owner)
if __name__=="__main__":main()
