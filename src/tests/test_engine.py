import copy
import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory_engine import Engine, extract, normalize_dataset, parse_time, event_time, export_bundle, relation
from metrics import f1, recall, relation_accuracy, source_turns
from experiment import check_split
from server import create_server

ROOT = Path(__file__).resolve().parents[1]
RAW = json.loads((ROOT/'data/synthetic.json').read_text(encoding='utf-8'))


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.e = Engine(copy.deepcopy(RAW))

    def query(self, q, **kwargs):
        return self.e.query('synthetic-adoption', q, **kwargs)

    def test_current_stage(self):
        r = self.query("What is Alice's adoption status?")
        self.assertEqual(r['answer'], 'interviews_passed')
        self.assertEqual(len(r['effective_ids']), 1)
        self.assertIn('UPDATE', [p['label'] for p in r['relations']])

    def test_historical_stage(self):
        self.assertEqual(self.query("Alice adoption status", as_of='2023-06-01T23:59:59')['answer'], 'researching')

    def test_current_scalar_replacement(self):
        self.assertEqual(self.query('Where does Alice live?')['answer'], 'Seattle')

    def test_historical_scalar(self):
        self.assertEqual(self.query('Where does Alice live?', as_of='2023-06-01')['answer'], 'Boston')

    def test_different_entity(self):
        r = self.query('Where does Bob live?')
        self.assertEqual(r['answer'], 'London')
        self.assertTrue(all(m['entity'] == 'Bob' for m in r['candidates']))

    def test_set_valued_attribute(self):
        r = self.query('What hobbies does Alice enjoy?')
        self.assertEqual(set(r['answer'].split('; ')), {'swimming', 'pottery'})
        self.assertEqual(r['relations'][0]['label'], 'RETAIN')

    def test_no_evidence(self):
        self.assertEqual(self.query("What is Alice's salary?")['answer_status'], 'insufficient_evidence')

    def test_conflict(self):
        r = self.e.query('synthetic-conflict', 'Does Dana work at DoorDash?')
        self.assertEqual(r['answer_status'], 'uncertain')
        self.assertEqual(r['relations'][0]['label'], 'CONFLICT')

    def test_unknown_time(self):
        r = self.e.query('synthetic-conflict', 'Where does Dana live?')
        self.assertEqual(r['answer_status'], 'uncertain')

    def test_no_persistent_invalidations(self):
        before = json.dumps(self.e.memories, sort_keys=True)
        self.query('Where does Alice live?')
        self.query('Where does Alice live?', as_of='2023-06-01')
        self.assertEqual(before, json.dumps(self.e.memories, sort_keys=True))

    def test_default_time_is_corpus_end(self):
        r = self.query('Where does Alice live?')
        self.assertEqual(r['as_of'], '2023-10-22T09:55:00')

    def test_iso_question_time(self):
        self.assertEqual(self.query('Where did Alice live on 2023-06-01?')['answer'], 'Boston')

    def test_ambiguous_historical_query_requires_input(self):
        with self.assertRaisesRegex(ValueError, 'as_of'):
            self.query('Where did Alice live last year?')

    def test_empty_question(self):
        with self.assertRaises(ValueError):
            self.query(' ')

    def test_k_bounds(self):
        for k in (0, 101, '10', True):
            with self.assertRaises(ValueError):
                self.query('Where does Alice live?', k=k)

    def test_missing_conversation(self):
        with self.assertRaises(ValueError):
            self.e.query('missing', 'question')

    def test_multiple_entity_question(self):
        with self.assertRaises(ValueError):
            self.query('Where do Alice and Bob live?')

    def test_vector_never_masquerades_as_lexical(self):
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.query('Where does Alice live?', method='vector')

    def test_fulltext_keeps_every_turn(self):
        r = self.query('Where does Alice live?', method='full_text', k=1)
        self.assertEqual(r['answer_status'], 'context_only')
        for s in self.e.conversations[0]['sessions']:
            for t in s['turns']:
                self.assertIn(t['text'], r['context'])

    def test_source_integrity(self):
        for m in self.e.memories:
            c = next(c for c in self.e.conversations if c['conversation_id'] == m['conversation_id'])
            t = next(t for s in c['sessions'] for t in s['turns'] if t['turn_id'] == m['source']['turns'][0])
            self.assertIn(m['content'], t['text'])
            self.assertEqual(m['source']['text'], t['text'])

    def test_stable_unique_ids(self):
        ids = [m['memory_id'] for m in self.e.memories]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [m['memory_id'] for m in Engine(copy.deepcopy(RAW)).memories])

    def test_json_export_roundtrip(self):
        self.assertEqual(json.loads(json.dumps(export_bundle(self.e)))['memories'], self.e.memories)

    def test_locomo_adapter_ignores_gold(self):
        sample = [{'sample_id': 'unit-conv', 'conversation': {'speaker_a': 'Alice', 'speaker_b': 'Bob',
            'session_1_date_time': '9:55 am on 22 October, 2023',
            'session_1': [{'dia_id': 'D1:1', 'speaker': 'Alice', 'text': 'I live in Boston.'}]},
            'qa': [{'question': 'x', 'answer': 'LEAKED ANSWER'}], 'event_summary': 'LEAKED SUMMARY'}]
        e = Engine(sample)
        self.assertEqual(e.memories[0]['value'], 'Boston')
        self.assertNotIn('LEAKED', json.dumps(e.conversations)+json.dumps(e.memories))

    def test_duplicate_turn_rejected(self):
        raw = copy.deepcopy(RAW)
        raw['conversations'][0]['sessions'][0]['turns'].append(raw['conversations'][0]['sessions'][0]['turns'][0])
        with self.assertRaises(ValueError):
            Engine(raw)

    def test_bad_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            parse_time('not-a-time')

    def test_relative_weekday_anchored_to_session(self):
        self.assertEqual(event_time('I passed last Friday.', '2023-10-22T09:55:00')[0], '2023-10-20T00:00:00')

    def test_unsupported_relative_time_is_unknown(self):
        self.assertEqual(event_time('I moved last month.', '2023-10-22T09:55:00')[2], 'unknown')

    def test_plan_not_present_fact(self):
        raw = copy.deepcopy(RAW)
        raw['conversations'][0]['sessions'][0]['turns'][0]['text'] = 'I plan to adopt a child.'
        r = Engine(raw).query('synthetic-adoption', 'What does Alice plan?', attribute='observation')
        self.assertEqual(r['answer_status'], 'uncertain')

    def test_distinct_attributes_never_supersede(self):
        a = next(m for m in self.e.memories if m['attribute'] == 'residence')
        b = next(m for m in self.e.memories if m['attribute'] == 'hobby')
        self.assertEqual(relation(a,b)[0], 'RETAIN')

    def test_gold_future_answers_do_not_affect_memory(self):
        raw = copy.deepcopy(RAW)
        raw['conversations'][0]['qa'] = [{'answer':'secret'}]
        self.assertEqual(self.e.memories, Engine(raw).memories)


