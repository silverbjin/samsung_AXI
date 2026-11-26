#!/usr/bin/env python3
"""B12R owner one-shot: CWD-independent read-only receipt + private PASS/FAIL TAR.

This is a human-review preparation tool, never an operator approval or C training.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import secrets
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from receive_b15_diagnostics import ReceiptError, publish_workspace, read_sidecar
from audit_a13_independent_groups import preview_candidates

MAX_MEMBER_BYTES = 9 * 1024 * 1024
MAX_BUNDLE_BYTES = 28 * 1024 * 1024
MAX_MEMBERS = 120
PNG_ALLOW = re.compile(r'^raw/trial_\d{4}/(?:tray_rgb\.png|physics_observations\.jsonl|capture_metadata\.json|initial_state\.json|final_state\.json|trial_summary\.json)$')
SVG_ALLOW = re.compile(r'^review/plots/B13-[0-9a-f]{20}_(?:z|tilt_deg|xy)\.svg$')
REVIEW_ALLOW = frozenset({
    'review/review.html', 'review/candidate_manifest.csv', 'review/evidence_audit.json',
    'B12_REVIEW_RECEIPT.json', 'B12_REVIEW_DECISIONS_TEMPLATE.csv',
    'B14_INDEPENDENCE_AUDIT.json', 'B12_OPERATOR_STEPS_KO.md'
})

class CliError(ValueError):
    pass

class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise CliError('B12R_ARGUMENT_INVALID ' + message)


def digest_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def note(lines: list[str], message: str, *, err=False):
    lines.append(('STDERR ' if err else 'STDOUT ') + message)
    print(message, file=sys.stderr if err else sys.stdout, flush=True)


def hash_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as fp:
        for block in iter(lambda:fp.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def resolve_archive(root: Path, requested: str | None) -> Path:
    if requested:
        archive=Path(requested).expanduser().absolute()
        if not archive.is_file():
            raise CliError('B12R_ARCHIVE_NOT_FOUND path='+str(archive))
        return archive
    folder=root/'ai/data/private/b_a13_diagnostics'
    candidates=sorted(folder.glob('smartdish_b_a13_*_diagnostics.tar.gz'),
                      key=lambda p:(p.stat().st_mtime_ns,p.name),reverse=True) if folder.exists() else []
    if not candidates:
        raise CliError('B12R_ARCHIVE_NOT_FOUND auto_discovery_dir='+str(folder))
    # Never choose an older file silently when the most recent candidate is invalid.
    return candidates[0]


def validate_sha(root: Path, expected: str) -> str:
    if not re.fullmatch(r'[0-9a-f]{40}',expected):
        raise CliError('B12R_GIT_SHA_INVALID')
    probe=subprocess.run(['git','-C',str(root),'rev-parse','HEAD'],text=True,capture_output=True)
    if probe.returncode or probe.stdout.strip()!=expected:
        raise CliError('B12R_CODE_SHA_PIN_MISMATCH')
    status=subprocess.run(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True,capture_output=True)
    if status.returncode or status.stdout.strip():
        raise CliError('B12R_DIRTY_TRACKED_WORKTREE')
    return expected


def safe_output(root: Path, requested: str | None, identifier: str, archive: Path | None):
    out=(Path(requested).expanduser().absolute() if requested else
         root/'ai/data/private'/('b12_operator_review_'+identifier))
    private=root/'ai/data/private'
    if not out.resolve().is_relative_to(private.resolve()) or out==private or out.exists() or out.is_symlink():
        raise CliError('B12R_WORKDIR_INVALID_OR_EXISTS path='+str(out))
    if archive and (out==archive or out in archive.parents):
        raise CliError('B12R_WORKDIR_INVALID')
    return out


def add_bytes(tar: tarfile.TarFile, rel: str, data: bytes):
    info=tarfile.TarInfo(rel)
    info.size=len(data);info.mode=0o600;info.mtime=0;info.uid=0;info.gid=0
    info.uname=info.gname=''
    tar.addfile(info,io.BytesIO(data))


def prepare_entries(workspace: Path | None, lines: list[str], status: dict):
    files=[('execution.log', ('\n'.join(lines)+'\n').encode('utf-8'))]
    if workspace and workspace.is_dir():
        for p in sorted(workspace.rglob('*')):
            if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(workspace.resolve()):
                continue
            rel=p.relative_to(workspace).as_posix()
            if rel in REVIEW_ALLOW or PNG_ALLOW.fullmatch(rel) or SVG_ALLOW.fullmatch(rel):
                files.append((rel,p.read_bytes()))
    files.append(('diagnostic_status.json',(json.dumps(status,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()))
    if len(files)+1>MAX_MEMBERS or any(len(v)>MAX_MEMBER_BYTES for _,v in files) or sum(map(lambda x:len(x[1]),files))>MAX_BUNDLE_BYTES:
        raise CliError('B12R_DIAGNOSTIC_SIZE_LIMIT')
    names=[x[0] for x in files]
    if len(names)!=len(set(names)):
        raise CliError('B12R_DIAGNOSTIC_DUPLICATE')
    linesum=''.join(digest_bytes(v)+'  '+name+'\n' for name,v in files)
    files.append(('SHA256SUMS',linesum.encode()))
    return files


def save_diagnostics(root: Path, lines: list[str], status: dict, workspace:Path|None,identifier:str):
    folder=root/'ai/data/private/b12r_diagnostics'
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    archive=folder/('smartdish_b12r_'+identifier+'_diagnostics.tar.gz')
    files=prepare_entries(workspace,lines,status)
    with tempfile.NamedTemporaryFile(prefix='.b12r-',suffix='.tar.gz.part',dir=folder,delete=False) as tf:
        temporary=Path(tf.name)
    try:
        with tarfile.open(temporary,'w:gz',format=tarfile.PAX_FORMAT) as t:
            for name,data in files:
                add_bytes(t,name,data)
        # No overwrite on generated name collision. Link is atomic on same filesystem.
        os.link(temporary,archive)
        archive_sha=hash_file(archive)
        sidecar=Path(str(archive)+'.sha256')
        with sidecar.open('x',encoding='utf-8') as fp:
            fp.write(archive_sha+'  '+archive.name+'\n')
        if read_sidecar(archive,sidecar)!=archive_sha:
            raise CliError('B12R_DIAGNOSTIC_SIDECAR_SELF_CHECK_FAILED')
        return archive,archive_sha,len(files)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None, *, repo_root=None):
    parser=SafeArgumentParser(description=__doc__)
    parser.add_argument('--sha',required=True,help='Pinned 40-digit current Git commit SHA')
    parser.add_argument('--archive',help='Existing B-15 diagnostics TAR.GZ (default: latest local B15)')
    parser.add_argument('--sha256-file',help='Explicit B-15 sidecar path (default: TAR path + .sha256)')
    parser.add_argument('--output',help='New absolute workspace under ai/data/private (never overwrite)')
    parser.add_argument('--mode',default='review',help='Only review is permitted')
    arg_error=None
    try:
        args=parser.parse_args(argv)
    except CliError as exc:
        arg_error=exc
        args=argparse.Namespace(sha='',archive=None,sha256_file=None,output=None,mode='review')
    root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
    identifier=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+str(os.getpid())+'_'+secrets.token_hex(3)
    lines=[];workspace=None;archive=None;archive_sha=None;receipt=None;rc=0;cause=None
    try:
        if arg_error is not None:
            raise arg_error
        if args.mode!='review':
            raise CliError('B12R_AUTO_APPROVAL_FORBIDDEN')
        sha=validate_sha(root,args.sha)
        note(lines,'B12R_CODE_SHA_PIN_PASS sha='+sha)
        archive=resolve_archive(root,args.archive)
        sidecar=Path(args.sha256_file).expanduser().absolute() if args.sha256_file else Path(str(archive)+'.sha256')
        if not sidecar.is_file():
            raise CliError('B12R_SIDECAR_MISSING path='+str(sidecar))
        # Existing B-12R library verifier; NEVER call sha256sum -c from an arbitrary CWD.
        try:
            archive_sha=read_sidecar(archive,sidecar)
        except ReceiptError as exc:
            raise CliError(str(exc)) from exc
        note(lines,'B12R_DIAGNOSTIC_ARCHIVE_SHA_PASS '+archive_sha)
        workspace=safe_output(root,args.output,identifier,archive)
        receipt=publish_workspace(archive,sidecar,workspace)
        note(lines,'B12R_REVIEW_WORKSPACE_READY candidates='+str(receipt['verified_candidates']))
        from csv import DictReader
        with (workspace/'review/candidate_manifest.csv').open(newline='',encoding='utf-8') as fp:
            rows=list(DictReader(fp))
        audit=preview_candidates(rows)
        (workspace/'B14_INDEPENDENCE_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
        if audit.get('status')!='B_DATASET_SPLIT_BLOCKED' or len(rows)!=receipt['verified_candidates']:
            raise CliError('B12R_AUDIT_RESULT_UNEXPECTED')
        note(lines,'B14_SEED_ONLY_GROUPS_NOT_INDEPENDENT')
        note(lines,'B_DATASET_SPLIT_BLOCKED '+json.dumps(audit['independent_templates_by_suggested_label'],sort_keys=True))
        if (workspace/'review/approval_ledger.jsonl').exists() or (workspace/'ai/data/manifest.csv').exists():
            raise CliError('B12R_UNAUTHORIZED_APPROVAL_OUTPUT')
        note(lines,'B_LABEL_APPROVAL_PENDING approved=0')
        note(lines,'B12R_REVIEW_DIR='+str(workspace))
    except (CliError,ReceiptError,OSError,ValueError,KeyError) as exc:
        rc=2;cause=('B12R_CANDIDATE_SCHEMA_MISMATCH '+str(exc) if isinstance(exc,KeyError) else str(exc))
        note(lines,'B12R_ONE_SHOT_BLOCKED '+cause,err=True)
    state={'schema':1,'status':'RUN_SUCCESS' if rc==0 else 'RUN_FAILED',
           'exit_code':rc,'error_code':cause.split()[0] if cause else None,
           'git_sha_requested':args.sha,'source_diagnostic_archive_sha256':archive_sha,
           'source_diagnostic_basename':archive.name if archive else None,
           'workspace':str(workspace) if workspace else None,
           'candidates':receipt['verified_candidates'] if receipt else 0,
           'approved_labels':0,'approval_ledger_created':False,
           'training_executed':False,'full_a13_archive_reverified':False}
    try:
        bundle,b_sha,members=save_diagnostics(root,lines,state,workspace,identifier)
        note(lines,'B12R_DIAGNOSTIC_ARCHIVE_CREATED path='+str(bundle)+' sha256='+b_sha+' members='+str(members))
        note(lines,'B12R_DIAGNOSTIC_SHA256_FILE path='+str(bundle)+'.sha256')
    except (OSError,ValueError,ReceiptError) as exc:
        note(lines,'B12R_DIAGNOSTIC_ARCHIVE_FAILED '+str(exc),err=True)
        if rc==0:rc=4
    return rc

if __name__=='__main__':
    raise SystemExit(main())
