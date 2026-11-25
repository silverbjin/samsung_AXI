"""B-10 CLI preflight tests. All archives here are synthetic/missing, never real A-13."""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

import pytest


SHELL = Path(__file__).resolve().parents[1] / 'scripts' / 'smartdish_b_real_data_one_shot.sh'


def prepare_git_repo(tmp_path):
    root = tmp_path / 'checkout'
    (root / 'scripts').mkdir(parents=True)
    dst = root / 'scripts' / SHELL.name
    shutil.copyfile(SHELL, dst)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 'qa@example.invalid'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'Test Only'], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), 'commit', '-qm', 'fixture checkout'], check=True)
    sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    return root, sha


def run_shell(root, sha, args, home):
    env = dict(os.environ, HOME=str(home))
    return subprocess.run(['bash', str(root / 'scripts' / SHELL.name), '--sha', sha, *args],
                          env=env, cwd=root, text=True, capture_output=True)


def test_b10_runner_shell_syntax():
    subprocess.run(['bash', '-n', str(SHELL)], check=True)


@pytest.mark.parametrize('path,marker', [
    ('/path/to/smartdish_a_tray_evidence.tar(5).gz', 'B_A13_ARCHIVE_PLACEHOLDER_PATH'),
    ('/tmp/this-a13-file-does-not-exist-ever.tar.gz', 'B_A13_ARCHIVE_FILE_MISSING'),
])
def test_b10_runner_fail_fast_explicit_missing(tmp_path, path, marker):
    root, sha = prepare_git_repo(tmp_path)
    res = run_shell(root, sha, ['--archive', path, '--mode', 'review'], tmp_path / 'home')
    assert res.returncode == 3
    assert marker in res.stderr
    assert 'SMARTDISH_B_A13_ARCHIVE_SHA_PASS' not in res.stdout
    assert not list((root / 'ai/data/private').glob('b_a13_review_*'))  # diagnostics-only permitted


def test_b10_runner_wrong_archive_hash_rejected_before_workspace(tmp_path):
    root, sha = prepare_git_repo(tmp_path)
    archive = tmp_path / 'fake-a13.tar.gz'
    archive.write_bytes(b'not the genuine accepted A13 archive')
    res = run_shell(root, sha, ['--archive', str(archive)], tmp_path / 'home')
    assert res.returncode == 2
    assert 'B10_ARCHIVE_SHA_MISMATCH' in res.stderr
    assert 'B_EVIDENCE_IMPORT_BLOCKED' in res.stderr
    assert not list((root / 'ai/data/private').glob('b_a13_review_*'))  # diagnostics-only permitted


def test_b10_runner_auto_discovery_missing_is_not_import_pass(tmp_path):
    root, sha = prepare_git_repo(tmp_path)
    home = tmp_path / 'home'
    home.mkdir()
    res = run_shell(root, sha, ['--mode', 'review'], home)
    assert res.returncode == 3
    assert 'B_A13_ORIGINAL_ARCHIVE_NOT_FOUND' in res.stderr
    assert 'B_EVIDENCE_IMPORT_BLOCKED' in res.stderr
    assert 'SMARTDISH_B_A13_INTERNAL_HASH_PASS' not in res.stdout


def test_b10_runner_auto_discovery_wrong_sha_distinct_from_missing(tmp_path):
    root, sha = prepare_git_repo(tmp_path)
    home = tmp_path / 'home'
    folder = home / 'samsung_AXI_A_TRAY/generated/smartdish_tray/run_mock'
    folder.mkdir(parents=True)
    (folder / 'smartdish_a_tray_evidence.tar.gz').write_bytes(b'not genuine data')
    res = run_shell(root, sha, ['--mode', 'review'], home)
    assert res.returncode == 2
    assert 'B10_ARCHIVE_SHA_MISMATCH' in res.stderr
    assert 'B_A13_ORIGINAL_ARCHIVE_NOT_FOUND' not in res.stderr
    assert not list((root / 'ai/data/private').glob('b_a13_review_*'))  # diagnostics-only permitted