class MetricTests(unittest.TestCase):
    def test_token_f1(self):
        self.assertEqual(f1('The red red car', ['red car']), .8)

    def test_multi_answer_and_empty(self):
        self.assertEqual(f1('Boston', ['Seattle', 'Boston']), 1)
        self.assertEqual(f1('', ['']), 1)

    def test_evidence_split_and_dedup(self):
        self.assertEqual(source_turns(['D1:1; D2:2', 'D1:1']), {'D1:1','D2:2'})
        self.assertEqual(recall(['D1:1','D1:1'], ['D1:1; D2:2']), .5)

    def test_no_gold_evidence_is_na(self):
        self.assertIsNone(recall([], []))

    def test_missing_relation_counts_wrong(self):
        self.assertEqual(relation_accuracy({}, [{'from_turn':'D1:1','to_turn':'D2:1','label':'UPDATE'}]), 0)

    def test_split_guard(self):
        with self.assertRaises(ValueError):
            check_split({'dev':['x']*4,'test':['x']*2,'confirmed_by_ta':True}, [])
        ids=['a','b','c','d','e','f']
        data=[{'conversation_id':cid} for cid in ids]
        team={'dev':ids[:4],'test':ids[4:],'selection_authority':'team','selection_permission_confirmed_by_user':True}
        check_split(team,data)
        with self.assertRaises(ValueError):
            check_split(dict(team,selection_permission_confirmed_by_user=False),data)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(ROOT/'data/synthetic.json', port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def fetch(self, path, body=None, headers=None):
        req = Request(self.base+path, data=json.dumps(body).encode() if body is not None else None,
                      headers=headers or {'Content-Type':'application/json'})
        return urlopen(req, timeout=5)

    def test_health_and_static(self):
        with self.fetch('/api/health') as r:
            self.assertEqual(json.load(r)['status'], 'ok')
        with self.fetch('/') as r:
            self.assertIn('text/html', r.headers['Content-Type'])

    def test_api_current_and_history(self):
        for as_of, answer in [(None,'Seattle'), ('2023-06-01','Boston')]:
            body = {'conversation_id':'synthetic-adoption','question':'Where does Alice live?','as_of':as_of}
            with self.fetch('/api/query', body) as r:
                self.assertEqual(json.load(r)['answer'], answer)

    def test_invalid_import_preserves_state(self):
        invalid = [[], [None], [{'conversation_id':'x','sessions':[None]}],
                   [{'conversation_id':'x','sessions':[{'session_id':1,'turns':[None]}]}]]
        for bad in invalid:
            with self.subTest(payload=bad):
                with self.assertRaises(HTTPError) as e:
                    self.fetch('/api/import', {'data': bad})
                self.assertEqual(e.exception.code, 400)
        with self.fetch('/api/conversations') as r:
            self.assertEqual(len(json.load(r)['conversations']), 2)

    def test_path_whitelist(self):
        with self.assertRaises(HTTPError) as e:
            self.fetch('/../server.py')
        self.assertEqual(e.exception.code, 404)

    def test_foreign_origin(self):
        with self.assertRaises(HTTPError) as e:
            self.fetch('/api/query', {}, {'Origin':'https://example.org'})
        self.assertEqual(e.exception.code, 403)


if __name__ == '__main__':
    unittest.main(verbosity=2)
