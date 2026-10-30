"""Collecte reproducible de trois publications publiques en PDF et HTML."""
import json
from datetime import datetime, timezone
from pathlib import Path
import requests
ROOT=Path(__file__).parent
SOURCES=[
 ("attention","https://arxiv.org/pdf/1706.03762","https://arxiv.org/abs/1706.03762"),
 ("rag","https://arxiv.org/pdf/2005.11401","https://arxiv.org/abs/2005.11401"),
 ("graphrag","https://arxiv.org/pdf/2404.16130","https://arxiv.org/abs/2404.16130")]
def collect():
    manifest=[]
    for name,pdf,html in SOURCES:
        for extension,url in [("pdf",pdf),("html",html)]:
            path=ROOT/"data"/"raw"/f"{name}.{extension}"
            row={"url":url,"file":path.name,"retrieved_at":datetime.now(timezone.utc).isoformat()}
            try:
                response=requests.get(url,timeout=60,headers={"User-Agent":"AcademicKnowledgeGraph/1.0"})
                response.raise_for_status()
                if extension=="pdf" and not response.content.startswith(b"%PDF"):
                    raise ValueError("La reponse n'est pas un PDF")
                path.write_bytes(response.content)
                row.update(status="downloaded",bytes=len(response.content))
            except Exception as exc:
                row.update(status="failed",error=type(exc).__name__)
            manifest.append(row)
    (ROOT/"reports"/"source_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
if __name__=="__main__":
    print(json.dumps(collect(),indent=2))
