"""Execute actual B launch scripts against isolated CPU-profile sentinel children."""
import os,subprocess,tempfile,shutil,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Adoption(unittest.TestCase):
    def test_b_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"scripts/smartdish_platform").mkdir(parents=True)
            (p/"ai/scripts").mkdir(parents=True)
            shutil.copyfile(ROOT/"scripts/smartdish_platform/runtime.py",p/"scripts/smartdish_platform/runtime.py")
            for stem in ("smartdish_b12r","smartdish_b_dacon_qa01"):
                name=stem+"_one_shot.sh"
                shutil.copyfile(ROOT/"scripts"/name,p/"scripts"/name)
                (p/"ai/scripts"/(stem+"_cli.py")).write_text("import os; print(os.environ['CUDA_VISIBLE_DEVICES']+'|'+os.environ['GALLIUM_DRIVER'])\n")
                e=dict(os.environ,CUDA_VISIBLE_DEVICES="0",GALLIUM_DRIVER="d3d12")
                out=subprocess.check_output(["bash",str(p/"scripts"/name)],env=e,text=True).strip()
                self.assertEqual(out,"|d3d12");self.assertEqual(e["CUDA_VISIBLE_DEVICES"],"0")
    def test_real_importer_uses_common_profile(self):
        s=(ROOT/"scripts/smartdish_b_real_data_one_shot.sh").read_text()
        for name in ("import_a13_evidence.py","extract_a13_candidates.py","package_a13_diagnostics.py"):
            self.assertIn('runtime.py" --role B -- python3 "$ROOT/ai/scripts/'+name,s)
if __name__=="__main__":unittest.main()
