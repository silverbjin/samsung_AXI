"""Read-only inventory of exact existing A artifacts, using B intake/hash validation."""
import argparse,json,tempfile
from pathlib import Path
from smartdish_b_product_evidence_qa import PINS,intake

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True,type=Path);p.add_argument("--out",required=True,type=Path);a=p.parse_args()
    result=[]
    # Existing moving and focused shutdown archives only; no Gazebo replay.
    for pin in PINS[2:]:
        with tempfile.TemporaryDirectory() as tmp:
            root,meta=intake(a.input/f"github-actions-artifact-{pin[1]}.zip",Path(tmp),pin)
            names=sorted(x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file())
            candidates=[n for n in names if ("odom" in n.lower() or n.endswith((".db3",".mcap")) or "bag" in n.lower())]
            result.append(meta|dict(files=names,raw_odom_or_bag_candidates=candidates,
                sampled_pose_exists=any(n.endswith("motion_pose.jsonl") for n in names)))
    a.out.write_text(json.dumps(dict(scope="EXISTING_A_ARTIFACT_INVENTORY_ONLY",sessions=result),indent=2)+"\n")
    print(json.dumps([dict(run=x["run_id"],candidates=x["raw_odom_or_bag_candidates"],sampled_pose=x["sampled_pose_exists"]) for x in result]))
if __name__=="__main__":main()
