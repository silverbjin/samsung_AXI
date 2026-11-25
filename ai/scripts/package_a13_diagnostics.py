#!/usr/bin/env python3
"""Package one B A-13 review attempt (PASS or FAIL) as a private SHA-sealed TAR.

Only a bounded set of review/evidence/diagnostic files is included. The
original A-13 source archive, renderer dumps, and any approval ledger are
intentionally excluded. This is NOT an approval or public release bundle.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import tarfile
import tempfile
from pathlib import Path

MAX_FILES = 180
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 95 * 1024 * 1024
SOURCE_SHA = '6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df'
SCENES = tuple(f'trial_{x:04d}' for x in range(1, 5))
ROOT_NAMES = ('summary.json', 'source_manifest.json', 'deployment_gate_manifest.json', 'SHA256SUMS')
TRIAL_NAMES = ('tray_rgb.png', 'capture_metadata.json', 'initial_state.json',
               'final_state.json', 'trial_summary.json', 'physics_observations.jsonl',
               'scenario.scenario.json', 'process_cleanup.json')
REVIEW_NAMES = ('review.html', 'candidate_manifest.csv', 'evidence_audit.json')
SVG_NAME = re.compile(r'^B13-[a-f0-9]{20}_(?:z|tilt_deg|xy)\.svg$')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def allowed_paths(workdir: Path):
    """Explicit allowlist prevents accidentally packaging full A original TAR/private state."""
    if not workdir.is_dir() or workdir.is_symlink():
        return
    for name in ROOT_NAMES:
        yield workdir / 'raw' / name, 'raw/' + name
    for scene in SCENES:
        for name in TRIAL_NAMES:
            yield workdir / 'raw' / scene / name, 'raw/' + scene + '/' + name
    for name in REVIEW_NAMES:
        yield workdir / 'review' / name, 'review/' + name
    folder = workdir / 'review' / 'plots'
    if folder.is_dir() and not folder.is_symlink():
        for path in sorted(folder.iterdir()):
            if SVG_NAME.fullmatch(path.name):
                yield path, 'review/plots/' + path.name


def tar_add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o600
    info.uid = info.gid = 0
    info.uname = info.gname = ''
    info.mtime = 0  # deterministic member metadata, not a simulated evidence timestamp
    tar.addfile(info, io.BytesIO(data))


def package(log: Path, workdir: Path | None, output: Path, exit_code: int,
            git_sha: str, source_archive: Path | None = None) -> dict:
    if not log.is_file() or log.is_symlink():
        raise ValueError('B_DIAGNOSTICS_LOG_NOT_READY')
    if output.exists() or output.is_symlink():
        raise ValueError('B_DIAGNOSTIC_ARCHIVE_NO_OVERWRITE')
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    entries = [('execution.log', log.read_bytes())]
    if len(entries[0][1]) > MAX_FILE_BYTES:
        raise ValueError('B_DIAGNOSTIC_LOG_TOO_LARGE')
    contains = []
    root = workdir.resolve(strict=True) if workdir is not None and workdir.is_dir() else None
    if root is not None:
        for src, name in allowed_paths(workdir):
            # Never dereference symlinks, including intermediate path components.
            if not src.is_file() or src.is_symlink() or not src.resolve().is_relative_to(root):
                continue
            data = src.read_bytes()
            if len(data) > MAX_FILE_BYTES:
                raise ValueError('B_DIAGNOSTIC_MEMBER_SIZE_LIMIT ' + name)
            entries.append((name, data))
            contains.append(name)
    if len(entries) + 2 > MAX_FILES or sum(len(d) for _, d in entries) > MAX_TOTAL_BYTES:
        raise ValueError('B_DIAGNOSTIC_ARCHIVE_SIZE_LIMIT')
    # Only the *input archive's SHA*, never its large raw bytes, is recorded.
    archive_sha = None
    for line in entries[0][1].decode('utf-8', errors='replace').splitlines():
        if 'SMARTDISH_B_A13_ARCHIVE_SHA_PASS sha256=' in line:
            value = line.split('sha256=', 1)[1].split()[0]
            if re.fullmatch(r'[0-9a-f]{64}', value):
                archive_sha = value
                break
    record = {
        'schema': 1, 'purpose': 'B_A13_PRIVATE_REVIEW_DIAGNOSTIC_NOT_APPROVED_DATASET',
        'exit_code': exit_code,
        'status': 'RUN_SUCCESS' if exit_code == 0 else 'RUN_FAILED',
        'git_sha': git_sha,
        'a13_source_git_sha': SOURCE_SHA,
        'source_archive_sha256': archive_sha,
        'source_archive_path': str(source_archive) if source_archive is not None else None,
        'workdir': str(workdir) if workdir is not None else None,
        'included_paths': contains,
        'candidate_review_only': True,
        'human_approved_labels': None,
        'created_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    entries.append(('diagnostic_status.json', (json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()))
    checksums = ''.join(f'{digest(data)}  {name}\n' for name, data in entries).encode()
    entries.append(('SHA256SUMS', checksums))
    fd, tmp = tempfile.mkstemp(prefix='.b-a13-diag-', suffix='.tar.gz.tmp', dir=output.parent)
    try:
        os.close(fd)
        with tarfile.open(tmp, mode='w:gz', format=tarfile.PAX_FORMAT) as tar:
            for name, data in entries:
                tar_add_bytes(tar, name, data)
        # Same filesystem atomic publication, never overwrite an existing archive.
        if output.exists():
            raise ValueError('B_DIAGNOSTIC_ARCHIVE_NO_OVERWRITE')
        os.replace(tmp, output)
        sha = hashlib.sha256(output.read_bytes()).hexdigest()
        sidecar = Path(str(output) + '.sha256')
        sidecar.write_text(sha + '  ' + output.name + '\n', encoding='utf-8')
        return {'archive_path': str(output), 'sha256': sha, 'members': len(entries), **record}
    finally:
        Path(tmp).unlink(missing_ok=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--workdir-file', type=Path, required=True)
    p.add_argument('--archive-file', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--exit-code', type=int, required=True)
    p.add_argument('--git-sha', required=True)
    args = p.parse_args()
    try:
        workdir = Path(args.workdir_file.read_text().strip()) if args.workdir_file.is_file() else None
        archive = Path(args.archive_file.read_text().strip()) if args.archive_file.is_file() else None
        result = package(args.log, workdir, args.output, args.exit_code, args.git_sha, archive)
    except (ValueError, OSError, tarfile.TarError) as exc:
        print('B_DIAGNOSTIC_ARCHIVE_FAILED ' + str(exc), flush=True)
        return 4
    print('SMARTDISH_B_DIAGNOSTIC_ARCHIVE_CREATED path=' + result['archive_path'] +
          ' sha256=' + result['sha256'] + ' status=' + result['status'] +
          ' members=' + str(result['members']), flush=True)
    print('SMARTDISH_B_DIAGNOSTIC_ARCHIVE_SHA256_FILE ' + result['archive_path'] + '.sha256', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
