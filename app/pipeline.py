import io
import json
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from app.core import chunks, document_id, resolve
from app import llm, store

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
for part in ("raw", "processed"):
    (DATA / part).mkdir(parents=True, exist_ok=True)

def read_file(path):
    if path.suffix.lower() == ".pdf":
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    raw = path.read_text(encoding="utf-8-sig")
    return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True) if path.suffix.lower() in {".html", ".htm"} else raw

def fetch_openalex(search, limit=10):
    """Public metadata endpoint; pagination intentionally bounded for a student prototype."""
    response = requests.get("https://api.openalex.org/works",
        params={"search": search, "per-page": min(max(limit, 1), 25)},
        headers={"User-Agent": "AcademicKnowledgeGraph/1.0"}, timeout=45)
    response.raise_for_status()
    paths = []
    for work in response.json()["results"]:
        inverse = work.get("abstract_inverted_index") or {}
        words = {pos: word for word, positions in inverse.items() for pos in positions}
        abstract = " ".join(words[p] for p in sorted(words))
        authors = [a["author"]["display_name"] for a in work.get("authorships", [])]
        lines = [f"Title: {work['title']}", f"Authors: {', '.join(authors)}",
                 f"Year: {work.get('publication_year')}", f"Source: {work['id']}"]
        for authorship in work.get("authorships", []):
            for institution in authorship.get("institutions", []):
                lines.append(f"{authorship['author']['display_name']} is affiliated with {institution['display_name']}.")
        if abstract:
            lines.append("Abstract: " + abstract)
        path = DATA / "raw" / (work["id"].split("/")[-1] + ".txt")
        path.write_text("\n".join(lines), encoding="utf-8")
        paths.append(str(path))
    return paths

def hdfs_put(name, content, directory="raw"):
    base = os.getenv("WEBHDFS_URL", "http://namenode:9870").rstrip("/")
    url = f"{base}/webhdfs/v1/knowledge/{directory}"
    params = {"user.name": "root"}
    response = requests.put(url, params=dict(params, op="MKDIRS"), timeout=30)
    response.raise_for_status()
    response = requests.put(url + "/" + name, params=dict(params, op="CREATE", overwrite="true"),
                            allow_redirects=False, timeout=30)
    if response.status_code != 307:
        response.raise_for_status()
        raise RuntimeError("WebHDFS did not redirect to a datanode")
    response = requests.put(response.headers["Location"], data=content, timeout=60)
    response.raise_for_status()

def process(path, use_hdfs=True, load_graph=True):
    text = read_file(path)
    if not text.strip():
        raise ValueError("Document vide ou PDF scanne sans OCR")
    docid = document_id(text)
    doc = {"id": docid, "title": path.stem, "source": path.name}
    raw_record = {"document": doc, "text": text}
    (DATA / "raw" / f"{docid}.json").write_text(json.dumps(raw_record, ensure_ascii=False), encoding="utf-8")
    if use_hdfs:
        hdfs_put(docid + ".json", json.dumps(raw_record).encode())
    combined = {"entities": [], "relations": []}
    usages = []
    for i, chunk in enumerate(chunks(text)):
        graph, usage = llm.extract(chunk)
        remap = {e["id"]: f"{i}:{e['id']}" for e in graph["entities"]}
        combined["entities"].extend(dict(e, id=remap[e["id"]]) for e in graph["entities"])
        combined["relations"].extend(dict(r, source=remap[r["source"]], target=remap[r["target"]]) for r in graph["relations"])
        usages.append(usage)
    graph = resolve(combined)
    record = {"document": doc, "graph": graph, "usage": usages, "mode": "gemini"}
    output = DATA / "processed" / f"{docid}.json"
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    if use_hdfs:
        hdfs_put(output.name, output.read_bytes(), "extracted")
    if load_graph:
        store.ingest(doc, graph)
    return record

def import_spark():
    paths = sorted((DATA / "processed" / "spark").glob("part-*.json"))
    if not paths:
        raise RuntimeError("Aucun resultat Spark local. Executer le batch et verifier sa sortie file:///project/data/processed/spark")
    count = 0
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            store.ingest(record["document"], record["graph"])
            count += 1
    return {"imported_documents": count}
