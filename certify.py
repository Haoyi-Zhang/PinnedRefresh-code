#!/usr/bin/env python3
"""Produce or verify a certificate for one trace JSON file."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from src.producer import produce
from src.checker import verify


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('trace',type=Path)
    p.add_argument('--certificate',type=Path,help='verify an existing certificate instead of producing one')
    p.add_argument('--output',type=Path,help='write produced certificate; otherwise print JSON')
    a=p.parse_args()
    try:
        tr=json.loads(a.trace.read_text())
        if a.certificate:
            cert=json.loads(a.certificate.read_text())
            ok=verify(tr,cert)
            print('VALID' if ok else 'INVALID')
            return 0 if ok else 1
        cert=produce(tr)
        if not verify(tr,cert): raise ValueError('produced certificate failed checking')
        text=json.dumps(cert,indent=2)+'\n'
        if a.output:
            a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(text)
        else: print(text,end='')
        return 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(f'error: {e}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
