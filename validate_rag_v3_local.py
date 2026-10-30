"""Live Gemini smoke check over prepared graph files, NOT a Neo4j benchmark."""
import json,os
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).parent
load_dotenv(ROOT/'.env');os.environ['GEMINI_MODEL']='gemini-3.1-flash-lite';os.environ['KG_RUN_LABEL']='v3_prepared_graph_smoke'
from app import rag_v3
from benchmark_v3 import evaluate
nodes={};facts=[]
for path in sorted((ROOT/'data/experiments/v3/records').glob('*.json')):
 rec=json.loads(path.read_text(encoding='utf-8'));nodes.update({e['id']:e for e in rec['graph']['entities']})
 for r in rec['graph']['relations']:
  facts.append({'subject_id':r['source'],'subject':nodes[r['source']]['name'],'predicate':r['type'],'object_id':r['target'],'object':nodes[r['target']]['name'],'source_id':rec['document']['id'],'url':rec['document']['source'],'quote':r['quote'],'source_kind':r['source_kind']})
q=json.loads((ROOT/'data/references-v3/questions.proposed.json').read_text(encoding='utf-8'))['questions'][3]
try:
 plan,usage=rag_v3.plan(q['question'],list(nodes.values()))
 answer=rag_v3.answer(q['question'],plan,facts)
 result={'status':'complete','storage':'prepared_local_json','not_a_neo4j_or_spark_validation':True,'reference_review':'pending_independent_human_review','question':q['question'],'plan':plan,'planner_usage':usage,'graphrag':answer,'provisional_metrics':evaluate(q['expected'],answer['items'])}
except Exception as e:result={'status':'failed','error_type':type(e).__name__,'storage':'prepared_local_json'}
(ROOT/'reports/rag-v3-local-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('SMOKE_STATUS',result['status'])
if result['status']=='complete':print('ITEMS',answer['items'],'FACTS',answer['retrieval']['returned_facts'])
