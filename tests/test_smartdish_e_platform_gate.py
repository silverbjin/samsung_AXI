import json,sys,tempfile,subprocess,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_e_platform_gate import validate
class Gate(unittest.TestCase):
    def test_gate(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            def g(*a):return subprocess.check_output(["git","-C",td,*a],text=True,stderr=subprocess.DEVNULL).strip()
            g("init","-q");g("config","user.name","fixture");g("config","user.email","ci@example.invalid")
            (p/"config").mkdir();(p/"config/smartdish_platform_baseline.json").write_text(json.dumps({"version":"fixture","protected_paths":["config/smartdish_platform_baseline.json"]}))
            g("add",".");g("commit","-qm","stable");pin=g("rev-parse","HEAD")
            roles={}
            for r in ("A","B","C","D"):
                (p/r).write_text("fixture");g("add",".");g("commit","-qm",r)
                roles[r]={"source_sha":g("rev-parse","HEAD"),"approval":"APPROVED","scoped_ci":"PASS","ci_run_ids":[1],"owner_required":False}
            m={"schema":1,"platform_sha":pin,"roles":roles}
            self.assertEqual(validate(p,m,pin)["integration_inputs"],"PASS")
            roles["A"]["approval"]="HOLD"
            self.assertEqual(validate(p,m,pin)["integration_inputs"],"HOLD")
            roles["A"]["approval"]="APPROVED";roles["A"]["owner_required"]=True;roles["A"]["owner_verdict"]="HOLD"
            self.assertIn("OWNER_EVIDENCE_NOT_ACCEPTED",validate(p,m,pin)["roles"]["A"]["problems"])
            roles["A"]["owner_required"]=False;roles["A"]["source_sha"]="0"*40
            self.assertIn("ROLE_NOT_IN_CANDIDATE",validate(p,m,pin)["roles"]["A"]["problems"])
if __name__=="__main__":unittest.main()
