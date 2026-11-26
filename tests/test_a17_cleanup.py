import json,os,sys,tempfile,unittest,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from a17_cleanup_contract import renderer,compare,gdb_exit,archive,proc_identity,owned_inferior
class A17(unittest.TestCase):
    def test_renderer_isolation(self):
        a={"GALLIUM_DRIVER":"d3d12","MESA_D3D12_DEFAULT_ADAPTER_NAME":"NVIDIA","DISPLAY":":0","QT_QPA_PLATFORM":"xcb","MESA_LOADER_DRIVER_OVERRIDE":"d3d12"}
        b=renderer(a,"software");self.assertEqual(b["GALLIUM_DRIVER"],"llvmpipe");self.assertEqual(b["LIBGL_ALWAYS_SOFTWARE"],"1")
        self.assertNotIn("MESA_D3D12_DEFAULT_ADAPTER_NAME",b);self.assertNotIn("MESA_LOADER_DRIVER_OVERRIDE",b)
        self.assertEqual(a["GALLIUM_DRIVER"],"d3d12");self.assertEqual(b["DISPLAY"],a["DISPLAY"]);self.assertEqual(b["QT_QPA_PLATFORM"],a["QT_QPA_PLATFORM"])
        self.assertEqual(renderer(a,"native"),a)
    def test_no_false_root(self):
        a={"profile":"native","instrumentation":"DIRECT","data":"PASS","all_owned_stopped":True,"server_rc":-11,"bridge_rc":0}
        b=dict(a,profile="software",server_rc=0)
        self.assertEqual(compare([a,b]),"SOFTWARE_MITIGATION_CANDIDATE_ROOT_UNPROVEN")
        self.assertEqual(compare([a,dict(b,server_rc=-11)]),"BOTH_PROFILES_CRASH_ROOT_UNPROVEN")
        self.assertEqual(compare([dict(a,server_rc=0),b]),"NOT_REPRODUCED_ROOT_UNPROVEN")
        self.assertEqual(compare([a,dict(b,data="HOLD")]),"CONTRAST_INCONCLUSIVE")
        self.assertEqual(compare([b]),"NATIVE_CONTRAST_NOT_RUN")
    def test_gdb_exit_signal_not_debugger_rc(self):
        self.assertEqual(gdb_exit({"inferior_exit_signal":11,"inferior_exit_code":0}),-11)
        self.assertEqual(gdb_exit({"inferior_exit_code":0}),0)
        self.assertIsNone(gdb_exit({"debugger_error":"missing"}))
        self.assertIsNone(gdb_exit({}))
    def test_owned_identity(self):
        import subprocess
        p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(10)"],start_new_session=True)
        try:
            s=proc_identity(p.pid);self.assertTrue(owned_inferior(p.pid,s["start_ticks"],os.getpid()))
            self.assertFalse(owned_inferior(p.pid,"0",os.getpid()))
            self.assertFalse(owned_inferior(p.pid,s["start_ticks"],os.getpid()+1))
        finally:p.terminate();p.wait(timeout=3)
    def test_archive_success_failure(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/"a17_report.json").write_text('{"exit_code":2,"root_cause":"UNPROVEN"}')
            h=archive(p);self.assertEqual(hashlib.sha256((p/"a17_cleanup_evidence.tar.gz").read_bytes()).hexdigest(),h)
            self.assertTrue((p/"a17_cleanup_evidence.tar.gz.sha256").is_file())
            with self.assertRaises(FileExistsError):archive(p)
    def test_archive_link_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/"a.log").write_text("x");(p/"b.log").symlink_to(p/"a.log")
            with self.assertRaisesRegex(ValueError,"UNSAFE_LINK"):archive(p)
if __name__=="__main__":unittest.main()
