import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from app import llm
from app.core import resolve, normalized, score
ROOT=Path(__file__).parent
def signatures(graph):
    nodes={e["id"]:e for e in graph["entities"]}
    es={(e["type"],normalized(e["name"])) for e in graph["entities"] if e["type"] in {"Author","Institution","Paper"}}
    rs={(nodes[r["source"]]["type"],normalized(nodes[r["source"]]["name"]),r["type"],
         nodes[r["target"]]["type"],normalized(nodes[r["target"]]["name"])) for r in graph["relations"]
         if r["type"] in {"AUTHORED","AFFILIATED_WITH"}}
    return es,rs

def run():
    results=[]
    target=ROOT/"data"/"processed"/"real"
    target.mkdir(parents=True,exist_ok=True)
    for path in sorted((ROOT/"data"/"gold").glob("*.pdf.json")):
        gold=json.loads(path.read_text(encoding="utf-8"))
        dest=target/path.name
        if dest.exists():
            pred=json.loads(dest.read_text(encoding="utf-8"))
            if pred.get("model") != llm.model(): raise RuntimeError("Cache model mismatch")
        else:
            graph,usage=llm.extract(gold["text"])
            pred={"document":gold["document"],"text":gold["text"],"graph":resolve(graph),
                  "usage":usage,"model":llm.model(),"mode":"gemini_real_frontmatter",
                  "scope":gold["annotation_scope"],"annotation_review":gold["review_status"]}
            dest.write_text(json.dumps(pred,ensure_ascii=False,indent=2),encoding="utf-8")
        ge,gr=signatures(gold["graph"]);pe,pr=signatures(pred["graph"])
        row={"file":path.name,"entity_metrics":score(ge,pe),"relation_metrics":score(gr,pr),
             "gold_entities":len(ge),"predicted_entities":len(pe),"gold_relations":len(gr),"predicted_relations":len(pr),
             "missing_relations":[list(r) for r in sorted(gr-pr)],
             "extra_relations":[list(r) for r in sorted(pr-gr)],"usage":pred["usage"]}
        results.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in {"missing_relations","extra_relations","usage"}},ensure_ascii=False),flush=True)
    report={"mode":"live_gemini","scope":"frontmatter_only","annotation_review":"pending_independent_human_review",
            "model":llm.model(),"documents":results}
    (ROOT/"reports"/"real-extraction.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report
if __name__=="__main__":run()
