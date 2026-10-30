"""Neo4j v3 uses dedicated labels, preserving the original experiment."""
import json,uuid
from pathlib import Path
from app import store
ROOT=Path(__file__).resolve().parents[1]
MODES={
 'paper_institutions':('MATCH (p:ResearchV3)<-[:AUTHORED]-(a:ResearchV3)-[:AFFILIATED_WITH]->(i:ResearchV3) WHERE p.id=$first','i'),
 'topic_papers':('MATCH (p:ResearchV3)-[:ABOUT]->(t:ResearchV3) WHERE t.id=$first','p'),
 'author_topics':('MATCH (a:ResearchV3)-[:AUTHORED]->(p:ResearchV3)-[:ABOUT]->(t:ResearchV3) WHERE a.id=$first','t'),
 'topic_institutions':('MATCH (t:ResearchV3)<-[:ABOUT]-(p:ResearchV3)<-[:AUTHORED]-(a:ResearchV3)-[:AFFILIATED_WITH]->(i:ResearchV3) WHERE t.id=$first','i'),
 'related_papers':('MATCH (p:ResearchV3)-[:ABOUT]->(t:ResearchV3)<-[:ABOUT]-(q:ResearchV3) WHERE p.id=$first AND q.id<>p.id','q'),
 'common_topics':('MATCH (p:ResearchV3)-[:ABOUT]->(t:ResearchV3)<-[:ABOUT]-(q:ResearchV3) WHERE p.id=$first AND q.id=$second','t'),
 'shared_authors':('MATCH (p:ResearchV3)<-[:AUTHORED]-(a:ResearchV3)-[:AUTHORED]->(q:ResearchV3) WHERE p.id=$first AND q.id=$second','a'),
 'coauthor_topic_papers':('MATCH (p:ResearchV3)<-[:AUTHORED]-(a:ResearchV3) MATCH (a)-[:AUTHORED]->(q:ResearchV3)-[:ABOUT]->(t:ResearchV3) WHERE p.id=$first AND t.id=$second','q')}
def graph():
 return {'entities':store.query('MATCH (e:ResearchV3) RETURN e.id AS id,e.name AS name,e.kind AS type ORDER BY e.id'),
 'relations':store.query('MATCH (a:ResearchV3)-[r]->(b:ResearchV3) RETURN a.id AS source,b.id AS target,type(r) AS type,r.quote AS quote,r.document_id AS document_id,r.source_kind AS source_kind ORDER BY source,target,type,document_id,quote')}
def ingest(records):
 store.query('CREATE CONSTRAINT research_v3_id IF NOT EXISTS FOR (e:ResearchV3) REQUIRE e.id IS UNIQUE')
 for rec in records:
  doc=rec['document'];store.query('MERGE (d:SourceV3 {id:$id}) SET d.title=$title,d.source=$source',**doc)
  store.query('UNWIND $rows AS e MERGE (n:ResearchV3 {id:e.id}) SET n.name=e.name,n.kind=e.type',rows=rec['graph']['entities'])
  for typ in ['AUTHORED','ABOUT','AFFILIATED_WITH']:
   rows=[dict(r,document_id=doc['id']) for r in rec['graph']['relations'] if r['type']==typ]
   store.query('UNWIND $rows AS r MATCH (a:ResearchV3 {id:r.source}),(b:ResearchV3 {id:r.target}) '+f'MERGE (a)-[e:{typ} {{document_id:r.document_id,quote:r.quote}}]->(b) SET e.source_kind=r.source_kind,e.method=r.method',rows=rows)
def analytics(mode,first,second=''):
 pattern,node=MODES[mode]
 return store.query(pattern+f' RETURN DISTINCT {node}.name AS answer ORDER BY answer',first=first,second=second)
def facts():
 return store.query('MATCH (a:ResearchV3)-[r]->(b:ResearchV3) MATCH (d:SourceV3 {id:r.document_id}) RETURN a.id AS subject_id,a.name AS subject,type(r) AS predicate,b.id AS object_id,b.name AS object,r.document_id AS source_id,d.source AS url,r.quote AS quote,r.source_kind AS source_kind ORDER BY subject_id,predicate,object_id')
def pagerank():
 name='v3_'+uuid.uuid4().hex
 store.query("CALL gds.graph.project($name,'ResearchV3',['AUTHORED','ABOUT','AFFILIATED_WITH']) YIELD graphName RETURN graphName",name=name)
 try:return store.query('CALL gds.pageRank.stream($name) YIELD nodeId,score RETURN gds.util.asNode(nodeId).name AS name,score ORDER BY score DESC LIMIT 20',name=name)
 finally:store.query('CALL gds.graph.drop($name) YIELD graphName RETURN graphName',name=name)
def status():return json.loads((ROOT/'reports/corpus-graph-v3.json').read_text(encoding='utf-8'))
if __name__=='__main__':
 from dotenv import load_dotenv
 load_dotenv(ROOT/'.env')
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--input',choices=['records','spark'],default='records');args=parser.parse_args()
 if args.input=='spark':
  records=[json.loads(line) for p in sorted((ROOT/'data/experiments/v3/spark').glob('part-*.json')) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
 else:records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'data/experiments/v3/records').glob('*.json'))]
 if len(records)!=28:raise ValueError('Expected all 28 source records before importing')
 before=store.query('MATCH (e:Entity) RETURN count(e) AS entities')
 ingest(records)
 result={'import_input':args.input,'v3_entities':len(graph()['entities']),'v3_relations':len(graph()['relations']),'legacy_before':before,'legacy_after':store.query('MATCH (e:Entity) RETURN count(e) AS entities'),'pagerank':pagerank()}
 (ROOT/'reports/neo4j-v3.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
