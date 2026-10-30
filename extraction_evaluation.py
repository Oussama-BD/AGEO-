"""Evaluation LLM sur un texte annote; --live requis pour tout appel."""
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from app import demo, llm
from app.core import normalized, score, resolve
ROOT=Path(__file__).parent
def signatures(graph):
    nodes={e["id"]:e for e in graph["entities"]}
    entities={(e["type"],normalized(e["name"])) for e in graph["entities"]}
    relations={(nodes[r["source"]]["type"],normalized(nodes[r["source"]]["name"]),r["type"],
                nodes[r["target"]]["type"],normalized(nodes[r["target"]]["name"])) for r in graph["relations"]}
    return entities,relations

def evaluate():
    prediction,usage=llm.extract(demo.TEXT)
    gold=demo.fixture()["graph"]
    ge,gr=signatures(gold)
    pe,pr=signatures(prediction)
    result={"corpus":"fictif annote manuellement", "entities":score(ge,pe), "relations":score(gr,pr),
            "resolution":{"before":len(prediction["entities"]),"after":len(resolve(prediction)["entities"])},
            "usage":usage, "prediction":prediction}
    (ROOT/"reports"/"extraction.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    if not args.live: parser.error("--live requis pour autoriser les appels Gemini")
    print(json.dumps(evaluate(),ensure_ascii=False,indent=2))
