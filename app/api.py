import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app import store, rag, pipeline, demo
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
app = FastAPI(title="AGEO RECHERCHE", version="1.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kg")

def auth(x_api_token: str = Header(default="")):
    expected = os.getenv("API_TOKEN", "")
    if not expected or not hmac.compare_digest(x_api_token, expected):
        raise HTTPException(401, "Jeton API absent ou incorrect")

@app.middleware("http")
async def timing(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("request_failed path=%s type=%s", request.url.path, type(exc).__name__)
        quota = getattr(exc,"code",None) == 429
        response = JSONResponse(status_code=429 if quota else 503, content={"detail":
            "Quota Gemini atteint. Consulter une reponse enregistree ou reessayer apres renouvellement." if quota
            else "Service indisponible. Consulter les journaux locaux."})
    response.headers["X-Process-Time"] = str(round(time.perf_counter()-started, 4))
    logger.info("%s %s status=%d", request.method, request.url.path, response.status_code)
    return response

@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")

@app.get("/health")
def health():
    statuses = {"api": "ok", "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))}
    try:
        store.query("RETURN 1 AS ok")
        statuses["neo4j"] = "ok"
    except Exception:
        statuses["neo4j"] = "unavailable"
    return statuses

@app.get("/demo")
def get_demo():
    return demo.fixture()

@app.get("/graph", dependencies=[Depends(auth)])
def graph():
    nodes = store.query("MATCH (e:Entity) RETURN e.id AS id, e.name AS name, e.kind AS type LIMIT 300")
    edges = store.query("MATCH (a:Entity)-[r]->(b:Entity) RETURN a.id AS source, b.id AS target, type(r) AS type, r.quote AS quote, r.document_id AS document_id LIMIT 500")
    return {"entities": nodes, "relations": edges}

class Query(BaseModel):
    mode: Literal["authors", "papers", "institutions", "topic_authors", "paper_institutions"]
    term: str = Field(min_length=2, max_length=200)

@app.post("/analytics", dependencies=[Depends(auth)])
def analytics(q: Query):
    start = time.perf_counter()
    return {"rows": store.query(store.TEMPLATES[q.mode], term=q.term), "latency_s": time.perf_counter()-start}

class Question(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    term: str | None = Field(default=None, min_length=2, max_length=300)

@app.post("/ask", dependencies=[Depends(auth)])
def ask(q: Question):
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(409, "Configurez GEMINI_API_KEY dans le fichier .env local")
    return rag.ask(q.question, q.term)

@app.get("/pagerank", dependencies=[Depends(auth)])
def pagerank():
    return store.pagerank()

@app.post("/seed", dependencies=[Depends(auth)])
def seed():
    record = demo.fixture()
    store.ingest(record["document"], record["graph"])
    return {"entities": len(record["graph"]["entities"]), "relations": len(record["graph"]["relations"]), "mode": "manual_fixture"}

class Import(BaseModel):
    filename: str
    hdfs: bool = True

@app.get("/files", dependencies=[Depends(auth)])
def files():
    return [p.name for p in (ROOT/"data"/"raw").iterdir() if p.suffix.lower() in {".pdf",".txt",".html",".htm"}]

@app.post("/ingest", dependencies=[Depends(auth)])
def ingest(body: Import):
    path = (ROOT/"data"/"raw"/body.filename).resolve()
    if path.parent != (ROOT/"data"/"raw").resolve() or not path.is_file():
        raise HTTPException(400, "Fichier non valide")
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(409, "Configurez GEMINI_API_KEY dans le fichier .env local")
    return pipeline.process(path, use_hdfs=body.hdfs, load_graph=not body.hdfs)

@app.post("/import-spark", dependencies=[Depends(auth)])
def import_spark():
    return pipeline.import_spark()

@app.get("/benchmark", dependencies=[Depends(auth)])
def benchmark_result():
    path = ROOT/"reports"/"real-benchmark.json"
    if not path.exists(): path = ROOT/"reports"/"benchmark.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "not_run"}


@app.get("/example", dependencies=[Depends(auth)])
def saved_example():
    path=ROOT/"reports"/"real-benchmark.json"
    if not path.exists(): raise HTTPException(404,"Aucune reponse reelle enregistree")
    report=json.loads(path.read_text(encoding="utf-8"))
    candidates=[a for a in report["answers"] if a["case"]=="real5" and a["track"]=="question_only"]
    return {"recorded":True,"model":report.get("model"),"question":candidates[0]["question"],
            "result":candidates[0]["answer"]} if candidates else {"recorded":True,"result":report["answers"][0]["answer"]}


# Expanded corpus is isolated from historical Entity/Document labels.
@app.get("/v3")
def v3_home():
    return FileResponse(ROOT / "static" / "corpus-v3.html")

@app.get("/v3/status")
def v3_status():
    from app import corpus_v3
    result=corpus_v3.status()
    result["neo4j_imported"]=(ROOT/"reports/neo4j-v3.json").exists()
    result["spark_executed"]=(ROOT/"reports/spark-v3-success.json").exists()
    return result

@app.get("/v3/graph", dependencies=[Depends(auth)])
def v3_graph():
    from app import corpus_v3
    return corpus_v3.graph()

@app.get("/v3/pagerank", dependencies=[Depends(auth)])
def v3_pagerank():
    from app import corpus_v3
    return corpus_v3.pagerank()

class V3Question(BaseModel):
    question: str = Field(min_length=3,max_length=1200)

@app.post("/v3/ask", dependencies=[Depends(auth)])
def v3_ask(body:V3Question):
    from app import corpus_v3,rag_v3
    from app.llm import model
    if model()!="gemini-3.1-flash-lite":
        raise HTTPException(409,"Configurer explicitement le modèle gratuit validé gemini-3.1-flash-lite pour cette expérience.")
    plan,usage=rag_v3.plan(body.question)
    cypher=corpus_v3.analytics(**plan)
    result=rag_v3.answer(body.question,plan)
    return {"execution":"live","model":model(),"plan":plan,"planner_usage":usage,"cypher":cypher,"graphrag":result}

@app.get("/v3/benchmark", dependencies=[Depends(auth)])
def v3_benchmark():
    path=ROOT/"reports/benchmark-v3-latest.json"
    checkpoints=list((ROOT/"reports/benchmark-v3").glob("*.json"))
    if checkpoints:path=max(checkpoints,key=lambda p:p.stat().st_mtime)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status":"not_run","reference_review":"pending_independent_human_review","rows":{}}


@app.get("/v3/prepared-graph", dependencies=[Depends(auth)])
def v3_prepared_graph():
    entities={};relations=[]
    for path in sorted((ROOT/"data/experiments/v3/records").glob("*.json")):
        rec=json.loads(path.read_text(encoding="utf-8"))
        entities.update({e["id"]:e for e in rec["graph"]["entities"]})
        relations.extend(dict(r,document_id=rec["document"]["id"]) for r in rec["graph"]["relations"])
    return {"entities":list(entities.values()),"relations":relations,"execution":"prepared_local_files"}
