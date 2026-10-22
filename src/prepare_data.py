"""Project-defined split; questions and gold files are physically separated."""
from pathlib import Path
import hashlib, json
from memory_engine import Engine, export_bundle

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'

def write(name, value):
    p = DATA / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def jsonl(name, rows):
    p = DATA / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows)+'\n', encoding='utf-8')

def main():
    raw = json.loads((DATA/'locomo/locomo10.json').read_text(encoding='utf-8'))
    selected = raw[:6]
    dev = [s['sample_id'] for s in selected[:4]]
    test = [s['sample_id'] for s in selected[4:]]
    manifest = {'kind':'project-defined-holdout', 'confirmed_by_ta':False, 'selection_authority':'team',
                'selection_permission_confirmed_by_user':True, 'course_assignment_required':False,
                'clarification_date':'2026-10-20',
                'dev':dev, 'test':test, 'remaining':[s['sample_id'] for s in raw[6:]],
                'selection_rule':'first six in pinned upstream order; first four dev, next two holdout',
                'limitation':'Some source turns were inspected while preparing examples. This is not a blind course test.',
                'upstream_sha256':hashlib.sha256((DATA/'locomo/locomo10.json').read_bytes()).hexdigest()}
    write('project-split.json', manifest)
    # Do not bundle QA/summary fields into inference data.
    permitted = [{'sample_id':s['sample_id'],'conversation':s['conversation']} for s in selected]
    write('project-conversations.json', permitted)
    counts = {}
    for partition, ids in [('dev',dev),('test',test)]:
        questions, gold = [], []
        for sample in selected:
            cid = sample['sample_id']
            if cid not in ids: continue
            for i, qa in enumerate(sample['qa']):
                # Category 5 adversarial questions lack ordinary gold answers; separate protocol required.
                if qa['category'] == 5 or 'answer' not in qa: continue
                qid = f'{cid}-qa-{i:03d}'
                questions.append({'question_id':qid,'conversation_id':cid,'question':qa['question']})
                gold.append({'question_id':qid,'answers':[str(qa['answer'])],
                             'evidence':qa.get('evidence',[]),'category':qa['category'],'relations':[]})
        jsonl(f'eval/questions.all-{partition}.jsonl',questions)
        jsonl(f'eval/gold.all-{partition}.jsonl',gold)
        gold_by_id = {g['question_id']:g for g in gold}
        chosen = []
        # Predeclared computational budget, independent of answers or model predictions.
        for cid in ids:
            for category in (1,2,3,4):
                pool = [q for q in questions if q['conversation_id']==cid and gold_by_id[q['question_id']]['category']==category]
                pool.sort(key=lambda q:hashlib.sha256(q['question'].encode()).hexdigest())
                chosen.extend(pool[:2])
        jsonl(f'eval/questions.{partition}.jsonl',chosen)
        jsonl(f'eval/gold.{partition}.jsonl',[gold_by_id[q['question_id']] for q in chosen])
        counts[partition] = {'evaluated':len(chosen),'all_eligible':len(questions)}
    engine = Engine(permitted)
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results/memory.locomo-six.json').write_text(json.dumps(export_bundle(engine),ensure_ascii=False,indent=2),encoding='utf-8')
    write('eval/data-counts.json',{'questions':counts,'conversations':len(selected),'memories':len(engine.memories),
                               'qa_policy':'two questions per category 1-4 per conversation, ordered by SHA-256(question); all eligible questions retained in all-* files; no performance-based sampling',
                               'adversarial_excluded':sum(q['category']==5 for s in selected for q in s['qa'])})
    print(json.dumps({'split':manifest,'questions':counts,'memories':len(engine.memories)},ensure_ascii=False))

if __name__ == '__main__':main()
