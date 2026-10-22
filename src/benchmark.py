"""Real local-model comparison. predict command has no gold-file argument."""
from pathlib import Path
import argparse, datetime, hashlib, json, platform, random, time
from memory_engine import Engine, VERSION
from local_models import OnnxAnswerer

ROOT = Path(__file__).resolve().parent

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def rows(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def predict(args):
    random.seed(args.seed)
    import numpy as np
    np.random.seed(args.seed)
    engine = Engine(read(args.data), ROOT/'models/embedding')
    answerer = OnnxAnswerer(ROOT/'models/qa')
    requests = rows(args.questions)
    allowed = {'question_id','conversation_id','question','as_of','entity','attribute'}
    if any(set(q)-allowed for q in requests):raise ValueError('Inference file contains annotations or unsupported fields')
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'run_kind':'project-defined-real-locomo', 'engine_version':VERSION,
                'method':args.method,'k':args.k,'seed':args.seed,'inference':'CPUExecutionProvider',
                'python':platform.python_version(),'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'dataset_sha256':sha(args.data),'questions_sha256':sha(args.questions),
                'code_sha256':{p.name:sha(p) for p in [ROOT/'memory_engine.py',ROOT/'local_models.py',Path(__file__)]},
                'embedding':read(ROOT/'models/embedding/model-manifest.json'),
                'qa':read(ROOT/'models/qa/model-manifest.json'),
                'full_text_policy':'complete original history through all overlapping 384-token windows, stride=96',
                'shared_answerer':'same quantized DistilBERT span extractor, max span 30 tokens, no gold input',
                'official_course_split':False, 'question_count':len(requests)}
    out.with_suffix('.config.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    start_run = time.perf_counter()
    with out.open('w',encoding='utf-8') as stream:
        for index,q in enumerate(requests):
            started = time.perf_counter()
            params = {k:v for k,v in q.items() if k!='question_id'}
            # General QA needs no gold-derived entity/attribute constraint.
            params['open_domain'] = True
            result = engine.query(**params, k=args.k, method=args.method)
            if args.method.startswith('dynamic') and result['answer_status'] in ('uncertain','insufficient_evidence'):
                neural = {'answer':result['answer'],'windows':0,'policy':'dynamic resolver abstention'}
            else:
                neural = answerer.answer(q['question'],result['context'])
            by_id = {m['memory_id']:m for m in result['candidates']}
            pairs=[{'from_turn':by_id[p['from_id']]['source']['turns'][0],
                    'to_turn':by_id[p['to_id']]['source']['turns'][0],'label':p['label']} for p in result['relations']]
            record={'question_id':q['question_id'],'conversation_id':q['conversation_id'],'question':q['question'],
                    'method':args.method,'k':args.k,'as_of':result['as_of'],'answer':neural['answer'],
                    'answer_status':result['answer_status'],'answer_mode':answerer.model_id,'model_detail':neural,
                    'candidate_turns':sorted({t for m in result['candidates'] for t in m['source']['turns']}),
                    'candidate_memory_ids':[m['memory_id'] for m in result['candidates']],
                    'effective_turns':sorted({t for m in result['candidates'] if m['memory_id'] in result['effective_ids'] for t in m['source']['turns']}),
                    'effective_ids':result['effective_ids'],'predicted_pairs':pairs,'decisions':result['decisions'],
                    'context_sha256':hashlib.sha256(result['context'].encode()).hexdigest(),
                    'context_chars':len(result['context']),'elapsed_seconds':time.perf_counter()-started,
                    'run_kind':'project-defined-real-locomo'}
            stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush()
            if (index+1)%20==0 or index+1==len(requests):
                print(f'{args.method} seed={args.seed}: {index+1}/{len(requests)}, elapsed={time.perf_counter()-start_run:.1f}s',flush=True)
    print('saved',out,flush=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('predict');q.add_argument('--data',default=ROOT/'data/project-conversations.json');q.add_argument('--questions',required=True)
    q.add_argument('--method',choices=['full_text','vector','dynamic_vector'],required=True)
    q.add_argument('--k',type=int,default=10);q.add_argument('--seed',type=int,default=17);q.add_argument('--out',required=True);q.set_defaults(func=predict)
    args=p.parse_args();args.func(args)
