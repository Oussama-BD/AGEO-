"""Evaluation: offline = controles techniques; live = Neo4j contre Gemini GraphRAG."""
import argparse
import json
import os
import statistics
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from app import local_demo, store, rag
from app.core import normalized, score
ROOT = Path(__file__).parent
CASES = [
 {"id":"q1","mode":"authors","term":"Graph Learning for Science","question":"Qui a ecrit Graph Learning for Science ?","expected":["Alice Martin","Bob Karim"]},
 {"id":"q2","mode":"papers","term":"Bob Karim","question":"Quels articles Bob Karim a-t-il ecrits ?","expected":["Graph Learning for Science","Reliable Retrieval"]},
 {"id":"q3","mode":"institutions","term":"Clara Benali","question":"A quelle institution Clara Benali est-elle affiliee ?","expected":["Universite Atlas"]},
 {"id":"q4","mode":"topic_authors","term":"GraphRAG","question":"Quels auteurs ont ecrit des articles sur GraphRAG ?","expected":["Bob Karim","Clara Benali"]},
 {"id":"q5","mode":"authors","term":"Reliable Retrieval","question":"Qui a ecrit Reliable Retrieval ?","expected":["Bob Karim","Clara Benali"]},
 {"id":"q6","mode":"papers","term":"Auteur absent","question":"Quels articles Auteur absent a-t-il ecrits ?","expected":[]}
]

def cost(usage):
    rates = [os.getenv("INPUT_USD_PER_MILLION"), os.getenv("OUTPUT_USD_PER_MILLION")]
    if not all(rates):
        return None
    return (usage.get("input_tokens",0)*float(rates[0]) + usage.get("output_tokens",0)*float(rates[1]))/1e6

def run(live=False, repeats=3):
    rows = []
    for case in CASES:
        for repetition in range(repeats):
            start = time.perf_counter()
            actual = store.query(store.TEMPLATES[case["mode"]],term=case["term"]) if live else local_demo.analytics(case["mode"],case["term"])
            latency = time.perf_counter()-start
            predicted = [r["answer"] for r in actual]
            metrics = score(map(normalized,case["expected"]),map(normalized,predicted))
            rows.append(dict(case_id=case["id"], method="Cypher" if live else "Local fixture traversal",
                repetition=repetition, predicted=predicted, exact_match=set(map(normalized,predicted))==set(map(normalized,case["expected"])),
                latency_s=latency, **metrics))
            if live:
                answer = rag.ask(case["question"],case["term"])
                usage = answer.get("usage",{})
                rows.append(dict(case_id=case["id"],method="GraphRAG", repetition=repetition,
                    predicted=answer["items"], latency_s=answer["latency_s"],
                    exact_match=set(map(normalized,answer["items"]))==set(map(normalized,case["expected"])),
                    source_count=len(answer["sources"]), estimated_usd=cost(usage), usage=usage,
                    **score(map(normalized,case["expected"]),map(normalized,answer["items"]))))
    summary = {}
    for method in sorted({r["method"] for r in rows}):
        subset = [r for r in rows if r["method"]==method]
        summary[method] = {"exact_match": statistics.mean(r["exact_match"] for r in subset),
            "mean_f1":statistics.mean(r["f1"] for r in subset),
            "median_latency_s":statistics.median(r["latency_s"] for r in subset),
            "p95_latency_s":sorted(r["latency_s"] for r in subset)[max(0,int(.95*len(subset))-1)]}
    result = {"mode":"live" if live else "offline_technical_checks", "cases":len(CASES),
        "repeats":repeats, "summary":summary, "rows":rows,
        "note":"Corpus fictif. Les controles offline ne mesurent ni la qualite du LLM ni Neo4j. Une reponse vide correcte obtient F1=1 par convention explicite; consulter aussi les mesures hors cas vides."}
    path = ROOT/"reports"/"benchmark.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--live",action="store_true",help="Necessite Neo4j avec fixture chargee et cle Gemini valide; appels potentiellement payants")
    parser.add_argument("--repeats",type=int,default=3)
    args=parser.parse_args()
    if args.repeats < 1: parser.error("--repeats doit etre positif")
    print(json.dumps(run(args.live,args.repeats),ensure_ascii=False,indent=2))
