import html,json
from pathlib import Path
from app.arxiv_metadata import parse_arxiv,name_key
ROOT=Path(__file__).parent
sections=[];audit=[]
for stem in ["attention","graphrag","rag"]:
    gold=json.loads((ROOT/"data"/"gold"/(stem+".pdf.json")).read_text(encoding="utf-8"))
    meta=parse_arxiv((ROOT/"data"/"raw"/(stem+".html")).read_text(encoding="utf-8"))
    names={name_key(a["name"]) for a in meta["authors"]}
    graph=gold["graph"];nodes={n["id"]:n for n in graph["entities"]}
    authors=[n for n in graph["entities"] if n["type"]=="Author"]
    rows=[]
    for n in authors:
        affiliations=[nodes[r["target"]]["name"] for r in graph["relations"] if r["type"]=="AFFILIATED_WITH" and r["source"]==n["id"]]
        present=name_key(n["name"]) in names
        key=stem+":"+n["id"]
        rows.append('<tr data-key="'+html.escape(key)+'"><td>'+html.escape(n["name"])+'</td><td>'+html.escape(", ".join(affiliations) or "Aucune affiliation annotée")+'</td><td>'+("Oui" if present else "À contrôler")+'</td><td><select><option value="pending">À relire</option><option value="confirmed">Confirmé par le lecteur</option><option value="correction">À corriger</option></select><input placeholder="Commentaire éventuel"></td></tr>')
    audit.append({"file":stem,"authors":len(authors),"html_author_agreement":all(name_key(a["name"]) in names for a in authors),
                  "reference_status":"pending_independent_human_review","audit_type":"metadata_crosscheck_not_independent_validation"})
    sections.append('<section><h2>'+html.escape(gold["document"]["title"])+'</h2><p><a href="'+gold["document"]["source"]+'" target="_blank">Consulter le PDF original page 1</a></p><table><tr><th>Auteur annoté</th><th>Affiliations annotées</th><th>Présent dans HTML</th><th>Relecture humaine</th></tr>'+"".join(rows)+'</table><details><summary>Texte de l’en-tête PDF utilisé pour les annotations</summary><pre>'+html.escape(gold["text"])+'</pre></details></section>')
page='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Relecture des annotations scientifiques</title>
<style>body{font:15px/1.5 Arial;margin:32px auto;max-width:1100px;padding:0 20px;color:#19372d}h1{color:black}h2{font-size:21px}section{border-top:1px solid #ddd;padding-top:20px;margin-top:25px}table{width:100%;border-collapse:collapse;font-size:13px}td,th{border:1px solid #d9d9d9;padding:10px;text-align:left;vertical-align:top}th{background:#e8eeeb}select,input{padding:8px;border:1px solid #bbc9c2;border-radius:4px;max-width:250px;margin:4px}pre{white-space:pre-wrap;background:#f2f5f3;padding:16px}button{padding:12px 18px;background:#244e40;color:white;border:0;cursor:pointer}.notice{background:#fff2d8;padding:15px}details{margin:15px 0}@media print{section{page-break-before:always}button{display:none}}</style>
<h1>Relecture des annotations scientifiques</h1><p>Vérifier les noms et les affiliations dans les PDF originaux, notamment les marqueurs †, ‡ et les numéros. Les lignes ci-dessous sont des propositions à relire.</p>
<p class="notice">Le recoupement automatique avec les auteurs HTML ne constitue pas une relecture humaine indépendante. Les statuts sont initialement tous « À relire ». Aucun nom de lecteur ni statut n’est envoyé à un serveur.</p>
<label>Nom ou initiales du lecteur <input id="reviewer" placeholder="À remplir par la personne qui relit"></label>
SECTIONS
<p><button onclick="exportReview()">Exporter ma relecture en JSON</button></p>
<script>function exportReview(){const reviewer=document.getElementById("reviewer").value.trim();if(!reviewer){alert("Indiquer le nom ou les initiales du lecteur.");return}const entries=[...document.querySelectorAll("tr[data-key]")].map(r=>({key:r.dataset.key,status:r.querySelector("select").value,comment:r.querySelector("input").value}));const data={reviewer,reviewer_identity:"self_declared_by_user",reviewed_at:new Date().toISOString(),entries,all_reviewed:entries.every(e=>e.status!=="pending")};const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));a.download="relecture-annotations.json";a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}</script></html>'''
(ROOT.parent/"relecture-annotations-v3.html").write_text(page.replace("SECTIONS","".join(sections)),encoding="utf-8")
(ROOT/"reports"/"annotation-audit-v3.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
questions=[
 ("mh1","Quelles institutions sont représentées dans au moins deux articles du corpus ?","Institution <- Author -> Paper; aggregation across distinct papers",3),
 ("mh2","Quels auteurs ont publié sur plusieurs sujets du corpus ?","Author -> Paper -> Topic; count distinct topics",2),
 ("mh3","Quels auteurs sont reliés au sujet retrieval-augmented generation ?","Author -> Paper -> Topic",2),
 ("mh4","Quelles institutions sont reliées à des travaux sur la recherche augmentée par récupération ?","Institution <- Author -> Paper -> Topic; semantic topic mapping",3),
 ("mh5","Quels articles partagent un sujet avec Attention Is All You Need ?","Paper -> Topic <- Paper",2),
 ("mh6","Quels auteurs de deux articles différents sont reliés à un même sujet ?","Author -> Paper -> Topic <- Paper <- Author; not a collaboration claim",4),
 ("sem1","Quels articles cherchent à améliorer l'accès des modèles à une mémoire externe ?","Semantic interpretation of abstracts and retrieval topics",None),
 ("sem2","Quels travaux abordent le raisonnement en plusieurs étapes ?","Semantic mapping to reasoning topics",None),
 ("sem3","Quels articles combinent récupération d'information et génération de texte ?","Semantic interpretation and comparison across abstracts",None),
 ("sem4","Quels travaux cherchent à traiter des séquences plus longues et quels auteurs y contribuent ?","Semantic paper selection, then Paper <- Author",2)]
draft=[{"id":id,"question":q,"required_reasoning":reason,"hops":hops,"expected":None,
        "status":"pending_topic_and_answer_annotation","must_not_score_until_annotated":True}
       for id,q,reason,hops in questions]
(ROOT/"data"/"corpus-v3"/"questions-draft.json").write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"review_rows":sum(a["authors"] for a in audit),"author_metadata_agreement":all(a["html_author_agreement"] for a in audit),"questions_prepared":len(draft)}))
