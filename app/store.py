import os
import uuid
from neo4j import GraphDatabase
from app.core import PAIRS, normalized

def driver():
    return GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=("neo4j", os.environ["NEO4J_PASSWORD"]), connection_timeout=5, max_transaction_retry_time=5)

def query(cypher, **params):
    if "$document_ids" in cypher:
        params.setdefault("document_ids", None)
    if "$searchterm" in cypher:
        params["searchterm"] = normalized(params.get("term", ""))
    with driver() as d:
        records, _, _ = d.execute_query(cypher, parameters_=params, database_=os.getenv("NEO4J_DATABASE","neo4j"))
        return [r.data() for r in records]

def ingest(doc, graph):
    with driver() as d, d.session(database=os.getenv("NEO4J_DATABASE","neo4j")) as session:
        session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE").consume()
        session.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE").consume()
        def write(tx):
            tx.run("MERGE (d:Document {id:$id}) SET d.title=$title, d.source=$source", **doc).consume()
            rows=[dict(e,search_name=normalized(e["name"])) for e in graph["entities"]]
            tx.run("UNWIND $rows AS row MERGE (e:Entity {id:row.id}) SET e.name=row.name, e.kind=row.type, e.search_name=row.search_name",rows=rows).consume()
            for rel in graph["relations"]:
                if rel["type"] not in PAIRS:
                    raise ValueError("Invalid relationship type")
                tx.run("MATCH (a:Entity {id:$source}), (b:Entity {id:$target}) "
                    f"MERGE (a)-[r:{rel['type']} {{document_id:$docid, quote:$quote}}]->(b)",
                    source=rel["source"], target=rel["target"], docid=doc["id"], quote=rel["quote"]).consume()
        session.execute_write(write)

def retrieve(term, document_ids=None):
    return query("""MATCH (seed:Entity)
    WHERE coalesce(seed.search_name,toLower(seed.name)) CONTAINS $searchterm
    WITH seed LIMIT 10 MATCH p=(seed)-[*1..2]-(other:Entity)
    WHERE all(r IN relationships(p) WHERE r.document_id IS NOT NULL
      AND ($document_ids IS NULL OR r.document_id IN $document_ids))
    UNWIND relationships(p) AS r WITH DISTINCT r LIMIT 150
    MATCH (d:Document {id:r.document_id})
    RETURN startNode(r).name AS subject, type(r) AS predicate, endNode(r).name AS object,
    r.quote AS quote, d.id AS document_id, d.title AS title, d.source AS source""",term=term,document_ids=document_ids)

ONE="($document_ids IS NULL OR r.document_id IN $document_ids)"
TEMPLATES={
 "authors": f"MATCH (a:Entity)-[r:AUTHORED]->(p:Entity) WHERE coalesce(p.search_name,toLower(p.name)) CONTAINS $searchterm AND {ONE} RETURN DISTINCT a.name AS answer, r.document_id AS document_id",
 "papers": f"MATCH (a:Entity)-[r:AUTHORED]->(p:Entity) WHERE coalesce(a.search_name,toLower(a.name)) CONTAINS $searchterm AND {ONE} RETURN DISTINCT p.name AS answer, r.document_id AS document_id",
 "institutions": f"MATCH (a:Entity)-[r:AFFILIATED_WITH]->(i:Entity) WHERE coalesce(a.search_name,toLower(a.name)) CONTAINS $searchterm AND {ONE} RETURN DISTINCT i.name AS answer, r.document_id AS document_id",
 "topic_authors": "MATCH (a:Entity)-[s:AUTHORED]->(p:Entity)-[r:ABOUT]->(t:Entity) WHERE coalesce(t.search_name,toLower(t.name)) CONTAINS $searchterm AND ($document_ids IS NULL OR (r.document_id IN $document_ids AND s.document_id IN $document_ids)) RETURN DISTINCT a.name AS answer, r.document_id AS document_id",
 "paper_institutions": "MATCH (p:Entity)<-[s:AUTHORED]-(a:Entity)-[r:AFFILIATED_WITH]->(i:Entity) WHERE coalesce(p.search_name,toLower(p.name)) CONTAINS $searchterm AND ($document_ids IS NULL OR (r.document_id IN $document_ids AND s.document_id IN $document_ids)) RETURN DISTINCT i.name AS answer, r.document_id AS document_id"
}
def analytics(mode,term,document_ids=None):
    return query(TEMPLATES[mode],term=term,document_ids=document_ids)

def pagerank():
    name="analytics_"+uuid.uuid4().hex
    query("CALL gds.graph.project($name, 'Entity', '*') YIELD graphName RETURN graphName",name=name)
    try:
        return query("CALL gds.pageRank.stream($name) YIELD nodeId, score RETURN gds.util.asNode(nodeId).name AS name, score ORDER BY score DESC LIMIT 20",name=name)
    finally:
        query("CALL gds.graph.drop($name) YIELD graphName RETURN graphName",name=name)
