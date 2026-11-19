"""Small release-focused tests; no ROS/Gazebo installed or mocked PASS markers."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from zipfile import ZipFile

HERE = Path(__file__).resolve().parents[1]
BUNDLER = HERE / 'scripts/samsungaxi_evidence_bundle.py'
WRAPPER = HERE / 'scripts/samsungaxi_d3d12_evidence_once.sh'
spec = importlib.util.spec_from_file_location('evidence', BUNDLER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_zip_includes_scoped_world_and_ros_logs(tmp_path):
    root = tmp_path / 'repo'
    logs = root / 'logs'
    logs.mkdir(parents=True)
    world = logs / 'world_20261119_160000.log'
    world.write_text('START\n' + ('noise\n' * 70000) + 'ERROR: timeout\n' + 'TOKEN=badsecret\n' + 'FINISH\n')
    home = tmp_path / 'home'
    ros_dir = home / '.ros' / 'log' / '2026-11-19-samsungaxi'
    ros_dir.mkdir(parents=True)
    (ros_dir / 'gz-123.log').write_text('Gazebo log\nFATAL bridge missing\n')
    session = logs / 'evidence' / 'session.log'
    session.parent.mkdir()
    session.write_text(f'All log files can be found below {ros_dir}\nRESTAURANT_OWNER_LOG={world}\n')
    stats_dir = root/'logs'/'evidence'
    (stats_dir/'gazebo_stats_20261119T160000Z.txt').write_text('real_time_factor: 0.9989\n')
    output = tmp_path / 'evidence.zip'
    result = module.gather(root, session, 0, output, home)
    assert output.stat().st_size < 100_000
    assert result['ros_log_dir_found'] and result['selected_world_log']
    with ZipFile(output) as bundle:
        names = set(bundle.namelist())
        assert {'manifest.json', 'logs/session.log', 'logs/world.log', 'ros/00_gz-123.log', 'metrics/gazebo_rtf_observation.txt'}.issubset(names)
        content = bundle.read('logs/world.log').decode()
        assert 'ERROR: timeout' in content
        assert 'badsecret' not in content
        assert '[REDACTED: credential-bearing line]' in content
        assert json.loads(bundle.read('manifest.json'))['scope'].endswith('not_nav2_acceptance')
    assert world.exists(), 'source evidence may not be modified'


def test_rejects_outside_ros_path_and_output_overwrite(tmp_path):
    root = tmp_path / 'repo'
    (root/'logs').mkdir(parents=True)
    session = root/'logs'/'session.log'
    session.write_text(f'All log files can be found below {tmp_path}/other-project\n')
    (tmp_path/'other-project').mkdir()
    out = tmp_path/'out.zip'
    result = module.gather(root, session, 0, out, tmp_path/'home')
    assert not result['ros_log_dir_found']
    try:
        module.gather(root, session, 0, out, tmp_path/'home')
    except FileExistsError:
        pass
    else:
        raise AssertionError('must not overwrite existing evidence')


def test_wrapper_collects_bundle_without_touching_original_runner(tmp_path):
    root = tmp_path/'repo'
    scripts = root/'scripts'
    scripts.mkdir(parents=True)
    logs = root/'logs'
    logs.mkdir()
    core = scripts/'core.sh'
    core.write_text('#!/bin/bash\n'
                    'echo "SAMSUNGAXI_GL_RENDERER=D3D12 (NVIDIA RTX 3060)"\n'
                    'echo "RESTAURANT_OWNER_LOG=$HOME/nonexisting"\n'
                    'echo "simulation stopped by operator"\n')
    dest = scripts/'samsungaxi_evidence_bundle.py'
    dest.write_bytes(BUNDLER.read_bytes())
    env = {**os.environ, 'SAMSUNG_AXI_ROOT': str(root), 'SAMSUNG_AXI_CORE_SCRIPT': str(core),
           'SAMSUNG_AXI_BUNDLER_SCRIPT': str(dest)}
    r = subprocess.run(['bash',str(WRAPPER),'world'], env=env, capture_output=True, text=True, timeout=15)
    assert r.returncode == 0, r.stdout+r.stderr
    assert 'SAMSUNGAXI_EVIDENCE_ZIP=' in r.stdout
    zips=list((logs/'evidence').glob('*.zip'))
    assert len(zips)==1
    with ZipFile(zips[0]) as bundle:
        assert 'SAMSUNGAXI_GL_RENDERER=' in bundle.read('logs/session.log').decode()
    assert core.read_text().startswith('#!/bin/bash')


def test_wrapper_preserves_failed_exit_and_bundles_it(tmp_path):
    root=tmp_path/'repo'
    (root/'scripts').mkdir(parents=True)
    core=root/'scripts'/'core.sh'
    core.write_text('#!/bin/bash\necho "ERROR: failed to start"\nexit 13\n')
    bundler=root/'scripts'/'samsungaxi_evidence_bundle.py'
    bundler.write_bytes(BUNDLER.read_bytes())
    env={**os.environ, 'SAMSUNG_AXI_ROOT':str(root),
         'SAMSUNG_AXI_CORE_SCRIPT':str(core), 'SAMSUNG_AXI_BUNDLER_SCRIPT':str(bundler)}
    r=subprocess.run(['bash',str(WRAPPER),'world'],env=env,capture_output=True,text=True,timeout=15)
    assert r.returncode == 13, r.stdout+r.stderr
    assert list((root/'logs'/'evidence').glob('*.zip'))
    with ZipFile(next((root/'logs'/'evidence').glob('*.zip'))) as z:
        assert 'ERROR: failed to start' in z.read('logs/session.log').decode()


def test_syntax_and_no_host_modification():
    for script in (WRAPPER, HERE/'scripts'/'samsungaxi_snapshot_rtf.sh'):
        subprocess.run(['bash','-n',str(script)],check=True)
    text=WRAPPER.read_text()
    assert 'pkill' not in text and 'killall' not in text
    assert 'wsl --shutdown' not in text and 'sudo' not in text
    assert 'GALLIUM_DRIVER=' not in text  # wrapper must not alter successful GPU runner
