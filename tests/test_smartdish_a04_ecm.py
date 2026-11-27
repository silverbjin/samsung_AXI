import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_a04_ecm import verify_ticks,NAMES
from smartdish_a04_motion import contact_category
def fixture(tmp_path):
    pair=tmp_path/"pairs.tsv";pair.write_text("id1\tid2\tname1\tname2\n7\t127\tfloor::body::floor_collision\twaffle_pi::wheel_left_link::wheel_left_collision\n200\t201\twaffle_pi::smartdish_product_tray::platform_collision\tsmartdish_product_dish_00::body::envelope\n")
    header=['sim_ns','iteration','dt_ns','contact_components','pair_count','pairs']+[n+'_'+k for n in NAMES for k in ('id','x','y','z','qx','qy','qz','qw')]
    rows=[];legs=[]
    for i in range(6):
        start=(i*4+1)*1000000;end=start+2000000;ids=[301,302,303] if i==4 else []
        legs.append(dict(mission='a04-empty' if i<3 else 'a04-loaded',leg=('TO_TABLE','TO_RETURN','TO_HOME')[i%3],status='SUCCEEDED',start_sim_ns=start,end_sim_ns=end,loaded_entity_ids=ids))
        for n in range(3):
            stamp=start+n*1000000;robot=[89,-2.6,-2.2,.01,0,0,0,1];ds=[]
            for j in range(3):ds+=([ids[j],-2.6,-2.2,.01+.445+.037*(j+.5),0,0,0,1] if ids else [0,0,0,0,0,0,0,1])
            rows.append([stamp,stamp//1000000,1000000,28,2 if ids else 1,'7:127;200:201' if ids else '7:127',*robot,*ds])
    g={"floor":{"lo":[-5,-4.5,-.2],"hi":[5,4.5,0]},"obstacles":[],"robot_collisions":[{"link":"smartdish_product_tray","collision":"platform_collision","lo":[-.27,-.27,.415],"hi":[.27,.27,.445]},{"link":"smartdish_product_tray","collision":"mast_collision","lo":[-.2675,-.0125,.43],"hi":[-.2525,.0125,1.13]}]}
    tick=tmp_path/"ticks.tsv"
    def run():
        tick.write_text("\t".join(header)+"\n"+"\n".join("\t".join(map(str,row)) for row in rows)+"\n")
        return verify_ticks(tick,pair,legs,g,contact_category)
    return rows,run
def test_complete_fixture(tmp_path):
    rows,run=fixture(tmp_path);r=run()
    assert r['pass'] and not r['negative_contact_inferred_from_silence']
def test_gap_rejected(tmp_path):
    rows,run=fixture(tmp_path);rows.pop(1);assert not run()['pass']
def test_missing_positive_contact_not_zero(tmp_path):
    rows,run=fixture(tmp_path)
    for row in rows:row[4]=0;row[5]='-'
    assert not run()['pass']
def test_dish_displacement_rejected(tmp_path):
    rows,run=fixture(tmp_path);rows[12][15]+=.02
    assert not run()['pass']
