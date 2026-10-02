#!/usr/bin/env python3
"""Bounded exact trace validation. Writes only into the explicit output directory."""
from __future__ import annotations
import argparse, collections, copy, csv, io, json, resource, sys, time, unittest
from pathlib import Path
from src.producer import produce
from src.checker import verify
from src.oracle import exact_distributions
from src.structural import saturated_verdict, snapshot_verdict, anchored_closure
from src.adaptive import exact_policy


def atomic_json(path: Path, value: object) -> None:
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n'); tmp.replace(path)


def run(output: Path, reuse_pilot: Path | None = None) -> dict:
    root=Path(__file__).resolve().parent
    # CPU and address-space limits apply only to this process. One worker, no children.
    resource.setrlimit(resource.RLIMIT_CPU,(110,115))
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    wall=time.perf_counter(); cpu=time.process_time()
    corpus=json.loads((root/'cases/traces.json').read_text())
    if len(corpus)>1000: raise ValueError('trace limit exceeded')
    ids=[r['id'] for r in corpus]
    if len(ids)!=len(set(ids)): raise ValueError('duplicate case identifier')
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('output directory is not empty; use an empty directory')
    pilot_cache={}
    if reuse_pilot:
        pilot_doc=json.loads(reuse_pilot.read_text())
        pilot_cache={r['case']:r for r in pilot_doc['records']}
    records=[]; family_counts=collections.Counter(); verdicts=collections.Counter()
    direct_assignments=0; reused_assignments=0; cert_checks=0; mutations=0; structural_checks=0; transforms=0
    for index,case in enumerate(corpus):
        if time.perf_counter()-wall>100: raise TimeoutError('campaign soft wall deadline exceeded')
        tr=case['trace']; cert=produce(tr)
        if not verify(tr,cert): raise AssertionError(f"certificate rejected: {case['id']}")
        cert_checks+=1
        if 'expected' in case and cert['kind']!=case['expected']: raise AssertionError(f"expected verdict mismatch: {case['id']}")
        rec={'id':case['id'],'family':case['family'],'verdict':cert['kind'],'certificate':cert,'observation_count':len(tr['observations'])}
        if case['exact_oracle']:
            if case['id'] in pilot_cache:
                cached=pilot_cache[case['id']]
                if cached['trace']!=tr or cached['certificate']!=cert: raise AssertionError('pilot input mismatch')
                oracle=cached['oracle'];reused_assignments+=oracle['assignment_count']
            else:
                oracle=exact_distributions(tr);direct_assignments+=oracle['assignment_count']
            if oracle['verdict']!=cert['kind']: raise AssertionError(f"oracle disagreement: {case['id']}")
            rec['oracle']=oracle
        if case['family'] in {'field-5-saturated','saturated-pilot'}:
            if saturated_verdict(tr)!=cert['kind']: raise AssertionError('saturated theorem disagreement')
            structural_checks+=1
        if all(ob['kind']=='snapshot' for ob in tr['observations']):
            if snapshot_verdict(tr)!=cert['kind']: raise AssertionError('snapshot theorem disagreement')
            structural_checks+=1
        anchored,closure=anchored_closure(tr)
        rec['all_delta_components_anchored']=anchored
        rec['closure_sizes']=[len(s) for s in closure]
        if anchored:
            expected='revealing' if any(len(s)>=tr['threshold'] for s in closure) else 'hiding'
            if expected!=cert['kind']: raise AssertionError('anchored closure disagreement')
            structural_checks+=1
        # Deterministic malformed/mathematically false certificate controls.
        bad=copy.deepcopy(cert)
        if cert['kind']=='hiding': bad['polynomials'][0][0]=0
        else: bad['weights']=[0]*len(tr['observations'])
        if verify(tr,bad): raise AssertionError('negative certificate accepted')
        mutations+=1
        # Reordering and exact duplication preserve an observation span.
        if index%17==0:
            transformed=copy.deepcopy(tr);transformed['observations']=list(reversed(tr['observations']))
            if transformed['observations'] and len(transformed['observations'])<64:
                transformed['observations'].append(copy.deepcopy(transformed['observations'][0]))
            tc=produce(transformed)
            if tc['kind']!=cert['kind'] or not verify(transformed,tc): raise AssertionError('metamorphic span check failed')
            cert_checks+=1;transforms+=1
        family_counts[case['family']]+=1;verdicts[cert['kind']]+=1;records.append(rec)
    adaptive=exact_policy();direct_assignments+=adaptive['assignment_count']
    suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_*.py')
    stream=io.StringIO(); test_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (output/'unit-tests.txt').write_text(stream.getvalue())
    if not test_result.wasSuccessful(): raise AssertionError('unit test failure')
    # Counts-only baseline: snapshot counts per epoch, deliberately ignores deltas.
    baseline_failures=[]
    for c,r in zip(corpus,records):
        tr=c['trace']; snapshot_counts=[len({ob['x'] for ob in tr['observations'] if ob['kind']=='snapshot' and ob['epoch']==e}) for e in range(tr['epochs'])]
        guess='hiding' if all(n<tr['threshold'] for n in snapshot_counts) else 'revealing'
        if guess!=r['verdict']: baseline_failures.append(c['id'])
    deterministic={'trace_count':len(corpus),'families':dict(sorted(family_counts.items())),
                   'verdict_counts':dict(sorted(verdicts.items())), 'exact_trace_count':sum(c['exact_oracle'] for c in corpus),
                   'fixed_trace_assignment_count':sum(r.get('oracle',{}).get('assignment_count',0) for r in records),
                   'adaptive_assignment_count':adaptive['assignment_count'],
                   'certificate_checks':cert_checks, 'rejected_certificate_mutations':mutations,
                   'structural_checks':structural_checks,'metamorphic_checks':transforms,
                   'unit_test_count':test_result.testsRun, 'baseline_false_hiding_count':len(baseline_failures),
                   'baseline_false_hiding_cases':baseline_failures}
    measurement={'workers':1,'child_processes':0,'direct_assignment_evaluations_this_run':direct_assignments,
                 'reused_pilot_assignments':reused_assignments,'wall_seconds':time.perf_counter()-wall,
                 'cpu_seconds':time.process_time()-cpu,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 'maximum_case_matrix_shape':[64,133], 'largest_exact_assignment_space':16807,
                 'maximum_field_bit_width':5,'hard_cpu_limit_seconds':110,'hard_address_space_limit_bytes':2*1024**3}
    atomic_json(output/'certificates.json',records)
    atomic_json(output/'adaptive.json',adaptive)
    atomic_json(output/'summary.json',deterministic)
    atomic_json(output/'measurement.json',measurement)
    with (output/'case-results.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['case','family','verdict','observations','all_delta_components_anchored','closure_sizes','exact_assignments'])
        for r in records:w.writerow([r['id'],r['family'],r['verdict'],r['observation_count'],r['all_delta_components_anchored'],';'.join(map(str,r['closure_sizes'])),r.get('oracle',{}).get('assignment_count',0)])
    return {'summary':deterministic,'measurement':measurement}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--reuse-pilot',type=Path,help='development only: reuse an exact, matching measured pilot')
    args=p.parse_args()
    try:
        report=run(args.output,args.reuse_pilot)
        # Keep the console output bounded; complete findings are in explicit result files.
        print(json.dumps({'trace_count':report['summary']['trace_count'],'verdict_counts':report['summary']['verdict_counts'],
                          'measurement':report['measurement']},indent=2))
    except (OSError,ValueError,AssertionError,TimeoutError) as e:
        print(f'FAILED: {e}',file=sys.stderr);raise SystemExit(1)
