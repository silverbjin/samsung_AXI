"""A adoption regression: the actual R03 adapter must use the shared profile."""
import os,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_platform.runtime import renderer_env
import a14_r03_dbg_collect as a
class Adoption(unittest.TestCase):
    def test_actual_import(self):
        self.assertIs(a.renderer_env,renderer_env)
        old=dict(DISPLAY=":0",GALLIUM_DRIVER="d3d12",MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA",WAYLAND_DISPLAY="wayland-0",QT_QPA_PLATFORM="wayland")
        expected=dict(DISPLAY=":0",GALLIUM_DRIVER="llvmpipe",LIBGL_ALWAYS_SOFTWARE="1",QT_QPA_PLATFORM="xcb")
        self.assertEqual(a.renderer_env(old,True),expected)
        self.assertEqual(a.renderer_env(old,False),old)
        self.assertEqual(old["GALLIUM_DRIVER"],"d3d12")
if __name__=="__main__":unittest.main()
