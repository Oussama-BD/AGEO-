import json
from pathlib import Path
from app.arxiv_metadata import author_graph
from app.core import normalized, score
from real_extraction import signatures
ROOT=Path(__file__).parent
def run():
    output=ROOT/"data"/"processed"/"hybrid-v3"
    output.mkdir(parents=True,exist_ok=True)
    results=[]
    for file in ["attention","graphrag","rag"]:
        prior=json.loads((ROOT/"data"/"processed"/"real"/(file+".pdf.json")).read_text(encoding="utf-8"))
        original=(ROOT/"data"/"raw"/(file+".html")).read_text(encoding="utf-8")
        candidates=[e for e in prior["graph"]["entities"] if e["type"]=="Paper"]
        if len(candidates)!=1:raise ValueError("An explicit paper identity is required")
        publication_id=prior["document"]["source"].split("#")[0].rstrip("/").split("/")[-1]
        html=author_graph(original,prior["graph"]["entities"],publication_id,candidates[0]["id"])
        html["source_file"]=file+".html"
        (output/(file+".html.json")).write_text(json.dumps(html,ensure_ascii=False,indent=2),encoding="utf-8")
        # Preserve PDF assertions and their provenance in a separate source record.
        pdf=dict(prior)
        pdf["document"]=dict(prior["document"],id=prior["document"]["id"]+"-hybrid-v3")
        (output/(file+".pdf.json")).write_text(json.dumps(pdf,ensure_ascii=False,indent=2),encoding="utf-8")
        # References are read here only for evaluation, never by the metadata extractor.
        gold=json.loads((ROOT/"data"/"gold"/(file+".pdf.json")).read_text(encoding="utf-8"))
        nodes={e["id"]:e for e in prior["graph"]["entities"]+html["graph"]["entities"]}
        combined={"entities":list(nodes.values()),"relations":prior["graph"]["relations"]+html["graph"]["relations"]}
        ge,gr=signatures(gold["graph"]);be,br=signatures(prior["graph"]);ae,ar=signatures(combined)
        def authored(graph):
            es={e["id"]:e for e in graph["entities"]}
            return {normalized(es[r["source"]]["name"]) for r in graph["relations"] if r["type"]=="AUTHORED"}
        expected=authored(gold["graph"])
        results.append({"file":file,"authors_before":score(expected,authored(prior["graph"])),
                        "authors_after":score(expected,authored(combined)),
                        "relations_before":score(gr,br),"relations_after":score(gr,ar),
                        "reference_review":"pending_independent_human_review",
                        "metadata_authors":len(html["graph"]["relations"])})
    report={"version":"hybrid-v3","llm_calls":0,"previous_results_preserved":True,
            "construction_sources":["existing Gemini PDF predictions","arXiv citation metadata"],
            "reference_used_for_construction":False,"documents":results}
    (ROOT/"reports"/"html-author-correction-v3.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":run()
