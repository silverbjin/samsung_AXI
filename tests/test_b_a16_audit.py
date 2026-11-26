import io,sys,tarfile,hashlib,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ai/scripts"))
from audit_b_a16 import read_tar,hold,canonical,need,QAError,SCENES,RAW,DIAGNOSTICS,OUTER,cleanup
def package(files):
    b=io.BytesIO();s="".join(hashlib.sha256(v).hexdigest()+"  "+k+"\n" for k,v in files.items()).encode()
    with tarfile.open(fileobj=b,mode="w:gz") as t:
        for k,v in {**files,"SHA256SUMS":s}.items():
            m=tarfile.TarInfo(k);m.size=len(v);t.addfile(m,io.BytesIO(v))
    return b.getvalue()
class QA04(unittest.TestCase):
    def test_allowlist(self):
        b=package({"x":b"a"});self.assertEqual(read_tar(b,hashlib.sha256(b).hexdigest(),allowed={"x"}),{"x":b"a"})
        with self.assertRaises(QAError):read_tar(b,hashlib.sha256(b).hexdigest(),allowed={"y"})
    def test_wrong_sha(self):
        with self.assertRaises(QAError):read_tar(package({"x":b"a"}),"0"*64,allowed={"x"})
    def test_traversal(self):
        b=package({"../x":b"a"})
        with self.assertRaises(QAError):read_tar(b,hashlib.sha256(b).hexdigest(),allowed={"../x"})
    def test_gt(self):
        hold(dict(human_approved=False,training_eligible=False,ground_truth="UNKNOWN_HOLD"))
        with self.assertRaises(QAError):hold(dict(human_approved=True,training_eligible=False,ground_truth="UNKNOWN_HOLD"))
    def test_exact_manifest_contract(self):
        self.assertEqual((len(SCENES),len(RAW),len(OUTER),len(DIAGNOSTICS)),(8,15,17,57))
    def test_cleanup_residual_and_separate(self):
        roles=["gui","server","native_contact","rgb_bridge","contact_bridge"]
        v={"all_owned_stopped":True,"gui":"PASS","cleanup":"FAIL","processes":[{"role":n,"returncode":-11 if n=="server" else 0,"signals":[2],"stopped":True,"process_group_remaining":False} for n in roles]}
        self.assertEqual(cleanup(v)["server_rc"],-11)
        v["processes"][0]["process_group_remaining"]=True
        with self.assertRaises(QAError):cleanup(v)
if __name__=="__main__":unittest.main()
