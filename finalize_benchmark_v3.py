"""Summarize paired V3 trials without treating missing trials as measurements."""
import json,statistics,math
from pathlib import Path
ROOT=Path(__file__).parent

def median(xs):return statistics.median(xs) if xs else None
def summarize():
 files=list((ROOT/'reports/benchmark-v3').glob('*.json'))
 if not files:return {'status':'not_run'}
 state=json.loads(max(files,key=lambda p:p.stat().st_mtime).read_text(encoding='utf-8'))
 paired=[r for r in state['rows'].values() if 'cypher' in r and 'graphrag' in r]
 result={'status':state['status'],'model':state['model'],'fingerprint':state['fingerprint'],'reference_review':state['reference_review'],'paired_trials':len(paired),'expected_pairs':60,'distinct_questions_completed':len({r['question_id'] for r in paired}),'protocols':{},'limitations':['Provisional assistant reference annotations pending independent review','10 questions; repetitions are not 30 independent questions','A shared planner is used by both methods in question_only','Network/SDK/provider wall time is not GPU compute time','Small corpus, local[2] Spark, PDF affiliations limited to three papers']}
 for track in ['controlled','question_only']:
  rows=[r for r in paired if r['track']==track];methods={}
  for method in ['cypher','graphrag']:
   lat=[r[method]['latency_s'] for r in rows];end=[r[method]['latency_s']+r.get('planner_usage',{}).get('latency_s',0) for r in rows]
   methods[method]={'trials':len(rows),'mean_f1':statistics.mean(r[method]['metrics']['f1'] for r in rows) if rows else None,'exact_match_rate':statistics.mean(r[method]['metrics']['exact_match'] for r in rows) if rows else None,'median_method_latency_s':median(lat),'p95_method_latency_s':sorted(lat)[math.ceil(.95*len(lat))-1] if lat else None,'median_end_to_end_including_shared_planner_s':median(end),'repetitions_completed':{str(rep):sum(r['repetition']==rep for r in rows) for rep in [1,2,3]}}
   if method=='graphrag':
    methods[method].update(median_provider_request_wall_s=median([r[method]['usage']['request_wall_s'] for r in rows]),median_rate_and_retry_wait_s=median([r[method]['usage']['rate_wait_s']+r[method]['usage']['retry_wait_s'] for r in rows]),input_tokens=sum(r[method]['usage']['input_tokens'] for r in rows),output_tokens=sum(r[method]['usage']['output_tokens'] for r in rows))
  result['protocols'][track]=methods
 result['question_results']=[{'id':qid,'question':next(r['question'] for r in paired if r['question_id']==qid),'cypher_mean_f1':statistics.mean(r['cypher']['metrics']['f1'] for r in paired if r['question_id']==qid),'graphrag_mean_f1':statistics.mean(r['graphrag']['metrics']['f1'] for r in paired if r['question_id']==qid)} for qid in sorted({r['question_id'] for r in paired})]
 (ROOT/'reports/benchmark-v3-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('PAIRED',len(paired),'STATUS',result['status']);return result
if __name__=='__main__':summarize()
