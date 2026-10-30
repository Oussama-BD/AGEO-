"""Annotations sourcees des premieres pages, preparees par l'assistant, a faire relire."""
import json
from pathlib import Path
from pypdf import PdfReader
from app.core import document_id, resolve, validate_graph
ROOT=Path(__file__).parent
papers=[
 {"file":"attention.pdf","url":"https://arxiv.org/abs/1706.03762",
  "title":"Attention Is All You Need",
  "authors":["Ashish Vaswani","Noam Shazeer","Niki Parmar","Jakob Uszkoreit","Llion Jones","Aidan N. Gomez","Łukasz Kaiser","Illia Polosukhin"],
  "affiliations":{"Ashish Vaswani":["Google Brain"],"Noam Shazeer":["Google Brain"],"Niki Parmar":["Google Research"],"Jakob Uszkoreit":["Google Research"],"Llion Jones":["Google Research"],"Aidan N. Gomez":["University of Toronto"],"Łukasz Kaiser":["Google Brain"]}},
 {"file":"graphrag.pdf","url":"https://arxiv.org/abs/2404.16130",
  "title":"From Local to Global: A GraphRAG Approach to Query-Focused Summarization",
  "authors":["Darren Edge","Ha Trinh","Newman Cheng","Joshua Bradley","Alex Chao","Apurva Mody","Steven Truitt","Dasha Metropolitansky","Robert Osazuwa Ness","Jonathan Larson"],
  "affiliations":{}},
 {"file":"rag.pdf","url":"https://arxiv.org/abs/2005.11401",
  "title":"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
  "authors":["Patrick Lewis","Ethan Perez","Aleksandra Piktus","Fabio Petroni","Vladimir Karpukhin","Naman Goyal","Heinrich Küttler","Mike Lewis","Wen-tau Yih","Tim Rocktäschel","Sebastian Riedel","Douwe Kiela"],
  "affiliations":{}}
]
g=papers[1]
g["affiliations"]={name:[("Microsoft Research" if name in {"Darren Edge","Ha Trinh","Dasha Metropolitansky","Robert Osazuwa Ness","Jonathan Larson"} else "Microsoft Strategic Missions and Technologies" if name in {"Newman Cheng","Joshua Bradley","Steven Truitt"} else "Microsoft Office of the CTO")] for name in g["authors"]}
r=papers[2]
r["affiliations"]={name:(["New York University"] if name=="Ethan Perez" else ["Facebook AI Research","University College London"] if name in {"Patrick Lewis","Tim Rocktäschel","Sebastian Riedel"} else ["Facebook AI Research"]) for name in r["authors"]}
out=ROOT/"data"/"gold"
out.mkdir(parents=True,exist_ok=True)
records=[]
for p in papers:
    text=PdfReader(ROOT/"data"/"raw"/p["file"]).pages[0].extract_text()
    front=text.split("Abstract")[0]
    # Only the affiliation author-block is evaluated; footnote past employers are outside scope.
    doc={"id":"real-"+document_id(front),"title":p["title"],"source":p["url"]+"#page=1"}
    entities=[{"id":"paper","name":p["title"],"type":"Paper"}]
    relations=[]
    for i,name in enumerate(p["authors"]):
        aid="author-"+str(i)
        entities.append({"id":aid,"name":name,"type":"Author"})
        relations.append({"source":aid,"target":"paper","type":"AUTHORED","quote":front})
        for institution in p["affiliations"].get(name,[]):
            iid="institution-"+institution
            if not any(e["id"]==iid for e in entities):
                entities.append({"id":iid,"name":institution,"type":"Institution"})
            relations.append({"source":aid,"target":iid,"type":"AFFILIATED_WITH","quote":front})
    graph=validate_graph({"entities":entities,"relations":relations},front)
    record={"document":doc,"text":front,"graph":resolve(graph),"source_file":p["file"],
            "page":1,"annotation_scope":"Title, full author listing and current affiliations in front matter; no footnote historical affiliations",
            "annotated_by":"assistant_source_review","review_status":"pending_independent_human_review",
            "evaluation_types":["Author","Institution","Paper"],"evaluation_relations":["AUTHORED","AFFILIATED_WITH"]}
    (out/(p["file"]+".json")).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    records.append(record)
cases=[]
def case(id,mode,term,question,expected):
    cases.append(dict(id=id,mode=mode,term=term,question=question,expected=expected))
case("real1","authors",papers[0]["title"],"Qui sont les auteurs de l'article Attention Is All You Need ?",papers[0]["authors"])
case("real2","authors",papers[1]["title"],"Qui a redige l'article From Local to Global: A GraphRAG Approach to Query-Focused Summarization ?",papers[1]["authors"])
case("real3","authors",papers[2]["title"],"Donne les auteurs de Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.",papers[2]["authors"])
case("real4","institutions","Patrick Lewis","Quelles affiliations sont indiquees pour Patrick Lewis ?",papers[2]["affiliations"]["Patrick Lewis"])
case("real5","institutions","Darren Edge","A quelle institution Darren Edge est-il rattache ?",["Microsoft Research"])
case("real6","paper_institutions",papers[0]["title"],"Quelles institutions sont representees par les auteurs de Attention Is All You Need ?",["Google Brain","Google Research","University of Toronto"])
case("real7","papers","Ha Trinh","Quels articles du corpus ont ete ecrits par Ha Trinh ?",[papers[1]["title"]])
case("real8","institutions","Auteur Inconnu XYZ","Quelles sont les affiliations de Auteur Inconnu XYZ ?",[])
(out/"questions.json").write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"documents":len(records),"questions":len(cases),"authors":sum(len(p["authors"]) for p in papers)},indent=2))
