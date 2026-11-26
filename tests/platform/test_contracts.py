import hashlib,io,json,os,signal,subprocess,sys,tarfile,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from smartdish_platform.runtime import gui_profile,renderer_env,workload_env
from smartdish_platform.lifecycle import stop_owned
from smartdish_platform.evidence import verify_archive,evidence_state
from smartdish_platform.baseline import check

class Contracts(unittest.TestCase):
    def test_gui_profile(self):
        src=dict(DISPLAY=":0",WAYLAND_DISPLAY="wayland-0",GALLIUM_DRIVER="d3d12",MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA")
        copy=dict(src);out=gui_profile(src,"xcb_software")
        self.assertEqual(src,copy);self.assertEqual(out["GALLIUM_DRIVER"],"llvmpipe")
        self.assertEqual(out["LIBGL_ALWAYS_SOFTWARE"],"1")
        self.assertNotIn("MESA_D3D12_DEFAULT_ADAPTER_NAME",out);self.assertNotIn("WAYLAND_DISPLAY",out)
        self.assertEqual(gui_profile(src,"xcb")["GALLIUM_DRIVER"],"d3d12")
        self.assertEqual(renderer_env(src,False),src)
        with self.assertRaises(ValueError):gui_profile({},"xcb_software")
        with self.assertRaises(ValueError):gui_profile(src,"unknown")
    def test_offline(self):
        e={"CUDA_VISIBLE_DEVICES":"0","GALLIUM_DRIVER":"d3d12"}
        self.assertEqual(workload_env(e,"B")["CUDA_VISIBLE_DEVICES"],"")
        self.assertEqual(workload_env(e,"C",gpu=True),e)
        self.assertEqual(e["CUDA_VISIBLE_DEVICES"],"0")
        with self.assertRaises(ValueError):workload_env(e,"B",gpu=True)
    def test_offline_cli(self):
        e=dict(os.environ,CUDA_VISIBLE_DEVICES="0",GALLIUM_DRIVER="d3d12")
        runner=Path(__file__).resolve().parents[2]/"scripts/smartdish_platform/runtime.py"
        out=subprocess.check_output([sys.executable,str(runner),"--role","B","--",sys.executable,"-c","import os; print(os.environ[\'CUDA_VISIBLE_DEVICES\']+\'|\'+os.environ[\'GALLIUM_DRIVER\'])"],env=e,text=True).strip()
        self.assertEqual(out,"|d3d12");self.assertEqual(e["CUDA_VISIBLE_DEVICES"],"0")
    def test_owned_process(self):
        p=subprocess.Popen(["sleep","30"],start_new_session=True)
        try:
            r=stop_owned(p,int_timeout=.5,term_timeout=.5,kill_timeout=.5)
            self.assertTrue(r["stopped"]);self.assertEqual(r["returncode"],-signal.SIGINT)
        finally:
            if p.poll() is None:p.kill();p.wait()
        p=subprocess.Popen(["sleep","30"])
        try:
            with self.assertRaises(ValueError):stop_owned(p)
        finally:p.terminate();p.wait()
    def test_independent_verdict(self):
        r=evidence_state("PASS","FAIL","FAIL",True)
        self.assertTrue(r["next_independent_scene_allowed"]);self.assertEqual(r["cleanup"],"FAIL")
        self.assertFalse(r["human_approved"])
        self.assertFalse(evidence_state("HOLD","PASS","PASS",True)["next_independent_scene_allowed"])
        self.assertFalse(evidence_state("PASS","PASS","FAIL",False)["next_independent_scene_allowed"])
    def test_archive(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.tar.gz"
            def create(items):
                with tarfile.open(p,"w:gz") as t:
                    for n,b in items:
                        m=tarfile.TarInfo(n);m.size=len(b);t.addfile(m,io.BytesIO(b))
                return hashlib.sha256(p.read_bytes()).hexdigest()
            raw=b"original";h=hashlib.sha256(raw).hexdigest()
            items=[("raw",raw),("SHA256SUMS",(h+"  raw\n").encode())]
            self.assertEqual(verify_archive(p,create(items))["manifest_count"],1)
            with self.assertRaises(ValueError):verify_archive(p,"0"*64)
            for bad in [items+[("../bad",b"x")],items+[("raw",raw)],items+[("unlisted",b"x")],[("raw",b"wrong"),items[1]]]:
                with self.assertRaises(ValueError):verify_archive(p,create(bad))
    def test_baseline_gate(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            def g(*a):return subprocess.check_output(["git","-C",td,*a],text=True,stderr=subprocess.DEVNULL).strip()
            g("init","-q");g("config","user.name","CI");g("config","user.email","ci@example.invalid")
            (p/"config").mkdir();(p/"config/smartdish_platform_baseline.json").write_text(json.dumps({"version":"fixture","protected_paths":["shared","config"]}))
            (p/"shared").write_text("approved");g("add",".");g("commit","-qm","baseline");pin=g("rev-parse","HEAD")
            (p/"feature").write_text("new");g("add",".");g("commit","-qm","feature")
            self.assertEqual(check(p,pin)["verdict"],"PASS")
            (p/"shared").write_text("regression");g("add",".");g("commit","-qm","drift")
            with self.assertRaisesRegex(ValueError,"DRIFT"):check(p,pin)
if __name__=="__main__":unittest.main()
