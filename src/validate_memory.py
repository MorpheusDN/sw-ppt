"""Validate exported memories against JSON Schema Draft 2020-12 and raw sources."""
from pathlib import Path
import json
from jsonschema import Draft202012Validator
from memory_engine import normalize_dataset
root=Path(__file__).resolve().parent
schema=json.loads((root/'schemas/memory-bundle.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(schema)
validator=Draft202012Validator(schema)
results=[]
for name,data in [('memory.synthetic.json','data/synthetic.json'),('memory.locomo-six.json','data/project-conversations.json')]:
    export=json.loads((root/'results'/name).read_text(encoding='utf-8'))
    validator.validate(export)
    conv=normalize_dataset(json.loads((root/data).read_text(encoding='utf-8')))
    turns={(c['conversation_id'],t['turn_id']):t['text'] for c in conv for s in c['sessions'] for t in s['turns']}
    assert len({m['memory_id'] for m in export['memories']})==len(export['memories'])
    assert all(turns[(m['conversation_id'],m['source']['turns'][0])]==m['source']['text'] for m in export['memories'])
    results.append({'file':name,'memories':len(export['memories']),'schema_valid':True,'unique_ids':True,'source_text_matches':True})
target=root.parent/'process/evidence/schema-check.json'
target.write_text(json.dumps({'validator':'jsonschema 4.26.0 / Draft 2020-12','result':'passed','files':results},indent=2),encoding='utf-8')
print(target.read_text(encoding='utf-8'))
