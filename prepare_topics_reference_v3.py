"""References proposees depuis les resumes, distinctes des predictions Gemini."""
import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).parent
ONTOLOGY={
"attention mechanisms":"Study or introduce an attention architecture, not merely mention a Transformer model.",
"long-context modeling":"Introduce mechanisms to handle long sequences or documents.",
"retrieval-augmented generation":"Combine document retrieval and a language generation or language-model pipeline.",
"dense retrieval":"Dense embedding or nearest-neighbor based document/passage retrieval is a substantive component.",
"question answering":"Question answering is a substantive task or evaluated application.",
"language-model pretraining":"Pretraining objectives, representations, datasets or foundational language-model training are substantive.",
"scaling laws":"Study empirical scaling relations and compute/data/model size trade-offs.",
"few-shot learning":"Study task learning or adaptation from examples in the prompt.",
"instruction tuning":"Train or fine-tune language models to follow instructions.",
"reasoning methods":"Propose or study a deliberate prompting/reasoning procedure, not just score a reasoning benchmark.",
"conversational generation":"Dialogue/chat generation is a primary application.",
"external memory":"Use an explicit external knowledge store or corpus beyond model parameters.",
"knowledge graphs":"Entity knowledge graphs are a substantive component.",
"summarization":"Summarization is a substantive method or evaluated application."
}
ASSIGNMENTS={
"1706.03762":["attention mechanisms"],
"2005.11401":["retrieval-augmented generation","dense retrieval","question answering","external memory"],
"2404.16130":["retrieval-augmented generation","question answering","external memory","knowledge graphs","summarization"],
"1810.04805":["language-model pretraining","question answering"],
"1802.05365":["language-model pretraining","question answering"],
"1907.11692":["language-model pretraining"],
"1910.10683":["language-model pretraining","question answering","summarization"],
"2004.04906":["dense retrieval","question answering"],
"2007.14062":["attention mechanisms","long-context modeling","question answering","summarization"],
"2004.05150":["attention mechanisms","long-context modeling","language-model pretraining","question answering","summarization"],
"2002.08909":["retrieval-augmented generation","dense retrieval","language-model pretraining","question answering","external memory"],
"1906.00300":["dense retrieval","language-model pretraining","question answering"],
"1911.00172":["dense retrieval","external memory"],
"2001.08361":["scaling laws"],
"2005.14165":["language-model pretraining","few-shot learning","question answering"],
"2302.13971":["language-model pretraining"],
"2307.09288":["language-model pretraining","instruction tuning","conversational generation"],
"2310.06825":["attention mechanisms","long-context modeling","instruction tuning"],
"2203.02155":["instruction tuning"],
"2201.11903":["reasoning methods","few-shot learning"],
"2205.11916":["reasoning methods"],
"2210.03629":["reasoning methods","question answering","few-shot learning"],
"2305.10601":["reasoning methods"],
"2212.10496":["dense retrieval"],
"2104.07567":["retrieval-augmented generation","dense retrieval","question answering","external memory","conversational generation"]
}
def run():
    corpus=json.loads((ROOT/"data/corpus-v3/articles.json").read_text(encoding="utf-8"))
    folder=ROOT/"data/references-v3";folder.mkdir(exist_ok=True)
    # Ontology is shared vocabulary, never the per-paper reference assignments.
    (ROOT/"data/corpus-v3/ontology.json").write_text(json.dumps(ONTOLOGY,ensure_ascii=False,indent=2),encoding="utf-8")
    reference={"version":"proposed-v3-1","annotated_by":"assistant_direct_abstract_review",
        "review_status":"pending_independent_human_review",
        "scope":"titles authors and abstracts; affiliations only for the three original PDF headers",
        "papers":[{"arxiv_id":a["arxiv_id"],"topics":ASSIGNMENTS[a["arxiv_id"]],
                   "source":a["source"],"abstract_sha256":hashlib.sha256(a["abstract"].encode()).hexdigest()}
                  for a in corpus]}
    path=folder/"topics.proposed.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8"))!=reference:
        raise RuntimeError("Frozen reference differs; create a new version instead of overwriting")
    path.write_text(json.dumps(reference,ensure_ascii=False,indent=2),encoding="utf-8")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT/"reports/references-v3-freeze.json").write_text(json.dumps({"sha256":digest,"status":reference["review_status"]},indent=2),encoding="utf-8")
    print("Reference proposals frozen:",len(reference["papers"]),"papers;",len(ONTOLOGY),"topics")
if __name__=="__main__":run()
