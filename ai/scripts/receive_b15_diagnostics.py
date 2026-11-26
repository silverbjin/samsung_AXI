#!/usr/bin/env python3
"""B-12R: safely verify a B-15 diagnostic TAR and stage an UNAPPROVED review workspace.

Never treats the diagnostic subset as the full A-13 archive. No label approval.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import posixpath
from html.parser import HTMLParser
import os
import re
import tarfile
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from PIL import Image, UnidentifiedImageError

EXPECTED_A13_SHA = 'bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e'
EXPECTED_A13_GIT_SHA = '6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df'
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_MEMBERS = 256
REQUIRED = {'SHA256SUMS', 'execution.log', 'diagnostic_status.json',
            'review/review.html', 'review/candidate_manifest.csv',
            'review/evidence_audit.json'}
REQUIRED_COLUMNS = {'candidate_id','source_image_path','source_image_sha256',
                    'physics_path','physics_sha256','physics_size_bytes',
                    'source_archive_sha256','source_git_sha','source_scene_id',
                    'suggested_label','label_status','temporal_review',
                    'capture_stamp_ns','pose_at_capture_ns','stack_id'}


class ReceiptError(ValueError):
    pass


def error(code: str):
    raise ReceiptError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_rel(path: str) -> str:
    p = PurePosixPath(path)
    if (not path or p.is_absolute() or '\\' in path or '\x00' in path
            or any(segment in ('', '.', '..') for segment in path.split('/'))
            or ':' in path.split('/')[0]):
        error('B12R_UNSAFE_ARCHIVE_PATH ' + repr(path))
    return str(p)


def read_sidecar(archive: Path, sidecar: Path):
    if not archive.is_file():
        error('B12R_ARCHIVE_NOT_FOUND')
    if not sidecar.is_file():
        error('B12R_SIDECAR_MISSING')
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        error('B12R_COMPRESSED_SIZE_LIMIT')
    try:
        body = sidecar.read_text(encoding='utf-8').strip().splitlines()
    except OSError as exc:
        raise ReceiptError('B12R_SIDECAR_MISSING') from exc
    if len(body) != 1:
        error('B12R_SIDECAR_INVALID')
    match = re.fullmatch(r'([0-9a-f]{64})  ([^\n]+)', body[0])
    if not match or match.group(2) != archive.name:
        error('B12R_SIDECAR_INVALID')
    h = hashlib.sha256()
    with archive.open('rb') as inp:
        for part in iter(lambda: inp.read(1024 * 1024), b''):
            h.update(part)
    if h.hexdigest() != match.group(1):
        error('B12R_ARCHIVE_SHA_MISMATCH')
    return h.hexdigest()


def read_archive(archive: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    total = 0
    try:
        with tarfile.open(archive, 'r:gz') as stream:
            for index, member in enumerate(stream):
                if index >= MAX_MEMBERS:
                    error('B12R_MEMBER_COUNT_LIMIT')
                path = safe_rel(member.name)
                if path in files:
                    error('B12R_MEMBER_DUPLICATE')
                if not member.isfile():
                    error('B12R_LINK_OR_SPECIAL_FORBIDDEN')
                if member.size < 0 or member.size > MAX_FILE_BYTES:
                    error('B12R_MEMBER_SIZE_LIMIT')
                total += member.size
                if total > MAX_TOTAL_BYTES:
                    error('B12R_TOTAL_SIZE_LIMIT')
                fp = stream.extractfile(member)
                if fp is None:
                    error('B12R_MISSING_MEMBER_BYTES')
                contents = fp.read(member.size + 1)
                if len(contents) != member.size:
                    error('B12R_MEMBER_LENGTH_MISMATCH')
                files[path] = contents
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise ReceiptError('B12R_TAR_CORRUPT') from exc
    if not REQUIRED <= set(files):
        error('B12R_REQUIRED_FILE_MISSING')
    if any('approval' in p.lower() for p in files):
        error('B12R_APPROVAL_IN_DIAGNOSTIC_FORBIDDEN')
    return files


def check_sums(files: dict[str, bytes]):
    try:
        lines = files['SHA256SUMS'].decode('utf-8').splitlines()
    except UnicodeError as exc:
        raise ReceiptError('B12R_HASH_LIST_ENCODING') from exc
    indexes = {}
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            error('B12R_HASH_LIST_INVALID')
        rel = safe_rel(match.group(2))
        if rel in indexes:
            error('B12R_HASH_LIST_DUPLICATE')
        indexes[rel] = match.group(1)
    if set(indexes) != set(files) - {'SHA256SUMS'}:
        error('B12R_HASH_SET_MISMATCH')
    for rel, sha in indexes.items():
        if digest(files[rel]) != sha:
            error('B12R_INTERNAL_SHA_MISMATCH ' + rel)
    return len(indexes)


class ReviewImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'iframe', 'object', 'embed') or any(k.lower().startswith('on') for k, _ in attrs):
            error('B12R_UNSAFE_HTML_CONTENT')
        if tag == 'img':
            values = [value for key,value in attrs if key == 'src']
            if len(values) != 1 or not values[0]:
                error('B12R_REVIEW_IMAGE_SRC_INVALID')
            self.sources.append(values[0])


def validate_review_assets(files: dict[str, bytes], rows: list[dict]):
    parser = ReviewImageParser()
    try:
        parser.feed(files['review/review.html'].decode('utf-8'))
    except UnicodeError as exc:
        raise ReceiptError('B12R_REVIEW_HTML_ENCODING') from exc
    expected = set()
    for row in rows:
        expected.add('raw/' + safe_rel(row['source_image_path']))
        for feature in ('z', 'tilt_deg', 'xy'):
            expected.add('review/plots/' + row['candidate_id'] + '_' + feature + '.svg')
    found = set()
    for source in parser.sources:
        if source.startswith('/') or ':' in source or '\\' in source or source.startswith('//'):
            error('B12R_REVIEW_IMAGE_SRC_INVALID')
        path = posixpath.normpath(posixpath.join('review', source))
        if path not in files or path not in expected:
            error('B12R_REVIEW_ASSET_MISSING_OR_UNEXPECTED')
        if path in found:
            error('B12R_REVIEW_ASSET_DUPLICATE')
        found.add(path)
    if found != expected:
        error('B12R_REVIEW_ASSET_INCOMPLETE')


def validate_candidates(files: dict[str, bytes], status: dict):
    try:
        rows = list(csv.DictReader(io.StringIO(files['review/candidate_manifest.csv'].decode('utf-8'))))
    except UnicodeError as exc:
        raise ReceiptError('B12R_CANDIDATE_CSV_ENCODING') from exc
    if not rows or len(rows) > 128:
        error('B12R_CANDIDATE_COUNT_INVALID')
    if not REQUIRED_COLUMNS <= set(rows[0]):
        error('B12R_CANDIDATE_SCHEMA_MISMATCH')
    if len({r['candidate_id'] for r in rows}) != len(rows):
        error('B12R_DUPLICATE_CANDIDATE')
    counts = Counter()
    for row in rows:
        for field, sha_field in [('source_image_path', 'source_image_sha256'),
                                 ('physics_path', 'physics_sha256')]:
            rel = 'raw/' + safe_rel(row[field])
            if rel not in files or digest(files[rel]) != row[sha_field]:
                error('B12R_CANDIDATE_HASH_MISMATCH ' + row['candidate_id'])
        try:
            size = int(row['physics_size_bytes'])
            cap = int(row['capture_stamp_ns'])
            pose = int(row['pose_at_capture_ns'])
        except (TypeError, ValueError) as exc:
            raise ReceiptError('B12R_INVALID_CANDIDATE_METADATA') from exc
        if (size != len(files['raw/' + row['physics_path']]) or cap <= 0
                or abs(cap - pose) > 250_000_000):
            error('B12R_CANDIDATE_METADATA_MISMATCH')
        if (row['source_archive_sha256'] != EXPECTED_A13_SHA
                or row['source_git_sha'] != EXPECTED_A13_GIT_SHA):
            error('B12R_CANDIDATE_PROVENANCE_MISMATCH')
        if row['label_status'] != 'REVIEW_REQUIRED' or row['suggested_label'] not in ('STABLE', 'UNSTABLE', 'REVIEW_REQUIRED'):
            error('B12R_LABEL_STATUS_INVALID')
        img = io.BytesIO(files['raw/' + row['source_image_path']])
        try:
            with Image.open(img) as im:
                im.verify()
            img.seek(0)
            with Image.open(img) as im:
                if im.format != 'PNG' or im.size != (640, 480) or im.mode != 'RGB':
                    error('B12R_IMAGE_FORMAT_INVALID')
        except (OSError, UnidentifiedImageError, SyntaxError) as exc:
            raise ReceiptError('B12R_IMAGE_CORRUPT') from exc
        if row['temporal_review'] != 'PASS':
            counts['temporal_hold'] += 1
        counts['suggested_' + row['suggested_label']] += 1
        counts['candidates'] += 1
    return rows, dict(counts)


def verify_bundle(archive: Path, sidecar: Path):
    archive = Path(archive)
    archive_sha = read_sidecar(archive, sidecar)
    files = read_archive(archive)
    verified = check_sums(files)
    try:
        status = json.loads(files['diagnostic_status.json'])
    except (ValueError, UnicodeError) as exc:
        raise ReceiptError('B12R_STATUS_INVALID') from exc
    if (status.get('exit_code') != 0 or status.get('status') != 'RUN_SUCCESS'
            or status.get('candidate_review_only') is not True
            or status.get('source_archive_sha256') != EXPECTED_A13_SHA
            or status.get('a13_source_git_sha') != EXPECTED_A13_GIT_SHA
            or not re.fullmatch(r'[0-9a-f]{40}', str(status.get('git_sha','')))):
        error('B12R_SOURCE_RUN_NOT_ACCEPTED')
    if ('SMARTDISH_B_A13_INTERNAL_HASH_PASS verified=88' not in files['execution.log'].decode('utf-8')
            or 'SMARTDISH_B_REAL_CANDIDATE_EXTRACTION_PASS' not in files['execution.log'].decode('utf-8')):
        error('B12R_SOURCE_LOG_PASS_MARKERS_MISSING')
    rows, counts = validate_candidates(files, status)
    validate_review_assets(files,rows)
    return files, {'schema': 1, 'result': 'B12R_REVIEW_WORKSPACE_READY',
                   'diagnostic_archive_sha256': archive_sha,
                   'diagnostic_members_verified': verified,
                   'b_run_git_sha': status['git_sha'],
                   'source_archive_sha256': EXPECTED_A13_SHA,
                   'verified_candidates': len(rows),
                   'candidate_counts': counts,
                   'operator_approvals': 0,
                   'approval_ledger_created': False,
                   'training_executed': False,
                   'source_a13_full_archive_reverified': False,
                   'note': 'B-15 diagnostic subset only. A13 full archive independently verified in prior run.'}, rows


def publish_workspace(archive: Path, sidecar: Path, output: Path):
    files, receipt, rows = verify_bundle(archive, sidecar)
    output = Path(output).expanduser().resolve()
    if output.exists():
        error('B12R_OUTPUT_EXISTS_NO_OVERWRITE')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.b12r-stage-',dir=output.parent) as temp:
        stage = Path(temp)
        for rel,contents in files.items():
            # Only approved paths from validated archive, never tar.extractall()
            path=stage/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as fp: fp.write(contents)
        (stage/'B12_REVIEW_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        csv_name=stage/'B12_REVIEW_DECISIONS_TEMPLATE.csv'
        fieldnames=('candidate_id','source_scene_id','suggested_label','temporal_review',
                    'decision','approved_label','reviewer_id','reason','license_status')
        with csv_name.open('w',encoding='utf-8',newline='') as fp:
            writer=csv.DictWriter(fp,fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({'candidate_id':row['candidate_id'],
                                 'source_scene_id':row['source_scene_id'],
                                 'suggested_label':row['suggested_label'],
                                 'temporal_review':row['temporal_review'],
                                 'decision':'','approved_label':'','reviewer_id':'',
                                 'reason':'','license_status':''})
        (stage/'B12_OPERATOR_STEPS_KO.md').write_text(
            '# B-12R 사람 승인 안내 — 승인 명령을 직접 입력해야 합니다\n\n'
            '1. review/review.html의 PNG와 SVG 12개 및 물리 Pose를 직접 검토합니다.\n'
            '2. B12_REVIEW_DECISIONS_TEMPLATE.csv는 **공란 템플릿**입니다. 편집만으로 승인 원장을 만들지 않습니다.\n'
            '3. 승인 또는 보류·제외 결정을 내린 후 아래 CLI에 **개별 candidate_id, 실사용자 reviewer_id, 이유, 사용권**을 지정합니다.\n\n'
            '```bash\n'
            'WORK="/실제/B12R/검토_작업폴더"\n'
            'python3 ai/scripts/review_a13_labels.py \\\n'
            '  --raw-dir "$WORK/raw" --review-dir "$WORK/review" \\\n'
            '  --candidate-id "<실제_candidate_id>" --reviewer-id "<실제_운영자>" \\\n'
            '  --decision DEFERRED --reason "검토 대기" --license-status UNVERIFIED\n'
            '```\n\n'
            'APPROVED는 사람이 `--approved-label`과 사용권을 명시한 경우에만 가능합니다.\n'
            '4. 운영자 승인 후 B-13 `register_a13_approved.py`를 별도 실행합니다.\n'
            '5. 현재 4개 후보는 클래스별 최대 2개 독립 그룹이므로 C 분할은 BLOCKED입니다.\n',encoding='utf-8')
        for rel in files:
            if rel.startswith('raw/'):
                (stage/rel).chmod(0o444)
        os.rename(stage,output)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--sha256-file',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    sidecar=args.sha256_file or Path(str(args.archive)+'.sha256')
    try:
        receipt=publish_workspace(args.archive,sidecar,args.output)
    except (OSError, ReceiptError,ValueError) as exc:
        print('B12R_RECEIVE_BLOCKED '+str(exc))
        raise SystemExit(2)
    print('B12R_RECEIVE_SHA_PASS '+receipt['diagnostic_archive_sha256'])
    print('B12R_REVIEW_WORKSPACE_READY candidates='+str(receipt['verified_candidates']))
    print('B_LABEL_APPROVAL_PENDING approved=0')


if __name__=='__main__':
    main()
