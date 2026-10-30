"""Fige les observations reelles terminees sans refaire d'appel Gemini."""
import json
import statistics
from pathlib import Path
ROOT=Path(__file__).parent
p=ROOT/"reports"/"real-benchmark-progress.json"
report=json.loads(p.read_text(encoding="utf-8"))
rows=report["rows"]
summary={}
for track in ["controlled","question_only"]:
    for method in ["Cypher","GraphRAG"]:
        subset=[r for r in rows if r["track"]==track and r["method"]==method]
        if subset:
            summary[track+"/"+method]={"questions":len(subset),"exact_match":statistics.mean(r["exact_match"] for r in subset),
                "mean_f1":statistics.mean(r["f1"] for r in subset),"median_latency_s":statistics.median(r["latency_s"] for r in subset)}
paired={a["case"] for a in report["answers"] if a["track"]=="controlled"} & {a["case"] for a in report["answers"] if a["track"]=="question_only"}
paired_summary={}
for key in summary:
    track,method=key.split("/")
    subset=[r for r in rows if r["track"]==track and r["method"]==method and r["case"] in paired]
    paired_summary[key]={"questions":len(subset),"exact_match":statistics.mean(r["exact_match"] for r in subset),
                        "mean_f1":statistics.mean(r["f1"] for r in subset),"median_latency_s":statistics.median(r["latency_s"] for r in subset)}
report.update(summary=summary,paired_summary=paired_summary,paired_cases=sorted(paired),
              completion_status="partial_daily_free_quota_20_requests_per_model",
              completed_observations=len(report["answers"]),
              model="gemini-2.5-flash",
              limitations=["Five questions paired across both conditions; sixth controlled only",
                           "One repetition; no significance or stable latency claim",
                           "Annotations prepared by assistant, awaiting independent human review",
                           "Frontmatter only; not an evaluation of complete scientific articles",
                           "Missing predicted relations are not repaired with gold annotations"])
report["completed_observation_tokens"]={
    field:sum(a["answer"].get("usage",{}).get(field,0) for a in report["answers"])
    for field in ["input_tokens","output_tokens"]}
(ROOT/"reports"/"real-benchmark.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"paired_summary":paired_summary,"completed_observations":len(report["answers"])},ensure_ascii=False,indent=2))
