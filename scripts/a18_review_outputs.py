"""Private review copies from actual t0 RGB: projected BBOX, not segmentation or labels."""
import csv,json,sys
from pathlib import Path
from PIL import Image,ImageDraw
from a18_pilot_world import phase_scenes
def main(root,phase):
    root=Path(root);rows=[]
    for scene in phase_scenes(phase):
        p=root/scene;d=json.loads((p/"a18_design.json").read_text());iv=json.loads((p/"initial_validity.json").read_text())
        with Image.open(p/"tray_rgb_t0.png") as src:
            im=src.convert("RGB");draw=ImageDraw.Draw(im)
            for name,x in iv["dishes"].items():
                bbox=x["conservative_projected_bbox_px"];draw.rectangle(bbox,outline="magenta",width=2);draw.text((bbox[0],bbox[1]),name,fill="white",stroke_width=1,stroke_fill="black")
            im.save(p/"roi_review.png")
        rows.append({"scene_id":scene,"layout_id":d["physical_layout_id"],"scope":"BBOX_ONLY_NOT_MASK","initial_placement":"","occlusion":"","physics_validity":"","learning_suitability":"","license_status":"","gt_decision":"","reviewer":"","reason":""})
    with (root/"review_worksheet.csv").open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
if __name__=="__main__":main(sys.argv[1],int(sys.argv[2]))
