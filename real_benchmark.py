"""Comparaison reelle, sur un graphe construit par Gemini, avec deux conditions."""
import argparse
import json
import statistics
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from app import store, rag, llm
from app.core import score, normalized
ROOT=Path(__file__).parent

def run(limit=8):
    cases=json.loads((ROOT/"data"/"gold"/"questions.json").read_text(encoding="utf-8"))[:limit]
    predictions=[json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT/"data"/"processed"/"real").glob("*.json"))]
    if len(predictions)!=3:raise RuntimeError("Executer real_extraction.py d'abord")
    ids=[p["document"]["id"] for p in predictions]
    for p in predictions:store.ingest(p["document"],p["graph"])
    progress=ROOT/"reports"/"real-benchmark-progress.json"
    previous=json.loads(progress.read_text(encoding="utf-8")) if progress.exists() else {}
    if previous and previous.get("model",llm.model()) != llm.model():
        raise RuntimeError("Checkpoint model mismatch; use a separate experiment directory")
    if previous and previous.get("document_ids") != ids:
        raise RuntimeError("Checkpoint corpus mismatch")
    rows=previous.get("rows",[]);answers=previous.get("answers",[])
    actual_input=sum(a["answer"].get("usage",{}).get("input_tokens",0) for a in answers)
    actual_output=sum(a["answer"].get("usage",{}).get("output_tokens",0) for a in answers)
    report={"mode":"live_cypher_vs_graphrag","model":llm.model(),"corpus":"three real papers frontmatter",
            "annotation_review":"pending_independent_human_review","document_ids":ids,
            "repetitions":1,"rows":rows,"answers":answers,
            "protocol":"Controlled: reference term given to both. Question-only: one LLM planner sees only the question, its plan is shared by Cypher and GraphRAG. Planning latency and token allocation included in both free-condition rows. Actual token totals count the shared planner only once. No gold graph is imported.",
            "reference_questions":len(cases)}
    for case in cases:
        for track in ["controlled","question_only"]:
            if any(a["case"]==case["id"] and a["track"]==track for a in answers):
                continue
            plan=None;planning_time=0;planning_usage={}
            if track=="question_only":
                start=time.perf_counter();plan=rag.plan_question(case["question"]);planning_time=time.perf_counter()-start
                planning_usage=plan.get("usage",{})
                actual_input+=planning_usage.get("input_tokens",0);actual_output+=planning_usage.get("output_tokens",0)
            terms=plan["terms"] if plan else [case["term"]]
            mode=plan["mode"] if plan else case["mode"]
            start=time.perf_counter()
            records=[]
            for term in terms:records.extend(store.analytics(mode,term,ids))
            predicted=sorted({r["answer"] for r in records})
            base={"case":case["id"],"track":track,"method":"Cypher","predicted":predicted,
                  "latency_s":time.perf_counter()-start+planning_time,"plan":plan,
                  "usage":planning_usage,"exact_match":set(map(normalized,predicted))==set(map(normalized,case["expected"])),
                  **score(map(normalized,case["expected"]),map(normalized,predicted))}
            rows.append(base)
            start=time.perf_counter()
            answer=rag.ask(case["question"],term=case["term"] if track=="controlled" else None,document_ids=ids,plan=plan)
            usage=answer.get("usage",{})
            actual_input+=usage.get("input_tokens",0)-planning_usage.get("input_tokens",0)
            actual_output+=usage.get("output_tokens",0)-planning_usage.get("output_tokens",0)
            predicted=answer["items"]
            rows.append({"case":case["id"],"track":track,"method":"GraphRAG","predicted":predicted,
                         "latency_s":time.perf_counter()-start+planning_time,"plan":plan,"usage":usage,
                         "exact_match":set(map(normalized,predicted))==set(map(normalized,case["expected"])),
                         "source_count":len(answer["sources"]),
                         **score(map(normalized,case["expected"]),map(normalized,predicted))})
            answers.append({"case":case["id"],"track":track,"question":case["question"],"expected":case["expected"],"answer":answer})
            (ROOT/"reports"/"real-benchmark-progress.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print(f'{case["id"]} {track}: Cypher={base["exact_match"]} GraphRAG={rows[-1]["exact_match"]}',flush=True)
    summary={}
    for track in ["controlled","question_only"]:
        for method in ["Cypher","GraphRAG"]:
            subset=[r for r in rows if r["track"]==track and r["method"]==method]
            summary[track+"/"+method]={"questions":len(subset),"exact_match":statistics.mean(r["exact_match"] for r in subset),
                "mean_f1":statistics.mean(r["f1"] for r in subset),"median_latency_s":statistics.median(r["latency_s"] for r in subset),
                "nonempty_mean_f1":statistics.mean(r["f1"] for r in subset if not r["empty_case"])}
    report["summary"]=summary
    report["completed_observation_tokens"]={"input_tokens":actual_input,"output_tokens":actual_output}
    report["limitations"]=["One repetition only; no stable latency estimate or significance test","Frontmatter only; no full-paper semantic conclusions","Annotations prepared by assistant, awaiting independent human review","Missing predicted facts affect both methods; gold graph is not injected"]
    (ROOT/"reports"/"real-benchmark.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--limit",type=int,default=8)
    args=p.parse_args()
    if not 1<=args.limit<=8:p.error("limit must be 1..8")
    print(json.dumps(run(args.limit)["summary"],ensure_ascii=False,indent=2))
