#!/usr/bin/env python3
"""Deterministic theorem witnesses; not a sample of real availability workloads."""
from pathlib import Path
import argparse,itertools,json,random
from src.budgets import capacities,lower_trace,bottleneck_partition


def generate() -> dict:
    math_cases=[]
    for b in itertools.product(range(2),repeat=2):
        for u in range(2):math_cases.append({'exposures':list(b),'pins':[u]})
    for b in itertools.product(range(2),repeat=3):math_cases.append({'exposures':list(b),'pins':[1,2]})
    for b,u in [([2,2,2,2],[3,3,3]),([1,0,2,1],[0,2,0]),([0,3,0,1],[2,1,2]),([2,0,0,2],[3,1,3])]:math_cases.append({'exposures':b,'pins':u})
    rnd=random.Random(20260913);variables=[]
    for i in range(8):
        t=i+3;b=[2]+[rnd.randrange(3) for _ in range(t-1)];u=[rnd.randrange(4) for _ in range(t-1)]
        g=capacities(b,u)['capacity'];k=max(2,g+1)
        case={'field':29,'threshold':k,'epochs':t,'pins':[sorted(rnd.sample(range(1,25),v)) for v in u],
              'exposed':[sorted(rnd.sample(range(1,25),v)) for v in b]}
        variables.append({'id':f'variable-budget-{i:02d}','exposures':b,'pins':u,'upper_case':case,
                          'lower_witness':lower_trace(b,u,g),'partition':bottleneck_partition(b,u)})
    return {
        'coordinate_pool':list(range(1,25)),
        'mathematical_cases':math_cases,
        'variable_cases':variables,
        'schedule_case':{'exposures':[1]*7,'pins':[1,0,2,0,1,1],'threshold':4,'charges':[3,1,4,1,5,2]},
        'mandatory_schedule_case':{
            'exposures':[2,1],
            'pins':[2],
            'threshold':4,
            'charges':[1],
            'allowed':[True],
            'mandatory':[True],
            'max_refreshes':1,
            'pool_size':5,
            'field':7,
        },
    }

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(generate(),indent=2,sort_keys=True)+'\n')
