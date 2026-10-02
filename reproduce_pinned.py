#!/usr/bin/env python3
"""One-worker exact validation of pinned refresh, public budgets, and message simulation."""
from __future__ import annotations
import argparse,collections,copy,csv,json,resource,sys,time
from pathlib import Path
from src.pinned import exact_pinned,exact_local_simulation,local_union_sizes,to_trace
from src.pinned_producer import produce_pinned
from src.pinned_checker import verify_pinned
from src.budget_validation import check_budget_corpus
from src.budgets import capacities
from src.exhaustive_validation import run_exhaustive_validation


def write_json(path: Path, obj: object) -> None:
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n');tmp.replace(path)


def run(output: Path) -> dict:
    resource.setrlimit(resource.RLIMIT_CPU,(110,115));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    root=Path(__file__).resolve().parent;wall=time.perf_counter();cpu=time.process_time()
    corpus=json.loads((root/'cases/pinned.json').read_text());budget_corpus=json.loads((root/'cases/budgets.json').read_text())
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError('use an empty output directory')
    records=[];counts=collections.Counter();assignments=0;mutations=0;maxrows=0
    for case in corpus:
        if time.perf_counter()-wall>100:raise TimeoutError('soft campaign deadline exceeded')
        tr=case['case'];cert=produce_pinned(tr)
        if cert['kind']!=case['expected'] or not verify_pinned(tr,cert):raise AssertionError('pinned certificate mismatch: '+case['id'])
        rows=len(to_trace(tr)['observations']);maxrows=max(maxrows,rows)
        rec={'id':case['id'],'family':case['family'],'verdict':cert['kind'],'certificate':cert,
             'equation_and_observation_rows':rows,'local_union_sizes':local_union_sizes(tr)}
        if case['exact_oracle']:
            oracle=exact_pinned(tr);assignments+=oracle['assignment_count']
            if oracle['verdict']!=cert['kind']:raise AssertionError('exact distribution disagreement')
            rec['oracle']=oracle
        bad=copy.deepcopy(cert)
        if cert['kind']=='hiding':bad['polynomials'][0][0]=0
        else:bad['weights']=[0]*len(cert['weights'])
        if verify_pinned(tr,bad):raise AssertionError('false pinned certificate accepted')
        mutations+=1;records.append(rec);counts[cert['kind']]+=1
    simulation=exact_local_simulation();assignments+=simulation['real_assignment_count']+simulation['ideal_assignment_count']
    budgets=check_budget_corpus(budget_corpus)
    exhaustive=run_exhaustive_validation()
    # All formula rows are theorem values, not measured performance observations.
    formula=[]
    for t in range(1,13):
        b,u=2,3;gamma=capacities([b]*t,[u]*(t-1))['capacity']
        closed=min(t*b,((t+1)//2)*b+u,b+2*u)
        if gamma!=closed:raise AssertionError('finite-horizon formula mismatch')
        formula.append({'slots':t,'moving_pins':gamma,'fixed_pins':min(t*b,b+u),'long_horizon_bound':b+2*u})
    summary={'pinned_trace_count':len(records),'pinned_verdict_counts':dict(counts),
             'pinned_exact_trace_count':sum(r['exact_oracle'] for r in corpus),
             'exact_pinned_assignments':assignments-250,'real_and_ideal_message_assignments':250,
             'pinned_certificate_checks':len(records),'rejected_pinned_mutations':mutations,
             'budget_validation':budgets['counts'],'independent_exhaustive_validation':{
                 'capacity_partition_vectors':exhaustive['capacity_partition_vectors'],
                 'concrete_set_systems':exhaustive['concrete_set_systems'],
                 'revealing_set_systems':exhaustive['revealing_set_systems'],
                 'dominating_budget_vectors':exhaustive['dominating_budget_vectors'],
                 'scheduler_instances':exhaustive['scheduler_instances'],
                 'mandatory_and_count_scheduler_instances':exhaustive['mandatory_and_count_scheduler_instances'],
                 'constant_closed_form_checks':exhaustive['constant_closed_form_checks'],
                 'fixed_pin_formula_consistency_checks':exhaustive['fixed_pin_formula_consistency_checks'],
                 'fixed_pin_rank_concrete_systems':exhaustive['fixed_pin_rank_concrete_systems'],
                 'fixed_pin_rank_revealing_systems':exhaustive['fixed_pin_rank_revealing_systems'],
                 'fixed_pin_rank_budget_vectors':exhaustive['fixed_pin_rank_budget_vectors'],
                 'horizon_inversion_checks':exhaustive['horizon_inversion_checks'],
                 'horizon_checked_domain':exhaustive['horizon_checked_domain'],
                 'threshold_envelope_regressions':len(exhaustive['threshold_envelope_regressions']),
                 'single_trace_budget_separation':exhaustive['single_trace_budget_separation'],
                 'universal_frontier_families':exhaustive['universal_frontier_families']},
             'formula_rows':len(formula)}
    measurement={'workers':1,'child_processes':0,'direct_assignment_evaluations_this_run':assignments,
                 'wall_seconds':time.perf_counter()-wall,'cpu_seconds':time.process_time()-cpu,
                 'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 'maximum_case_matrix_shape':[maxrows,133],'largest_pinned_exact_assignment_space':3125,
                 'hard_cpu_limit_seconds':110,'hard_address_space_limit_bytes':2*1024**3}
    for name,value in [('certificates',records),('simulation',simulation),('budgets',budgets),('exhaustive',exhaustive),('summary',summary),('measurement',measurement)]:
        write_json(output/(name+'.json'),value)
    with (output/'cadence.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['slots','moving_pins','fixed_pins','long_horizon_bound']);w.writeheader();w.writerows(formula)
    with (output/'case-results.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['case','family','verdict','constraint_and_observation_rows','exact_assignments'])
        for r in records:w.writerow([r['id'],r['family'],r['verdict'],r['equation_and_observation_rows'],r.get('oracle',{}).get('assignment_count',0)])
    return {'summary':summary,'measurement':measurement}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    try:print(json.dumps(run(a.output),indent=2))
    except (ValueError,OSError,AssertionError,TimeoutError) as e:print('FAILED: '+str(e),file=sys.stderr);raise SystemExit(1)
