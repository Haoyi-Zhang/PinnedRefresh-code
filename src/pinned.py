"""Uniform pinned-share refresh and its reduction to trace certificates.

Pins are deterministic equality constraints, NOT observed random differences.
This is an ideal algebraic update model. See the manuscript for the passive,
refresh-atomic private-channel realization and the assumptions it requires.
"""
from __future__ import annotations
from collections import Counter
from itertools import product
from .model import validate, integer
from .checker import evaluate


def validate_pinned(case: dict) -> None:
    if not isinstance(case,dict) or set(case)!={'field','threshold','epochs','pins','exposed'}:
        raise ValueError('pinned case requires field, threshold, epochs, pins, exposed')
    q,k,t=(case[z] for z in ('field','threshold','epochs'))
    validate({'field':q,'threshold':k,'epochs':t,'observations':[]})
    if not isinstance(case['pins'],list) or len(case['pins'])!=t-1 or not isinstance(case['exposed'],list) or len(case['exposed'])!=t:
        raise ValueError('pin or exposure epoch lengths do not match')
    coords=set()
    for subset in case['pins']+case['exposed']:
        if not isinstance(subset,list) or any(not integer(x) or not 1<=x<q for x in subset) or len(subset)!=len(set(subset)):
            raise ValueError('each pin/exposure set must contain distinct nonzero coordinates')
        coords.update(subset)
    if len(coords)>24 or sum(map(len,case['exposed']))>64:
        raise ValueError('pinned case exceeds coordinate/exposure budget')


def to_trace(case: dict) -> dict:
    validate_pinned(case)
    # Ordered equality rows precede the ordered exposed-share rows. Their outputs
    # are zero. All remaining rows are observations of current valid shares.
    obs=[{'kind':'delta','before':e,'after':e+1,'x':x} for e,xs in enumerate(case['pins']) for x in xs]
    obs += [{'kind':'snapshot','epoch':e,'x':x} for e,xs in enumerate(case['exposed']) for x in xs]
    result={z:case[z] for z in ('field','threshold','epochs')};result['observations']=obs
    # At most 264 deterministic pin equations plus 64 exposed values.
    # Pin equations are not corruption events; the generic 64-observation
    # input validator is deliberately not applied to this internal encoding.
    return result


def multiply(a: list[int], b: list[int], q: int) -> list[int]:
    out=[0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):out[i+j]=(out[i+j]+x*y)%q
    return out


def increment_coefficients(pins: list[int], free: list[int], k: int, q: int) -> list[int]:
    d=max(k-1-len(pins),0)
    if len(free)!=d:raise ValueError('incorrect increment coefficient count')
    if d==0:return [0]*k
    factor=[0,1]
    for x in pins:factor=multiply(factor,[-x%q,1],q)
    p=multiply(factor,free,q)
    return p+[0]*(k-len(p))


def exact_pinned(case: dict, cap: int = 20000) -> dict:
    validate_pinned(case)
    q,k,t=(case[z] for z in ('field','threshold','epochs'))
    dims=[max(k-1-len(o),0) for o in case['pins']]
    randomness=(k-1)+sum(dims);assignments=q**(1+randomness)
    if assignments>cap:raise ValueError('pinned exact-oracle cap exceeded')
    hist=[]
    for s in range(q):
        counts=Counter()
        for r in product(range(q),repeat=randomness):
            poly=[s]+list(r[:k-1]);states=[poly];offset=k-1
            for pins,d in zip(case['pins'],dims):
                inc=increment_coefficients(pins,list(r[offset:offset+d]),k,q);offset+=d
                nxt=[(a+b)%q for a,b in zip(poly,inc)]
                if any(evaluate(poly,x,q)!=evaluate(nxt,x,q) for x in pins):raise AssertionError('pin invariant failed')
                states.append(nxt);poly=nxt
            out=tuple((sum(coef*x**j for j,coef in enumerate(states[e])))%q for e,xs in enumerate(case['exposed']) for x in xs)
            counts[out]+=1
        hist.append(counts)
    same=all(h==hist[0] for h in hist[1:]);supports=[set(h) for h in hist]
    disjoint=all(supports[i].isdisjoint(supports[j]) for i in range(q) for j in range(i+1,q))
    return {'assignment_count':assignments,'refresh_dimensions':dims,'initial_randomness_dimension':k-1,
            'conditional_support_sizes':[len(h) for h in hist],
            'multiplicities':sorted({c for h in hist for c in h.values()}),
            'verdict':'hiding' if same else 'revealing' if disjoint else 'partial',
            'histograms':[[{'observations':list(v),'count':n} for v,n in sorted(h.items())] for h in hist]}


def local_union_sizes(case: dict) -> list[int]:
    validate_pinned(case)
    return [len(set(case['exposed'][e])|(set(case['pins'][e-1]) if e else set())|(set(case['pins'][e]) if e<case['epochs']-1 else set())) for e in range(case['epochs'])]


def lower_bound_case(k: int, u: int, b: int, q: int) -> dict:
    """A pin-and-exposure trace revealing k current shares at its central epoch."""
    if b<1 or k>2*u+b:raise ValueError('lower-bound parameters do not apply')
    c=min(b,k);a=min(u,k-c);d=k-c-a
    left=list(range(1,a+1));center=list(range(a+1,a+c+1));right=list(range(a+c+1,k+1))
    left_chunks=[left[j:j+b] for j in range(0,a,b)]
    right_chunks=[right[j:j+b] for j in range(0,d,b)]
    exposed=left_chunks+[center]+right_chunks
    pins=[left[:] for _ in left_chunks]+[right[:] for _ in right_chunks]
    case={'field':q,'threshold':k,'epochs':len(exposed),'pins':pins,'exposed':exposed}
    validate_pinned(case);return case


def exact_local_simulation() -> dict:
    """One nontrivial real/ideal refresh-message distribution, exactly enumerated.

q=5, degree<3, pinned x=1, online coordinates 2,3,4. Dealer 2 and
recipient 2 are corrupted; dealers 3 and 4 are honest. Each increment is
r*X*(X-1). The transcript contains aggregate r, corrupted r, and both honest
messages to x=2. Honest randomness is erased after the atomic refresh.
"""
    q=5;real=Counter();ideal=Counter()
    for c,h1,h2 in product(range(q),repeat=3):
        real[((c+h1+h2)%q,c,2*h1%q,2*h2%q)]+=1
    for total,c,message in product(range(q),repeat=3):
        ideal[(total,c,message,(2*(total-c)-message)%q)]+=1
    if real!=ideal:raise AssertionError('local simulation distributions differ')
    return {'real_assignment_count':125,'ideal_assignment_count':125,'distinct_transcripts':len(real),
            'equal_histograms':True,'multiplicities':sorted(set(real.values())),
            'histogram':[{'transcript':list(v),'count':n} for v,n in sorted(real.items())]}
