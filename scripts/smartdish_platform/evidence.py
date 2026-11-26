"""Read-only bounded archive integrity; no label promotion or archive extraction."""
import hashlib
import re
import tarfile
from pathlib import Path,PurePosixPath

def sha256(path):
    with Path(path).open("rb") as f: return hashlib.file_digest(f,"sha256").hexdigest()

def verify_archive(path, expected_sha, *, max_bytes=128*1024*1024, max_members=500):
    if not re.fullmatch("[0-9a-f]{64}",expected_sha) or sha256(path)!=expected_sha:
        raise ValueError("PLATFORM_ARCHIVE_SHA_MISMATCH")
    hashes={};manifest=None;size=0
    with tarfile.open(path,"r:gz") as t:
        for m in t:
            p=PurePosixPath(m.name)
            if not m.isfile() or p.is_absolute() or ".." in p.parts or m.name!=p.as_posix() or m.name in hashes:
                raise ValueError("PLATFORM_ARCHIVE_UNSAFE_MEMBER")
            size+=m.size
            if size>max_bytes or len(hashes)>=max_members: raise ValueError("PLATFORM_ARCHIVE_LIMIT")
            with t.extractfile(m) as f:
                if m.name=="SHA256SUMS":
                    manifest=f.read().decode()
                    hashes[m.name]=None
                else:
                    hashes[m.name]=hashlib.file_digest(f,"sha256").hexdigest()
    if manifest is None: raise ValueError("PLATFORM_MANIFEST_MISSING")
    del hashes["SHA256SUMS"]
    checked={}
    for line in manifest.splitlines():
        h,n=line.split("  ",1)
        if n in checked or n not in hashes or hashes[n]!=h:
            raise ValueError("PLATFORM_MANIFEST_MISMATCH")
        checked[n]=h
    if not checked or checked!=hashes: raise ValueError("PLATFORM_MANIFEST_COVERAGE")
    return {"archive_sha256":expected_sha,"manifest_count":len(checked),"integrity":"PASS"}

def evidence_state(data,gui,cleanup,stopped):
    if data not in ("PASS","HOLD") or gui not in ("PASS","FAIL","NOT_RUN","NOT_REQUESTED") or cleanup not in ("PASS","FAIL","NOT_RUN") or type(stopped) is not bool:
        raise ValueError("PLATFORM_VERDICT_INVALID")
    return {"data":data,"gui":gui,"cleanup":cleanup,"all_owned_stopped":stopped,
            "next_independent_scene_allowed":data=="PASS" and stopped,
            "ground_truth":"UNKNOWN_HOLD","human_approved":False}
