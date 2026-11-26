#!/usr/bin/env python3
"""CPU-only offline Owner QA03 release-HOLD runner with private diagnostics."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,os,sys,tarfile,datetime
from pathlib import Path
from audit_b_a15 import audit_owner,owner_missing_report,review_rows,QAError,OWNER_SHA


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def make_diagnostics(out,result,rc):
    """Never embed original Owner TAR, human review decisions, or training data."""
    meta={'schema':1,'scope':'B_QA03_PRIVATE_DIAGNOSTIC_NOT_TRAINING_DATA',
          'result_code':rc,'actual_owner_raw_directly_recomputed':result['actual_owner_raw_directly_recomputed'],
          'approved_count':0,'training_executed':False}
    (out/'diagnostic_status.json').write_text(json.dumps(meta,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    items=[out/n for n in ('qa_report.json','review_worksheet.csv','diagnostic_status.json') if (out/n).is_file()]
    summed=''.join(f'{digest(x)}  {x.name}\n' for x in items).encode()
    dest=out/'b_a15_qa03_diagnostics.tar.gz'
    with tarfile.open(dest,'x:gz') as tar:
        for p in items:tar.add(p,arcname=p.name,recursive=False)
        info=tarfile.TarInfo('SHA256SUMS');info.size=len(summed);info.mode=0o600
        tar.addfile(info,io.BytesIO(summed))
    side=Path(str(dest)+'.sha256');side.write_text(f'{digest(dest)}  {dest.name}\n')
    print('B_A15_QA03_DIAGNOSTICS='+str(dest),flush=True)
    print('B_A15_QA03_DIAGNOSTICS_SHA='+digest(dest),flush=True)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner',type=Path,required=True,help='Exact A15 WSL2 Owner TAR (never Cloud)')
    p.add_argument('--sha256-file',type=Path,help='Owner TAR companion sidecar')
    p.add_argument('--out-dir',type=Path,required=True,help='Nonexisting PRIVATE output directory')
    a=p.parse_args(argv)
    out=a.out_dir.expanduser().absolute()
    if out.exists():print('B_A15_QA03_OUTPUT_EXISTS_NO_OVERWRITE',file=sys.stderr);return 2
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    try:os.chmod(out,0o700)
    except OSError:pass
    report=owner_missing_report();code=2
    owner=a.owner.expanduser().absolute()
    side=(a.sha256_file or Path(str(owner)+'.sha256')).expanduser().absolute()
    if owner.is_symlink() or side.is_symlink() or not owner.is_file() or not side.is_file():
        report['first_error']='B_A15_OWNER_INPUT_OR_SIDECAR_MISSING'
    else:
        try:
            if owner.stat().st_size>400*1024*1024:raise QAError('B_A15_OWNER_COMPRESSED_LIMIT')
            report=audit_owner(owner.read_bytes(),side.read_bytes());code=0
        except (QAError,OSError,KeyError,ValueError,UnicodeError,TypeError) as exc:
            report['first_error']=str(exc)
            report['reason']='B_A15_OWNER_INTAKE_OR_PHYSICS_VALIDATION_FAILED'
    (out/'qa_report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8')
    rows=review_rows(report)
    if rows:
        with (out/'review_worksheet.csv').open('x',newline='',encoding='utf8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    make_diagnostics(out,report,code)
    print('B_A15_OWNER_RAW_AUDIT_VERIFIED_REVIEW_ONLY' if code==0 else 'B_A15_OWNER_RAW_AUDIT_HOLD',flush=True)
    print('B_A15_QA03_DATASET_RELEASE_HOLD approved=0',flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
