#!/usr/bin/env python3
"""Compact, local-only SAMSUNGAXI diagnostic ZIP, no ROS dependency.

Only the current session log, a same-session world log, and the ROS launch
log directory explicitly named by that session are eligible. Large files are
excerpted; no raw rosbag, sensor frames, unrelated logs, or credentials.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZIP_DEFLATED

MAX_FILE_OUTPUT = 300_000
MAX_ROS_FILES = 8
MAX_ROS_LOG_DIR_FILES = 40
MATCH_TERMS = re.compile(r"\b(error|fatal|exception|traceback|segfault|abort|failed|warn|killed|out.of.memory)\b", re.I)
# Avoid leaking account identifiers or incidental credentials in shared bundles.
SECRET_LINE = re.compile(r"(password|api[_-]?key|authorization\s*:|bearer\s+|gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|secret=|token=)", re.I)
ROS_PATH = re.compile(r"All log files can be found below\s+(\/[^\s]+)")
RUN_LOG = re.compile(r"RESTAURANT_OWNER_LOG=([^\s]+)")


def redact(line: str) -> str:
    if SECRET_LINE.search(line):
        return "[REDACTED: credential-bearing line]\n"
    return line


def compact_file(path: Path, size_limit: int = MAX_FILE_OUTPUT) -> tuple[str, dict]:
    """Capture first/last evidence plus first error candidates without huge ZIPs."""
    stat = path.stat()
    max_line = 4096
    head: list[str] = []
    errors: list[str] = []
    tail: list[str] = []
    head_budget, tail_budget, error_budget = 45_000, 145_000, 70_000
    head_bytes = tail_bytes = error_bytes = 0
    lines_total = 0
    # Entire source scanned by streaming; no raw file copied wholesale.
    with path.open('r', encoding='utf-8', errors='replace') as f:
        for line in f:
            lines_total += 1
            line = redact(line[:max_line] + ('\n[LINE TRUNCATED]\n' if len(line) > max_line else ''))
            byte_size = len(line.encode('utf-8', errors='replace'))
            if head_bytes + byte_size <= head_budget:
                head.append(line)
                head_bytes += byte_size
            if MATCH_TERMS.search(line) and error_bytes + byte_size <= error_budget:
                errors.append(f'L{lines_total}: {line}')
                error_bytes += byte_size
            tail.append(line)
            tail_bytes += byte_size
            while tail_bytes > tail_budget and tail:
                tail_bytes -= len(tail.pop(0).encode('utf-8', errors='replace'))
    body = (
        '== HEAD (bounded) ==\n' + ''.join(head) +
        '\n== FIRST ERROR/WARNING CANDIDATES (bounded) ==\n' + ''.join(errors) +
        '\n== TAIL (bounded) ==\n' + ''.join(tail)
    )
    raw = body.encode('utf-8', errors='replace')
    if len(raw) > size_limit:
        body = raw[:size_limit].decode('utf-8', errors='ignore') + '\n[BUNDLE EXCERPT TRUNCATED]\n'
    return body, dict(size_bytes=stat.st_size, captured_bytes=len(body.encode()), total_lines=lines_total,
                      excerpted=stat.st_size > len(body.encode()), sha256_excerpt=hashlib.sha256(body.encode()).hexdigest())


def last_marker(source: str, regex: re.Pattern[str]) -> str | None:
    matches = regex.findall(source)
    return matches[-1] if matches else None


def validate_ros_dir(path_value: str | None, home: Path) -> Path | None:
    if not path_value:
        return None
    allowed = (home / '.ros/log').resolve()
    p = Path(path_value).resolve()
    try:
        p.relative_to(allowed)
    except ValueError:
        return None
    return p if p.is_dir() else None


def same_session_world_log(root: Path, since: float, session: str) -> Path | None:
    marker = last_marker(session, RUN_LOG)
    if marker:
        target = Path(marker).resolve()
        allowed = (root / 'logs').resolve()
        try:
            target.relative_to(allowed)
        except ValueError:
            return None
        if target.is_file() and target.name.startswith('world_'):
            return target
    candidates = [p for p in (root / 'logs').glob('world_*.log') if p.is_file() and p.stat().st_mtime >= since - 5]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def gather(root: Path, session_path: Path, since: float, output: Path, home: Path | None = None,
           include_ros: bool = True) -> dict:
    root = root.resolve()
    home = (home or Path.home()).resolve()
    session_path = session_path.resolve()
    if not session_path.is_file():
        raise ValueError('SESSION_LOG_MISSING')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f'OUTPUT_EXISTS: {output}')
    with session_path.open('rb') as stream:
        stream.seek(max(0, session_path.stat().st_size - 2_000_000))
        session_text = stream.read().decode('utf-8', errors='replace')
    candidates: list[tuple[str, Path]] = [('logs/session.log', session_path)]
    world = same_session_world_log(root, since, session_text)
    if world and world != session_path:
        candidates.append(('logs/world.log', world))
    ros = validate_ros_dir(last_marker(session_text, ROS_PATH), home) if include_ros else None
    # Optional live RTF stats captured separately during the same world session.
    stats_dir = root / 'logs' / 'evidence'
    stats_files = [p for p in stats_dir.glob('gazebo_stats_*.txt')
                   if p.is_file() and p.stat().st_mtime >= since - 5]
    stats = max(stats_files, key=lambda p: p.stat().st_mtime) if stats_files else None
    if stats:
        candidates.append(('metrics/gazebo_rtf_observation.txt', stats))
    if ros:
        # Small bounded set, prioritize log files that have a failure signal or are fresh.
        log_files = []
        for p in list(ros.rglob('*.log'))[:MAX_ROS_LOG_DIR_FILES]:
            if p.is_file():
                log_files.append(p)
        log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for i, p in enumerate(log_files[:MAX_ROS_FILES]):
            candidates.append((f'ros/{i:02d}_{p.name}', p))
    manifest = {
        'project': 'SAMSUNGAXI',
        'bundle_schema': 1,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'owner_rtf_from_screenshot': 'not_measured_by_script',
        'scope': 'read_only_compact_current_session; not_nav2_acceptance',
        'ros_log_dir_found': bool(ros),
        'selected_world_log': bool(world),
        'rtf_stats_file_found': bool(stats),
        'files': {},
        'missing': [],
    }
    with ZipFile(output, 'x', compression=ZIP_DEFLATED, compresslevel=7) as archive:
        for arcname, src in candidates:
            if not src.is_file():
                manifest['missing'].append(arcname)
                continue
            content, meta = compact_file(src)
            archive.writestr(arcname, content)
            manifest['files'][arcname] = meta
        if world is None:
            manifest['missing'].append('logs/world.log')
        if stats is None:
            manifest['missing'].append('metrics/gazebo_rtf_observation.txt (optional)')
        if ros is None:
            manifest['missing'].append('ros/*.log (session path not found or outside ~/.ros/log)')
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        archive.writestr('README.txt',
                         'SAMSUNGAXI compact diagnostic evidence, local-only.\n'
                         'Excerpts are NOT the entire raw log.\n'
                         'Original logs remain unchanged on disk.\n'
                         'No ROS/Gazebo/WSL success is asserted by bundle creation.\n')
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.home() / 'samsung_AXI')
    p.add_argument('--session-log', type=Path, required=True)
    p.add_argument('--since-unix', type=float, default=0)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--no-ros', action='store_true')
    args = p.parse_args()
    try:
        manifest = gather(args.root, args.session_log, args.since_unix, args.output,
                          include_ros=not args.no_ros)
    except (OSError, ValueError) as exc:
        print(f'SAMSUNGAXI_EVIDENCE_BLOCKED={exc}', file=sys.stderr)
        return 2
    print(f'SAMSUNGAXI_EVIDENCE_ZIP={args.output.resolve()}')
    print('SAMSUNGAXI_EVIDENCE_CONTENTS=' + ','.join(manifest['files']))
    print('SAMSUNGAXI_EVIDENCE_ZIP_COMPLETE_NO_ACCEPTANCE_CLAIM')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
