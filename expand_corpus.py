"""Collecte publique bornee de 25 resumes arXiv, avec cache et delai entre requetes."""
import json,time,hashlib
from datetime import datetime,timezone
from pathlib import Path
import requests
from app.arxiv_metadata import parse_arxiv
ROOT=Path(__file__).parent
IDS=["1706.03762","2005.11401","2404.16130","1810.04805","1802.05365","1907.11692",
"1910.10683","2004.04906","2007.14062","2004.05150","2002.08909","1906.00300",
"1911.00172","2001.08361","2005.14165","2302.13971","2307.09288","2310.06825",
"2203.02155","2201.11903","2205.11916","2210.03629","2305.10601","2212.10496","2104.07567"]
def collect():
    folder=ROOT/"data"/"raw"/"abstracts-v3";folder.mkdir(parents=True,exist_ok=True)
    existing={"1706.03762":"attention.html","2005.11401":"rag.html","2404.16130":"graphrag.html"}
    records=[];errors=[];failures=0
    session=requests.Session();session.headers["User-Agent"]="AcademicKnowledgeGraph/1.0 (public research metadata)"
    for aid in IDS:
        path=folder/(aid+".html")
        try:
            if not path.exists():
                if aid in existing and (ROOT/"data"/"raw"/existing[aid]).exists():
                    path.write_bytes((ROOT/"data"/"raw"/existing[aid]).read_bytes())
                else:
                    time.sleep(3.2)
                    response=session.get("https://arxiv.org/abs/"+aid,timeout=40)
                    response.raise_for_status()
                    parse_arxiv(response.text) # Reject captcha or error pages before caching.
                    path.write_bytes(response.content)
            text=path.read_text(encoding="utf-8")
            parsed=parse_arxiv(text)
            if not parsed["abstract"] or not parsed["abstract"]["value"].strip():raise ValueError("No abstract")
            records.append({"arxiv_id":aid,"title":parsed["title"]["value"],
                "authors":[a["name"] for a in parsed["authors"]],"abstract":parsed["abstract"]["value"],
                "source":"https://arxiv.org/abs/"+aid,"html_file":str(path.relative_to(ROOT)).replace("\\","/"),
                "html_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
                "collected_at":datetime.now(timezone.utc).isoformat()})
            print(aid,parsed["title"]["value"],flush=True);failures=0
        except Exception as exc:
            failures+=1;errors.append({"arxiv_id":aid,"error":type(exc).__name__})
            if failures>=3:break
    destination=ROOT/"data"/"corpus-v3";destination.mkdir(parents=True,exist_ok=True)
    (destination/"articles.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    report={"target":len(IDS),"collected":len(records),"errors":errors,"llm_calls":0,
        "scope":"titles authors and abstracts; no full-text claims"}
    (ROOT/"reports"/"corpus-v3.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report),flush=True)
if __name__=="__main__":collect()
