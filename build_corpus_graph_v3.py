"""Isolated v3 corpus construction; references are never read here."""
import json,hashlib
from pathlib import Path
from collections import Counter
from app.arxiv_metadata import author_graph,name_key
from app.core import locate_quote
ROOT=Path(__file__).parent
OUT=ROOT/'data/experiments/v3/records'
def ident(kind,name):return 'v3:'+kind.lower()+':'+hashlib.sha256(name_key(name).encode()).hexdigest()[:20]
def build():
 corpus=json.loads((ROOT/'data/corpus-v3/articles.json').read_text(encoding='utf-8'))
 topics=json.loads((ROOT/'data/experiments/v3/topics.predicted.json').read_text(encoding='utf-8'))
 OUT.mkdir(parents=True,exist_ok=True);records=[]
 for a in corpus:
  raw=(ROOT/a['html_file']).read_text(encoding='utf-8');assert hashlib.sha256(raw.encode()).hexdigest()==a['html_sha256']
  pid='v3:paper:'+a['arxiv_id']
  known=[{'id':pid,'name':a['title'],'type':'Paper'}]+[{'id':ident('Author',n),'name':n,'type':'Author'} for n in a['authors']]
  rec=author_graph(raw,known,a['arxiv_id'],pid)
  rec['document']['id']='v3:html:'+a['arxiv_id'];rec['source_sha256']=a['html_sha256']
  for r in rec['graph']['relations']:r['source_kind']='raw_html_metadata'
  for t in topics.get(a['arxiv_id'],[]):
   assert locate_quote(t['quote'],a['abstract']) is not None
   tid=ident('Topic',t['name'])
   rec['graph']['entities'].append({'id':tid,'name':t['name'],'type':'Topic'})
   rec['graph']['relations'].append({'source':pid,'target':tid,'type':'ABOUT','quote':t['quote'],'source_kind':'decoded_citation_abstract','method':'gemini-3.1-flash-lite'})
  records.append(rec)
 for stem in ['attention','rag','graphrag']:
  old=json.loads((ROOT/f'data/processed/real/{stem}.pdf.json').read_text(encoding='utf-8'));es={e['id']:e for e in old['graph']['entities']};nodes={};rels=[]
  for r in old['graph']['relations']:
   if r['type']!='AFFILIATED_WITH':continue
   row=dict(r,source_kind='pdf_extracted_text',method='previous_gemini_2.5_flash_prediction')
   for key in ['source','target']:
    e=es[r[key]];eid=ident(e['type'],e['name']);nodes[eid]=dict(e,id=eid);row[key]=eid
   rels.append(row)
  records.append({'document':dict(old['document'],id='v3:pdf:'+stem),'graph':{'entities':list(nodes.values()),'relations':rels}})
 for i,r in enumerate(records):
  assert all(e['id'].startswith('v3:') for e in r['graph']['entities'])
  (OUT/f'{i:02d}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 nodes={e['id']:e for r in records for e in r['graph']['entities']};rels=[x for r in records for x in r['graph']['relations']]
 report={'version':'v3','papers':len(corpus),'documents':len(records),'entity_count':len(nodes),'entities_by_type':dict(Counter(e['type'] for e in nodes.values())),'relations_by_type':dict(Counter(r['type'] for r in rels)),'topic_model':'gemini-3.1-flash-lite','topics_completed':len(topics),'references_used_for_construction':False,'neo4j_label':'ResearchV3','reference_review':'pending_independent_human_review'}
 (ROOT/'reports/corpus-graph-v3.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));return records
if __name__=='__main__':build()
