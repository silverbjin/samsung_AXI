"""No ROS, Windows or GPU required for this read-only diagnostic test."""
import json
import os
from pathlib import Path
import subprocess
import textwrap

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'samsungaxi_hw_probe.sh'


def test_syntax_and_no_side_effects():
    assert subprocess.run(['bash', '-n', str(SCRIPT)]).returncode == 0
    p = subprocess.run(['bash', str(SCRIPT), '--self-test'], text=True, capture_output=True)
    assert p.returncode == 0
    assert 'SELF_TEST_PASS_NO_HARDWARE' in p.stdout
    src = SCRIPT.read_text()
    assert 'wsl --shutdown' not in src and 'sudo ' not in src
    assert 'Get-CimInstance' in src and '/dev/dxg' in src


def test_non_windows_environment_graceful(tmp_path):
    p = subprocess.run(['bash', str(SCRIPT), '--output-dir', str(tmp_path)],
                       text=True, capture_output=True, timeout=30)
    assert p.returncode == 0, (p.stdout, p.stderr)
    data = json.loads((tmp_path / 'samsungaxi_hardware.json').read_text())
    assert data['project'] == 'SAMSUNGAXI'
    assert data['windows_host']['status'] in ('unavailable', 'ok', 'error', 'timeout')
    assert isinstance(data['wsl2']['cpu']['logical_processors_affinity_available'], int)
    assert 'SAMSUNGAXI_HARDWARE_DIAG_COMPLETE_NO_CHANGES' in p.stdout


def test_mocked_host_and_gpu_parsing(tmp_path):
    bindir = tmp_path / 'bin'; bindir.mkdir()
    ps = bindir / 'powershell.exe'
    ps.write_text('''#!/usr/bin/env bash\nprintf '%s\\n' '{"Status":"ok","CPU":[{"Name":"Test CPU","Cores":12,"LogicalProcessors":24}],"RAMBytes":34359738368,"GPU":[{"Name":"Test GPU","DriverVersion":"1"}],"WindowsVersion":"11","WSLConfig":{"memory":"12GB"}}'\n''')
    ps.chmod(0o755)
    gl = bindir / 'glxinfo'
    gl.write_text("#!/usr/bin/env bash\necho 'OpenGL vendor string: Microsoft Corporation'\necho 'OpenGL renderer string: D3D12 (Test GPU)'\n")
    gl.chmod(0o755)
    env=os.environ.copy(); env['PATH']=str(bindir)+os.pathsep+env['PATH']
    out=tmp_path/'output'
    p = subprocess.run(['bash', str(SCRIPT), '--output-dir', str(out)],
                       text=True, capture_output=True, env=env, timeout=30)
    assert p.returncode == 0, (p.stdout,p.stderr)
    d = json.loads((out/'samsungaxi_hardware.json').read_text())
    assert d['windows_host']['CPU'][0]['Name'] == 'Test CPU'
    assert d['windows_host']['RAMBytes'] == 34359738368
    assert d['wsl2']['gpu']['opengl_default_probe']['renderer']=='D3D12 (Test GPU)'
    assert 'WINDOWS_RAM=32.00 GiB' in (out/'samsungaxi_hardware.txt').read_text()
def test_downloaded_to_tmp_defaults_to_samsungaxi_workspace(tmp_path):
    """Curl to /tmp should never try writing /logs or another project tree."""
    import shutil
    download = tmp_path / 'temporary_download.sh'
    shutil.copy2(SCRIPT, download)
    env=os.environ.copy(); env['HOME']=str(tmp_path)
    p=subprocess.run(['bash',str(download)],env=env,text=True,capture_output=True,timeout=30)
    assert p.returncode==0,(p.stdout,p.stderr)
    report_dir=tmp_path/'samsung_AXI'/'logs'/'hardware'
    assert list(report_dir.glob('*/samsungaxi_hardware.json'))
