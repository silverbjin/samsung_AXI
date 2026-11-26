import os,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from a17_gpu_retention_contract import *
class Retention(unittest.TestCase):
    def test_scope(self):
        env={"GALLIUM_DRIVER":"d3d12","MESA_D3D12_DEFAULT_ADAPTER_NAME":"NVIDIA"}
        self.assertEqual(server_override(env),{"LD_PRELOAD":CORE});self.assertNotIn("LD_PRELOAD",env)
        for x in ({"LD_PRELOAD":"old.so"},{"LD_AUDIT":"old.so"},{"LIBGL_ALWAYS_SOFTWARE":"1"},{"GALLIUM_DRIVER":"llvmpipe"},{"MESA_D3D12_DEFAULT_ADAPTER_NAME":"Intel"},{"MESA_LOADER_DRIVER_OVERRIDE":"other"}):
            with self.assertRaises(ValueError):server_override(dict(env,**x))
    def test_gate(self):
        row={"data":"PASS","cleanup":"PASS","server_rc":0,"bridge_rc":0,"shutdown_signal_sent":True,"all_owned_stopped":True,"frames":[{"stamp_ns":1000000000,"sha256":BASELINE_PIXEL}]}
        maps="0000 /usr/lib/wsl/lib/libd3d12core.so\n0000 /usr/lib/wsl/lib/libd3d12.so\n"
        glx="Accelerated: yes\nOpenGL renderer string: D3D12 (NVIDIA GeForce RTX 3060)\n"
        self.assertEqual(evaluate(row,maps,glx)["verdict"],"GPU_RETENTION_MINIMAL_MITIGATION_PASS")
        for bad in (dict(row,server_rc=-11),dict(row,frames=[]),dict(row,all_owned_stopped=False),dict(row,frames=[{"stamp_ns":1000000000,"sha256":"bad"}])):
            self.assertEqual(evaluate(bad,maps,glx)["verdict"],"GPU_RETENTION_MINIMAL_MITIGATION_HOLD")
        self.assertEqual(evaluate(row,"",glx)["verdict"],"GPU_RETENTION_MINIMAL_MITIGATION_HOLD")
        self.assertEqual(evaluate(row,maps,"llvmpipe")["verdict"],"GPU_RETENTION_MINIMAL_MITIGATION_HOLD")
        self.assertEqual(evaluate(row,maps,glx)["production_cleanup"],"NOT_RUN")
if __name__=="__main__":unittest.main()
