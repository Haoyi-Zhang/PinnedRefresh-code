#!/usr/bin/env python3
"""Create or verify a pinned-path certificate for a single supplied JSON case."""
import argparse,json,sys
from pathlib import Path
from src.pinned_producer import produce_pinned
from src.pinned_checker import verify_pinned
p=argparse.ArgumentParser(description=__doc__);p.add_argument('case',type=Path)
g=p.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=Path);g.add_argument('--certificate',type=Path)
a=p.parse_args()
try:
    case=json.loads(a.case.read_text())
    if a.output:
        cert=produce_pinned(case)
        if not verify_pinned(case,cert):raise AssertionError('producer certificate failed verification')
        a.output.write_text(json.dumps(cert,indent=2)+'\n');print(cert['kind'])
    else:
        cert=json.loads(a.certificate.read_text())
        if not verify_pinned(case,cert):raise ValueError('certificate rejected')
        print('accepted '+cert['kind'])
except (OSError,ValueError,AssertionError) as e:print('FAILED: '+str(e),file=sys.stderr);raise SystemExit(1)
