"""Backend de demonstration explicite, sans Neo4j ni LLM."""
from app.demo import fixture
from app.core import normalized

def analytics(mode, term):
    graph = fixture()["graph"]
    nodes = {e["id"]:e for e in graph["entities"]}
    rels = graph["relations"]
    term = normalized(term)
    result = set()
    for r in rels:
        a,b = nodes[r["source"]], nodes[r["target"]]
        if mode == "authors" and r["type"] == "AUTHORED" and term in normalized(b["name"]):
            result.add(a["name"])
        if mode == "papers" and r["type"] == "AUTHORED" and term in normalized(a["name"]):
            result.add(b["name"])
        if mode == "institutions" and r["type"] == "AFFILIATED_WITH" and term in normalized(a["name"]):
            result.add(b["name"])
        if mode == "topic_authors" and r["type"] == "ABOUT" and term in normalized(b["name"]):
            for s in rels:
                if s["type"] == "AUTHORED" and s["target"] == a["id"]:
                    result.add(nodes[s["source"]]["name"])
    return [{"answer":v, "document_id":fixture()["document"]["id"]} for v in sorted(result)]
