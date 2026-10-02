#!/usr/bin/env python3
"""Regenerate the frozen, bounded mathematical input corpus."""
from __future__ import annotations
import argparse, itertools, json, random
from pathlib import Path


def snap(e, x): return {"kind":"snapshot", "epoch":e, "x":x}
def delta(u, v, x): return {"kind":"delta", "before":u, "after":v, "x":x}
def trace(q, k, t, obs): return {"field":q, "threshold":k, "epochs":t, "observations":obs}


def generate() -> list[dict]:
    cases=[]
    def add(identifier, family, tr, oracle=False, expected=None):
        r={"id":identifier, "family":family, "trace":tr, "exact_oracle":oracle}
        if expected is not None: r['expected']=expected
        cases.append(r)
    for z in (5,6):
        add(f'coordinate-{z}','saturated-pilot',trace(7,3,2,[snap(0,1),snap(0,2),snap(1,3),snap(1,4),delta(0,1,z)]),True,'hiding' if z==5 else 'revealing')
    for q in (3,5):
        choices=[None]+list(range(1,q))
        idx=0
        for a,b in itertools.product(choices,repeat=2):
            for mask in range(1 << (q-1)):
                obs=([snap(0,a)] if a else [])+([snap(1,b)] if b else [])
                obs += [delta(0,1,x) for x in range(1,q) if mask & (1 << (x-1))]
                add(f'field-{q}-{idx:03d}',f'field-{q}-threshold-two',trace(q,2,2,obs),q==3 or idx%17==0)
                idx+=1
    idx=0
    for a,b in itertools.product(list(itertools.combinations(range(1,5),2)),repeat=2):
        for z in (None,1,2,3,4):
            obs=[snap(0,x) for x in a]+[snap(1,x) for x in b]+([delta(0,1,z)] if z else [])
            add(f'saturated-{idx:03d}','field-5-saturated',trace(5,3,2,obs)); idx+=1
    add('chain-global','chain',trace(7,3,3,[snap(0,1),snap(1,2),snap(2,3),delta(0,1,1),delta(1,2,3)]),False,'revealing')
    add('chain-left','chain',trace(7,3,2,[snap(0,1),snap(1,2),delta(0,1,1)]),False,'hiding')
    add('chain-right','chain',trace(7,3,2,[snap(0,2),snap(1,3),delta(0,1,3)]),False,'hiding')
    rng=random.Random(20260911)
    for idx in range(80):
        if idx<20:
            q,k,t=7,3,3; obs=[]
            for _ in range(rng.randrange(0,19)):
                x=rng.randrange(1,q)
                if rng.randrange(2): obs.append(snap(rng.randrange(t),x))
                else:
                    u,v=sorted(rng.sample(range(t),2)); obs.append(delta(u,v,x))
            expected=None; family='generated-general'
        elif idx<40:
            q,k,t=7,3,4; obs=[]
            for _ in range(rng.randrange(1,12)):
                u,v=sorted(rng.sample(range(t),2)); x=rng.randrange(1,q)
                obs.extend([snap(u,x),delta(u,v,x)])
            expected=None; family='generated-anchored'
        elif idx<60:
            q,k,t=11,4,5
            obs=[snap(rng.randrange(t),rng.randrange(1,q)) for _ in range(rng.randrange(0,30))]
            expected=None; family='generated-snapshot'
        else:
            q,k,t=29,12,12
            hidden=idx%2==0
            obs=[delta(0,1,x) for x in range(1,25)]
            obs += [snap(0,x) for x in range(1,12 if hidden else 13)]
            while len(obs)<64:
                if rng.randrange(2):
                    obs.append(snap(rng.randrange(t),rng.randrange(1,12)))
                else:
                    u,v=sorted(rng.sample(range(t),2)); obs.append(delta(u,v,rng.randrange(1,25)))
            expected='hiding' if hidden else 'revealing'; family='dimension-boundary'
        add(f'generated-{idx:02d}',family,trace(q,k,t,obs),False,expected)
    fixtures=[
        ('lifetime-retained',trace(7,2,2,[snap(0,1),snap(0,2)]),'revealing'),
        ('lifetime-erased',trace(7,2,2,[snap(0,1),snap(1,2)]),'hiding'),
        ('recovery-mixed',trace(7,3,2,[snap(0,1),snap(0,2),snap(1,3),snap(1,4)]),'hiding'),
        ('recovery-common',trace(7,3,2,[snap(0,1),snap(0,2),snap(1,3),snap(1,4),snap(1,5)]),'revealing'),
        ('full-state-coordinate-5',trace(7,3,2,[snap(0,1),snap(0,2),snap(1,3),snap(1,4),snap(0,5),delta(0,1,5)]),'revealing'),
        ('full-state-coordinate-6',trace(7,3,2,[snap(0,1),snap(0,2),snap(1,3),snap(1,4),snap(0,6),delta(0,1,6)]),'revealing'),
        ('empty-observations',trace(3,2,1,[]),'hiding'),
        ('repeated-snapshot',trace(5,3,1,[snap(0,1)]*4),'hiding'),
        ('anchored-delta',trace(7,3,2,[snap(0,1),snap(0,2),delta(0,1,1),snap(1,3),snap(1,4)]),'revealing'),
        ('unanchored-delta',trace(7,3,2,[snap(0,1),snap(0,2),snap(1,3),snap(1,4),delta(0,1,5)]),'hiding')]
    for ident,tr,verdict in fixtures: add(ident,'boundary-fixture',tr,False,verdict)
    return cases

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(generate(),indent=2)+'\n')
