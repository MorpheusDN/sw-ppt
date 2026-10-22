"""Shared answer policy for the API and experiment runner."""
import re

def answer_query(result, answerer):
    if result['method'].startswith('dynamic') and result['answer_status'] in ('uncertain','insufficient_evidence'):
        result['model_detail'] = {'windows':0,'policy':'resolver abstention'}
        return result
    response = answerer.answer(result['question'],result['context'])
    result['answer'] = response['answer']
    result['answer_mode'] = answerer.model_id
    result['answer_status'] = 'answered' if response.get('windows') else 'insufficient_evidence'
    result['model_detail'] = response
    if 'span_start' in response:
        a, b = response['span_start'], response['span_end']
        context = result['context']
        start = context.rfind('\n',0,a)+1
        end = context.find('\n',b)
        lines = context[start:end if end!=-1 else None]
        result['answer_source_turns'] = list(dict.fromkeys(re.findall(r'\bD\d+:\d+\b',lines)))
        cited = set(result['answer_source_turns'])
        result['evidence_ids'] = [m['memory_id'] for m in result['candidates'] if cited.intersection(m['source']['turns'])]
    return result
