#!/usr/bin/env python3
"""Deterministic boundary and proof-falsification inputs for pinned refresh."""
from __future__ import annotations
import argparse,json,random
from pathlib import Path
from src.pinned import lower_bound_case,to_trace


def generate():
    records=[]
    def add(ident,family,case,expected,oracle=False):
        to_trace(case)
        records.append({'id':ident,'family':family,'case':case,'expected':expected,'exact_oracle':oracle})
    add('pinned-switch','exact-control',{'field':5,'threshold':3,'epochs':3,'pins':[[1],[3]],'exposed':[[1],[2],[3]]},'revealing',True)
    add('pinned-fixed','exact-control',{'field':5,'threshold':3,'epochs':3,'pins':[[1],[1]],'exposed':[[1],[2],[3]]},'hiding',True)
    # Predeclared lower-bound grid; every case is a theorem-generated witness,
    # not an independently sampled deployment or workload.
    idx=0
    for k in range(2,10):
        for u in range(0,4):
            for b in (1,2):
                if k<=2*u+b:
                    add(f'pinned-lower-{idx:02d}','lower-bound',lower_bound_case(k,u,b,11),'revealing');idx+=1
    rng=random.Random(20260912)
    for idx in range(24):
        # A nontrivial strict-upper-bound family: b=2,u=2,k=7.
        t=4+(idx%5);pins=[sorted(rng.sample(range(1,25),2)) for _ in range(t-1)]
        exposed=[sorted(rng.sample(range(1,25),2)) for _ in range(t)]
        add(f'pinned-upper-{idx:02d}','strict-upper-bound',{'field':29,'threshold':7,'epochs':t,'pins':pins,'exposed':exposed},'hiding')
    # No observations: secrecy holds even when every update is forced to zero.
    add('pinned-zero-exposure','zero-exposure',{'field':7,'threshold':3,'epochs':3,'pins':[[1,2,3],[2,3,4]],'exposed':[[],[],[]]},'hiding')
    # The input envelope counts exposed values separately from pin equations.
    for hidden in (True,False):
        exposed=[list(range(1,7)) if e<4 else list(range(1,6)) for e in range(12)]
        if not hidden:
            exposed[1]=list(range(7,13))
        add('pinned-max-hidden' if hidden else 'pinned-max-revealed','maximum-constraint-shape',
            {'field':29,'threshold':12,'epochs':12,'pins':[list(range(1,25)) for _ in range(11)],'exposed':exposed},
            'hiding' if hidden else 'revealing')
    for x in (5,6):
        add(f'pinned-coordinate-{x}','coordinate-sensitive',
            {'field':7,'threshold':3,'epochs':2,'pins':[[x]],'exposed':[[1,2],[3,4]]},
            'hiding' if x==5 else 'revealing')
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(generate(),indent=2)+'\n')
