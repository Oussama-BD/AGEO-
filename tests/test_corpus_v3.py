import json,unittest
from pathlib import Path
from unittest.mock import patch
from app import rag_v3,corpus_v3
from benchmark_v3 import evaluate,fingerprint
R=Path(__file__).resolve().parents[1]
class CorpusTests(unittest.TestCase):
 def test_namespace_and_evidence(self):
  rows=[json.loads(p.read_text(encoding='utf-8')) for p in (R/'data/experiments/v3/records').glob('*.json')]
  self.assertEqual(len(rows),28)
  for rec in rows:
   ids={e['id'] for e in rec['graph']['entities']}
   self.assertTrue(all(i.startswith('v3:') for i in ids))
   for rel in rec['graph']['relations']:
    self.assertIn(rel['source'],ids);self.assertIn(rel['target'],ids);self.assertTrue(rel['quote'])
 def test_legacy_scope_isolated(self):
  for pattern,_ in corpus_v3.MODES.values():self.assertNotIn(':Entity',pattern);self.assertIn(':ResearchV3',pattern)
 def test_three_hop_retrieval_and_cap(self):
  rows=[{'subject_id':str(i),'object_id':str(i+1)} for i in range(5)]
  got,meta=rag_v3.retrieve({'first':'0','second':''},rows)
  self.assertEqual(len(got),3);self.assertFalse(meta['truncated'])
  got,meta=rag_v3.retrieve({'first':'0','second':''},rows,max_facts=2)
  self.assertEqual(len(got),2);self.assertTrue(meta['truncated'])
 def test_model_without_verified_free_tier_is_blocked(self):
  import os
  from app import llm
  with patch.dict(os.environ,{'GEMINI_MODEL':'unverified-paid-model'}):
   with self.assertRaises(ValueError):llm.model()
 def test_reference_fingerprint_changes(self):
  self.assertNotEqual(fingerprint({},{'v':1}),fingerprint({}, {'v':2}))
 def test_empty_score_explicit(self):self.assertEqual(evaluate([],[])['f1'],1)
 def test_plan_rejects_unknown_entity(self):
  with patch('app.rag_v3.llm.generate',return_value=(json.dumps({'mode':'topic_papers','first':'invented','second':''}),{})):
   with self.assertRaises(ValueError):rag_v3.plan('question',[{'id':'known','name':'topic','type':'Topic'}])
 def test_pending_review_gate_before_database(self):
  import benchmark_v3
  with patch('app.corpus_v3.graph') as graph, patch('app.llm.model',return_value='gemini-3.1-flash-lite'):
   with self.assertRaises(ValueError):benchmark_v3.run(allow_provisional=False)
   graph.assert_not_called()
class ApiV3Tests(unittest.TestCase):
 def test_v3_graph_requires_auth(self):
  from fastapi.testclient import TestClient
  from app.api import app
  with TestClient(app) as c:self.assertEqual(c.get('/v3/graph').status_code,401)
 def test_prepared_graph_never_queries_neo4j(self):
  from app.api import v3_prepared_graph
  with patch('app.store.query') as query:
   graph=v3_prepared_graph();query.assert_not_called()
  self.assertEqual(len(graph['entities']),289)
  self.assertEqual(graph['execution'],'prepared_local_files')
 def test_benchmark_budget_preserves_planned_stage(self):
  import tempfile,benchmark_v3
  (R/".test-tmp").mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=R/".test-tmp") as tmp:
   root=Path(tmp);(root/'data/references-v3').mkdir(parents=True);(root/'reports').mkdir()
   refs={'review_status':'pending_independent_human_review','questions':[{'id':'one','question':'Q','mode':'topic_papers','first':'id','second':'','expected':[]}]}
   (root/'data/references-v3/questions.proposed.json').write_text(json.dumps(refs),encoding='utf-8')
   with patch.object(benchmark_v3,'ROOT',root),patch('app.llm.model',return_value='gemini-3.1-flash-lite'),patch('app.corpus_v3.graph',return_value={'entities':[]}),patch('app.corpus_v3.facts',return_value=[]),patch('app.corpus_v3.analytics',return_value=[]),patch('app.rag_v3.answer') as answer:
    state=benchmark_v3.run(max_calls=0,allow_provisional=True)
   answer.assert_not_called();self.assertEqual(state['status'],'call_budget_reached')
   self.assertIn('cypher',state['rows']['1:one:controlled'])
   self.assertTrue((root/'reports/benchmark-v3-latest.json').exists())

if __name__=='__main__':unittest.main()
