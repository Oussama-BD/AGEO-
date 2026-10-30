"""Fixtures manuelles pour tests techniques; aucune extraction LLM simulee."""
from app.core import document_id, resolve, validate_graph

TEXT = """Corpus fictif de demonstration.
Alice Martin authored Graph Learning for Science.
Bob Karim authored Graph Learning for Science.
Alice Martin is affiliated with Universite Atlas.
Bob Karim is affiliated with Institut Horizon.
Graph Learning for Science is about Graph Learning.
Bob Karim authored Reliable Retrieval.
Clara Benali authored Reliable Retrieval.
Reliable Retrieval is about GraphRAG.
Reliable Retrieval cites Graph Learning for Science.
Clara Benali is affiliated with Universite Atlas."""
NAMES = [("a","Alice Martin","Author"),("b","Bob Karim","Author"),("c","Clara Benali","Author"),
 ("p","Graph Learning for Science","Paper"),("q","Reliable Retrieval","Paper"),
 ("u","Universite Atlas","Institution"),("i","Institut Horizon","Institution"),
 ("t","Graph Learning","Topic"),("g","GraphRAG","Topic")]
LINKS = [("a","p","AUTHORED",1),("b","p","AUTHORED",2),("a","u","AFFILIATED_WITH",3),
 ("b","i","AFFILIATED_WITH",4),("p","t","ABOUT",5),("b","q","AUTHORED",6),
 ("c","q","AUTHORED",7),("q","g","ABOUT",8),("q","p","CITES",9),("c","u","AFFILIATED_WITH",10)]

def fixture():
    graph = {"entities": [{"id": i,"name": n,"type": t} for i,n,t in NAMES],
             "relations": [{"source": a,"target": b,"type": t,"quote": TEXT.splitlines()[line]}
                           for a,b,t,line in LINKS]}
    validate_graph(graph, TEXT)
    return {"document": {"id": document_id(TEXT), "title": "Corpus fictif de demonstration",
                        "source": "demo.txt"}, "graph": resolve(graph), "mode": "manual_fixture", "usage": []}

def facts():
    record = fixture()
    entities = {e["id"]: e for e in record["graph"]["entities"]}
    return [dict(subject=entities[r["source"]]["name"], predicate=r["type"],
                 object=entities[r["target"]]["name"], quote=r["quote"],
                 document_id=record["document"]["id"], title=record["document"]["title"],
                 source="demo.txt") for r in record["graph"]["relations"]]
