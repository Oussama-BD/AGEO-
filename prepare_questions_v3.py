"""Reference preparation ONLY: never imported by extraction or retrieval."""
import json,hashlib
from pathlib import Path
from app.arxiv_metadata import name_key
from build_corpus_graph_v3 import ident
R=Path(__file__).parent
def prepare():
 corpus=json.loads((R/'data/corpus-v3/articles.json').read_text(encoding='utf-8'))
 proposed=json.loads((R/'data/references-v3/topics.proposed.json').read_text(encoding='utf-8'))
 papers={a['arxiv_id']:a for a in corpus};topics={a['arxiv_id']:set(a['topics']) for a in proposed['papers']}
 affiliations={}
 for stem in ['attention','rag','graphrag']:
  ref=json.loads((R/f'data/gold/{stem}.pdf.json').read_text(encoding='utf-8'));es={e['id']:e for e in ref['graph']['entities']}
  for rel in ref['graph']['relations']:
   if rel['type']=='AFFILIATED_WITH':affiliations.setdefault(name_key(es[rel['source']]['name']),set()).add(es[rel['target']]['name'])
 def inst(aid):return sorted(set().union(*(affiliations.get(name_key(n),set()) for n in papers[aid]['authors'])))
 def topicpapers(t):return sorted(papers[i]['title'] for i,ts in topics.items() if t in ts)
 def author_topics(n):return sorted(set().union(*(topics[i] for i,a in papers.items() if name_key(n) in {name_key(x) for x in a['authors']})))
 defs=[
 ('mh1','Quelles institutions sont associées aux auteurs de Attention Is All You Need ?','paper_institutions','v3:paper:1706.03762','',inst('1706.03762'),2),
 ('mh2','Quels articles portent sur la génération augmentée par récupération ?','topic_papers',ident('Topic','retrieval-augmented generation'),'',topicpapers('retrieval-augmented generation'),1),
 ('mh3','Quels sujets sont reliés aux publications de Darren Edge ?','author_topics',ident('Author','Darren Edge'),'',author_topics('Darren Edge'),2),
 ('mh4','Quelles institutions sont reliées aux travaux sur les graphes de connaissances ?','topic_institutions',ident('Topic','knowledge graphs'),'',sorted(set().union(*(set(inst(i)) for i,ts in topics.items() if 'knowledge graphs' in ts))),3),
 ('mh5','Quels autres articles partagent au moins un sujet avec Attention Is All You Need ?','related_papers','v3:paper:1706.03762','',sorted(a['title'] for i,a in papers.items() if i!='1706.03762' and topics[i]&topics['1706.03762']),2),
 ('mh6','Quels sujets Big Bird et Longformer ont-ils en commun ?','common_topics','v3:paper:2007.14062','v3:paper:2004.05150',sorted(topics['2007.14062']&topics['2004.05150']),2),
 ('mh7','Quels auteurs ont signé à la fois Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks et Retrieval Augmentation Reduces Hallucination in Conversation ?','shared_authors','v3:paper:2005.11401','v3:paper:2104.07567',sorted(set(papers['2005.11401']['authors'])&set(papers['2104.07567']['authors'])),2),
 ('mh8','Quels articles sur la récupération dense ont été écrits par au moins un auteur de Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks ?','coauthor_topic_papers','v3:paper:2005.11401',ident('Topic','dense retrieval'),sorted(a['title'] for i,a in papers.items() if 'dense retrieval' in topics[i] and {name_key(n) for n in a['authors']}&{name_key(n) for n in papers['2005.11401']['authors']}),3),
 ('sem1','Quels articles proposent des méthodes pour guider le raisonnement des modèles ?','topic_papers',ident('Topic','reasoning methods'),'',topicpapers('reasoning methods'),1),
 ('sem2','Quels articles traitent de la prise en charge de longs contextes ?','topic_papers',ident('Topic','long-context modeling'),'',topicpapers('long-context modeling'),1)]
 questions=[dict(id=i,question=q,mode=m,first=f,second=s,expected=e,hops=h) for i,q,m,f,s,e,h in defs]
 result={'review_status':'pending_independent_human_review','reference_origin':'assistant abstract review plus arXiv author metadata and original proposed PDF references','scope':'semantic answers are operationalized by the frozen topic ontology, not all possible interpretations','questions':questions}
 dest=R/'data/references-v3/questions.proposed.json';data=json.dumps(result,ensure_ascii=False,indent=2)
 if dest.exists() and dest.read_text(encoding='utf-8')!=data:raise ValueError('Frozen reference differs; create a new version')
 dest.write_text(data,encoding='utf-8')
 print('FROZEN QUESTIONS',len(questions),'sha256',hashlib.sha256(data.encode()).hexdigest())
if __name__=='__main__':prepare()
