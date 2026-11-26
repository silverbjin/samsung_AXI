import ast,hashlib,json,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import a17_production_profile as p
from smartdish_platform.lifecycle import stop_owned
from a16_archive import scene_package
ENV={"GALLIUM_DRIVER":"d3d12","MESA_D3D12_DEFAULT_ADAPTER_NAME":"NVIDIA","ROS_DISTRO":"jazzy","GZ_SIM_RENDER_ENGINE":"ogre2"}
GLX="Accelerated: yes\nOpenGL renderer string: D3D12 (NVIDIA GeForce RTX 3060)\n"
def fake_run(args,env,timeout=15):
    if args[0]=="uname":return "6.18.58.1-microsoft-standard-WSL2"
    if args[0]=="gz":return "8.15.0"
    if args[0]=="dpkg-query":return p.MESA_VERSION
    if args[0]=="glxinfo":return GLX
    raise AssertionError(args)
def fake_library(name,h):return {"path":name,"realpath":name,"sha256":h,"size_bytes":123}
def good_record():
    return {"runtime_observation":{"pid":123},"runtime_observation_pre_shutdown":{"pid":123}}
def good_rows():
    return [{"role":r,"returncode":0,"stopped":True,"process_group_remaining":False,"signals":[2]} for r in ("server","native_contact","rgb_bridge","contact_bridge")]
class Profile(unittest.TestCase):
    def test_inherit_exact_and_independent(self):
        e=dict(ENV,LD_PRELOAD="existing.so");x,r=p.prepare(e,p.INHERIT,"CLOUD_CI")
        self.assertEqual(x,e);self.assertIsNone(r);self.assertIsNot(x,e)
    def test_explicit_owner_scope(self):
        with self.assertRaisesRegex(ValueError,"OWNER_PROFILE_ONLY"):p.prepare(ENV,p.RETAIN,"CLOUD_CI")
        with self.assertRaisesRegex(ValueError,"PROFILE_UNKNOWN"):p.prepare(ENV,"auto","OWNER_WSL2")
        with patch.object(p,"_run",side_effect=fake_run),patch.object(p,"_trusted_library",side_effect=fake_library):
            e,r=p.prepare(ENV,p.RETAIN,"OWNER_WSL2")
        self.assertEqual(e["LD_PRELOAD"],p.CORE);self.assertNotIn("LD_PRELOAD",ENV)
        self.assertEqual(r["owner_minimal_evidence_sha256"],p.OWNER_ACCEPTANCE_SHA)
        self.assertEqual(r["production_cleanup"],"NOT_RUN");self.assertFalse(r["vendor_fix_proven"])
    def test_reject_before_launch(self):
        for bad in (dict(LD_PRELOAD="x"),dict(LD_AUDIT="x"),dict(GALLIUM_DRIVER="llvmpipe"),dict(MESA_D3D12_DEFAULT_ADAPTER_NAME="Intel"),dict(LIBGL_ALWAYS_SOFTWARE="1"),dict(MESA_LOADER_DRIVER_OVERRIDE="other"),dict(ROS_DISTRO="humble"),dict(GZ_SIM_RENDER_ENGINE="ogre")):
            with patch.object(p,"_run") as cmd:
                with self.assertRaises(ValueError):p.prepare(dict(ENV,**bad),p.RETAIN,"OWNER_WSL2")
                cmd.assert_not_called()
    def test_version_and_renderer_drift(self):
        for executable,value in (("uname","generic"),("gz","8.16.0"),("dpkg-query","new"),("glxinfo","llvmpipe")):
            with patch.object(p,"_run",side_effect=lambda args,e: value if args[0]==executable else fake_run(args,e)),patch.object(p,"_trusted_library",side_effect=fake_library):
                with self.assertRaises(ValueError):p.prepare(ENV,p.RETAIN,"OWNER_WSL2")
        with patch.object(p,"_run",side_effect=fake_run),patch.object(p,"_trusted_library",side_effect=ValueError("A17_08_LIBRARY_SHA_DRIFT")):
            with self.assertRaisesRegex(ValueError,"SHA_DRIFT"):p.prepare(ENV,p.RETAIN,"OWNER_WSL2")
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"file.so";f.write_bytes(b"not ELF")
            with self.assertRaisesRegex(ValueError,"OUTSIDE_WSL"):p._trusted_library(str(f),"0"*64)
    def test_cleanup_independent(self):
        self.assertEqual(p.cleanup_result(good_record(),good_rows(),"PASS",True),"PASS")
        for rc in (-11,-9,143):
            rows=good_rows();rows[0]["returncode"]=rc
            self.assertEqual(p.cleanup_result(good_record(),rows,"PASS",True),"HOLD")
        rows=good_rows();rows[0]["signals"]=[2,15]
        self.assertEqual(p.cleanup_result(good_record(),rows,"PASS",True),"HOLD")
        for rec,rows,data,stopped in (({},good_rows(),"PASS",True),(dict(runtime_observation={}),good_rows(),"PASS",True),(good_record(),good_rows()[:-1],"PASS",True),(good_record(),good_rows(),"HOLD",True),(good_record(),good_rows(),"PASS",False)):
            self.assertEqual(p.cleanup_result(rec,rows,data,stopped),"HOLD")
        self.assertEqual(p.cleanup_result(None,[],"HOLD",False),"NOT_REQUESTED")
        # Visual GUI result is separate; residual groups still block.
        gui={"role":"gui","returncode":1,"stopped":True,"process_group_remaining":False}
        self.assertEqual(p.cleanup_result(good_record(),good_rows()+[gui],"PASS",True),"PASS")
    def test_real_production_callsite_contract(self):
        # Verify actual production collector, not a parallel sample launcher.
        tree=ast.parse((ROOT/"scripts/a16_pilot_collect.py").read_text())
        calls=[x for x in ast.walk(tree) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name)]
        launches=[x for x in calls if x.func.id=="launch"]
        server=[x for x in launches if isinstance(x.args[0],ast.Constant) and x.args[0].value=="server"]
        self.assertEqual(len(server),1);self.assertEqual(ast.unparse(server[0].args[2]),"server_env")
        for x in launches:
            if x is not server[0]:self.assertNotIn("server_env",ast.unparse(x))
        prep=[x for x in calls if x.func.id=="prepare_server_profile"];self.assertEqual(len(prep),1)
        self.assertLess(prep[0].lineno,min(x.lineno for x in launches))
        observations=[x for x in calls if x.func.id=="observe_server_profile"]
        self.assertEqual(len(observations),2)
        self.assertTrue(any(len(x.args)==3 and x.args[2].value=="runtime_observation_pre_shutdown" for x in observations))
        source=(ROOT/"scripts/a16_pilot_collect.py").read_text()
        self.assertIn('choices=PROFILES,default=INHERIT',source)
        self.assertIn('and profile_ok else 2',source)
    def test_failure_archive_keeps_distinct_verdict(self):
        import tarfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d);v={"data_verdict":"PASS","cleanup":"FAIL","ground_truth":"UNKNOWN_HOLD","training_eligible":False,"production_contact_health":"HOLD","server_runtime_profile":{"production_cleanup":"HOLD"}}
            (path/"verdict.json").write_text(json.dumps(v))
            scene_package(path)
            with tarfile.open(path/"a16_raw.tar.gz","r:gz") as t:
                self.assertEqual(json.load(t.extractfile("verdict.json")),v)
            self.assertTrue((path/"a16_raw.tar.gz.sha256").is_file())
if __name__=="__main__":unittest.main()
