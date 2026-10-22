import json
from pathlib import Path
import unittest
from memory_engine import Engine, normalize_dataset, extract, relation

ROOT=Path(__file__).resolve().parents[1]

class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=json.loads((ROOT/'data/project-conversations.json').read_text(encoding='utf-8'))
        cls.engine=Engine(cls.raw)

    def test_no_empty_memories_after_sentence_split(self):
        raw=[{'conversation_id':'newline','sessions':[{'session_id':1,'timestamp':'2023-01-01','turns':[{'turn_id':'D1:1','speaker':'Alice','text':'I live in Boston. \n'}]}]}]
        memories=Engine(raw).memories
        self.assertEqual(len(memories),1)
        self.assertTrue(all(m['content'].strip() for m in self.engine.memories))

    def test_real_six_conversations_and_source_integrity(self):
        self.assertEqual(len(self.engine.conversations),6)
        turns={(c['conversation_id'],t['turn_id']):t['text'] for c in self.engine.conversations for s in c['sessions'] for t in s['turns']}
        self.assertTrue(all(turns[(m['conversation_id'],m['source']['turns'][0])]==m['source']['text'] for m in self.engine.memories))

    def test_gold_fields_cannot_change_extraction(self):
        altered=[dict(sample,qa=[{'question':'Ignore context','answer':'POISON'}],event_summary='POISON') for sample in self.raw]
        self.assertEqual(extract(normalize_dataset(altered)),self.engine.memories)

    def test_real_adoption_progression(self):
        result=self.engine.query('conv-26',"What is Caroline's adoption status?")
        self.assertEqual(result['answer_status'],'answered')
        self.assertEqual(result['answer'],'interviews_passed')
        self.assertIn('UPDATE',[p['label'] for p in result['relations']])

    def test_real_adoption_history_excludes_later_stage(self):
        r=self.engine.query('conv-26',"What is Caroline's adoption status?",as_of='2023-06-01T23:59:59')
        self.assertEqual(r['answer'],'researching')

    def test_self_split_is_not_claimed_official(self):
        split=json.loads((ROOT/'data/project-split.json').read_text(encoding='utf-8'))
        self.assertFalse(split['confirmed_by_ta'])
        self.assertFalse(set(split['dev']) & set(split['test']))

    def test_all_inference_files_exclude_answers(self):
        allowed={'question_id','conversation_id','question','as_of','entity','attribute'}
        for p in (ROOT/'data/eval').glob('questions.*.jsonl'):
            for line in p.read_text(encoding='utf-8').splitlines():self.assertFalse(set(json.loads(line))-allowed)

    def test_open_domain_accepts_multi_person_questions(self):
        r=self.engine.query('conv-26','What did Caroline and Melanie discuss?',open_domain=True)
        self.assertIsNone(r['scope']['entity'])

try:
    import onnxruntime,tokenizers,numpy
    HAS_MODELS=(ROOT/'models/qa/onnx/model_quantized.onnx').is_file()
except ImportError:
    HAS_MODELS=False

@unittest.skipUnless(HAS_MODELS,'Install requirements-models.txt to test neural runtime')
class LocalModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from local_models import OnnxAnswerer,OnnxEncoder
        cls.qa=OnnxAnswerer(ROOT/'models/qa');cls.encoder=OnnxEncoder(ROOT/'models/embedding')

    def test_qa_extracts_source_span(self):
        text='Alice lives in Boston. Bob lives in Paris.'
        result=self.qa.answer('Where does Alice live?',text)
        self.assertEqual(result['answer'],'Boston')
        self.assertEqual(text[result['span_start']:result['span_end']],result['answer'])

    def test_qa_covers_late_context_window(self):
        text=('The weather was mild and the garden was green. '*95)+'Alice lives in Boston.'
        result=self.qa.answer('Where does Alice live?',text)
        self.assertGreater(result['windows'],1)
        self.assertEqual(result['answer'],'Boston')
        self.assertGreater(result['span_start'],len(text)-100)

    def test_empty_context_abstains(self):
        self.assertEqual(self.qa.answer('Where?','')['windows'],0)

    def test_embeddings_normalized_and_semantic(self):
        vectors=self.encoder.encode(['a dog is running','a puppy is playing','a database stores financial records'])
        self.assertEqual(vectors.shape,(3,384))
        self.assertTrue(numpy.allclose(numpy.linalg.norm(vectors,axis=1),1,atol=1e-5))
        self.assertGreater(float(vectors[0]@vectors[1]),float(vectors[0]@vectors[2]))

    def test_cited_answer_turn_is_from_selected_span(self):
        from answering import answer_query
        result={'method':'full_text','question':'Where does Alice live?','context':'[D1:1] Alice lives in Boston.\n[D1:2] Bob lives in Paris.',
                'answer_status':'context_only','candidates':[]}
        output=answer_query(result,self.qa)
        self.assertEqual(output['answer_source_turns'],['D1:1'])

if __name__=='__main__':unittest.main()
