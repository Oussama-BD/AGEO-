import argparse
import json
import hashlib
import os
import requests
from pathlib import Path
from app import pipeline, store
ROOT=Path(__file__).parent
def upload():
    files=[]
    verified=[]
    def put_verified(name,content,directory):
        pipeline.hdfs_put(name,content,directory)
        url=os.getenv("WEBHDFS_URL","http://namenode:9870")+"/webhdfs/v1/knowledge/"+directory+"/"+name
        response=requests.get(url,params={"op":"OPEN","user.name":"root"},timeout=60)
        response.raise_for_status()
        if hashlib.sha256(response.content).digest()!=hashlib.sha256(content).digest():
            raise RuntimeError("HDFS checksum mismatch: "+name)
        verified.append(directory+"/"+name)
    for path in sorted((ROOT/"data"/"raw").iterdir()):
        if path.suffix in {".pdf",".html"}:
            put_verified(path.name,path.read_bytes(),"sources")
            files.append(path.name)
    count=0
    for path in sorted((ROOT/"data"/"processed"/"real").glob("*.json")):
        pred=json.loads(path.read_text(encoding="utf-8"))
        raw={"document":pred["document"],"text":pred["text"]}
        put_verified(path.name,json.dumps(raw,ensure_ascii=False).encode(),"raw")
        put_verified(path.name,path.read_bytes(),"extracted")
        count+=1
    result={"source_files":files,"extractions":count,"scope":"real frontmatter","sha256_readback_verified":verified}
    (ROOT/"reports"/"hdfs-upload.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

def load():
    loaded=pipeline.import_spark()
    result={"spark_import":loaded,
            "gds":store.query("RETURN gds.version() AS version"),
            "graph_counts":store.query("MATCH (n) RETURN count(n) AS nodes"),
            "relation_counts":store.query("MATCH ()-[r]->() RETURN count(r) AS relations"),
            "pagerank":store.pagerank()}
    (ROOT/"reports"/"integration.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=["upload","load"])
    a=p.parse_args();print(json.dumps(upload() if a.stage=="upload" else load(),ensure_ascii=False,indent=2))
