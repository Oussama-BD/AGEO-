"""Resumable exploratory benchmark. Provisional references require an explicit flag."""
import os,json,hashlib,time,argparse
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).parent
load_dotenv(ROOT/'.env')
from app import llm,corpus_v3,rag_v3
from app.core import score
from app.arxiv_metadata import name_key

def fingerprint(graph,refs):return hashlib.sha256(json.dumps({'graph':graph,'reference':refs,'model':llm.model(),'protocol':2,'query_templates':corpus_v3.MODES},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def evaluate(expected,predicted):
 e={name_key(x) for x in expected};p={name_key(x) for x in predicted}
 return dict(score(e,p),exact_match=e==p)
def save(path,obj):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def run(max_calls=10,repetitions=3,allow_provisional=False):
 if llm.model()!='gemini-3.1-flash-lite':raise ValueError('This experiment requires the validated free-tier model gemini-3.1-flash-lite')
 refs=json.loads((ROOT/'data/references-v3/questions.proposed.json').read_text(encoding='utf-8'))
 if refs['review_status']!='independently_reviewed' and not allow_provisional:raise ValueError('Independent review pending; use --allow-provisional only for exploratory evaluation')
 graph=corpus_v3.graph();facts=corpus_v3.facts();fp=fingerprint(graph,refs)
 folder=ROOT/'reports/benchmark-v3';folder.mkdir(exist_ok=True);path=folder/(fp+'.json')
 state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'fingerprint':fp,'model':llm.model(),'reference_review':refs['review_status'],'interpretation':'exploratory; no validated superiority claim','repetitions_requested':repetitions,'rows':{},'status':'running'}
 if state['repetitions_requested']!=repetitions:raise ValueError('Repetition count mismatch')
 calls=0;state['status']='running'
 try:
  for rep in range(repetitions):
   for q in refs['questions']:
    for track in ['controlled','question_only']:
     key=f"{rep+1}:{q['id']}:{track}";row=state['rows'].setdefault(key,{'question_id':q['id'],'question':q['question'],'repetition':rep+1,'track':track})
     if 'plan' not in row:
      if track=='controlled':row['plan']={k:q[k] for k in ['mode','first','second']}
      else:
       if calls>=max_calls:state['status']='call_budget_reached';save(path,state);return state
       calls+=1;row['plan'],row['planner_usage']=rag_v3.plan(q['question'],graph['entities'])
      save(path,state)
     if 'cypher' not in row:
      start=time.perf_counter();items=[r['answer'] for r in corpus_v3.analytics(**row['plan'])]
      row['cypher']={'items':items,'latency_s':time.perf_counter()-start,'metrics':evaluate(q['expected'],items)};save(path,state)
     if 'graphrag' not in row:
      if calls>=max_calls:state['status']='call_budget_reached';save(path,state);return state
      calls+=1;answer=rag_v3.answer(q['question'],row['plan'],facts)
      answer['metrics']=evaluate(q['expected'],answer['items']);row['graphrag']=answer;save(path,state)
     print('COMPLETED',key,flush=True)
  state['status']='complete'
 except Exception as e:
  state['status']='quota_exhausted' if getattr(e,'code',None)==429 else 'failed';state['error_type']=type(e).__name__
 finally:
  state['calls_attempted_last_run']=calls;save(path,state)
  save(ROOT/'reports/benchmark-v3-latest.json',state)
 return state
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--max-calls',type=int,default=10);p.add_argument('--allow-provisional',action='store_true');a=p.parse_args()
 if not 0<=a.max_calls<=90:p.error('max-calls must be 0..90')
 r=run(a.max_calls,allow_provisional=a.allow_provisional);print('STATUS',r['status'],'ROWS',len(r['rows']))
