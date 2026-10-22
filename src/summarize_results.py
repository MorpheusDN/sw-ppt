"""Score saved predictions only after inference, audit candidates and repetitions."""
from pathlib import Path
import argparse, collections, json, statistics
from experiment import score, rows, write_json

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results/real'
METHODS=['full_text','vector','dynamic_vector']

def main():
    reports={}
    for partition,seeds in [('dev',[17]),('test',[17,23,41])]:
        expected=len(rows(ROOT/f'data/eval/questions.{partition}.jsonl'))
        for seed in seeds:
            for method in METHODS:
                path=RESULTS/f'{method}-{partition}-seed{seed}.jsonl'
                if not path.exists() or len(rows(path))!=expected:
                    raise RuntimeError(f'Incomplete predictions: {path}')
                target=path.with_suffix('.metrics.json')
                score(argparse.Namespace(predictions=path,gold=ROOT/f'data/eval/gold.{partition}.jsonl',out=target))
                reports[(partition,seed,method)]=json.loads(target.read_text(encoding='utf-8'))
            vector=rows(RESULTS/f'vector-{partition}-seed{seed}.jsonl')
            dynamic=rows(RESULTS/f'dynamic_vector-{partition}-seed{seed}.jsonl')
            assert all(a['question_id']==b['question_id'] and a['candidate_memory_ids']==b['candidate_memory_ids'] for a,b in zip(vector,dynamic)), 'Candidate mismatch invalidates ablation'
    summary={'kind':'project-defined-real-locomo; not official course split',
             'data':json.loads((ROOT/'data/eval/data-counts.json').read_text(encoding='utf-8')),
             'dev':[], 'test':[], 'candidate_identity_verified':True,
             'repetitions':'three fresh CPU inference runs; ONNX deterministic, seeds logged but no sampling is used',
             'limitations':['only 30 development and 16 holdout QA questions were evaluated',
                            'project-defined split, source examples inspected, not a blind course test',
                            'single-span SQuAD answerer cannot synthesize multi-hop or list answers',
                            'self-built dynamic annotations have no independent human review']}
    keys=['qa_f1','candidate_recall_at_k','effective_recall','mean_seconds']
    for method in METHODS:
        dev=reports[('dev',17,method)]
        summary['dev'].append({'method':method,'n_questions':dev['n_questions'],**{k:dev[k] for k in keys}})
        test=[reports[('test',seed,method)] for seed in [17,23,41]]
        row={'method':method,'n_questions':test[0]['n_questions'],'runs':3}
        for key in keys:
            values=[r[key] for r in test if r[key] is not None]
            row[key]=statistics.mean(values) if values else None
            row[key+'_sd']=statistics.stdev(values) if len(values)>1 else (0.0 if values else None)
        predictions=[rows(RESULTS/f'{method}-test-seed{seed}.jsonl') for seed in [17,23,41]]
        row['answers_identical_across_runs']=all([q['answer'] for q in pred]==[q['answer'] for q in predictions[0]] for pred in predictions[1:])
        row['abstentions']=sum(q['model_detail'].get('windows',0)==0 for q in predictions[0])
        row['total_fulltext_windows_per_run']=sum(q['model_detail'].get('windows',0) for q in predictions[0])
        summary['test'].append(row)
    diagnostic=RESULTS/'dynamic-diagnostic-metrics.json'
    if diagnostic.exists():
        d=json.loads(diagnostic.read_text(encoding='utf-8'))
        summary['self_built_dynamic']={k:v for k,v in d.items() if k!='detail'}
    write_json(RESULTS/'summary.json',summary)
    # Select actual error/success records mechanically, without changing any method after scoring.
    qa=rows(ROOT/'data/eval/questions.test.jsonl');gold={g['question_id']:g for g in rows(ROOT/'data/eval/gold.test.jsonl')}
    vr={r['question_id']:r for r in rows(RESULTS/'vector-test-seed17.jsonl')}
    dr={r['question_id']:r for r in rows(RESULTS/'dynamic_vector-test-seed17.jsonl')}
    detail={d['question_id']:d for d in reports[('test',17,'vector')]['detail']}
    selected=[]
    groups=[('best_vector_answer', sorted(qa,key=lambda q:(-detail[q['question_id']]['qa_f1'],q['question_id']))),
            ('retrieval_miss', [q for q in qa if detail[q['question_id']]['candidate_recall_at_k']==0]),
            ('dynamic_abstention', [q for q in qa if dr[q['question_id']]['model_detail'].get('windows',0)==0])]
    for reason, candidates in groups:
        candidates=[q for q in candidates if q['question_id'] not in {c['question_id'] for c in selected}]
        if candidates:
            q=candidates[0];qid=q['question_id']
            selected.append({'case_type':reason,**q,'gold':gold[qid], 'vector':vr[qid], 'dynamic':dr[qid], 'vector_metrics':detail[qid]})
    write_json(RESULTS/'error-cases.json',selected)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
