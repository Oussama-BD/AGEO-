"""Prepare topic/question review sheets without claiming independent review."""
import json,html
from pathlib import Path
R=Path(__file__).parent
corpus=json.loads((R/'data/corpus-v3/articles.json').read_text(encoding='utf-8'))
refs=json.loads((R/'data/references-v3/topics.proposed.json').read_text(encoding='utf-8'))
pred=json.loads((R/'data/experiments/v3/topics.predicted.json').read_text(encoding='utf-8'))
qs=json.loads((R/'data/references-v3/questions.proposed.json').read_text(encoding='utf-8'))
ontology=json.loads((R/'data/corpus-v3/ontology.json').read_text(encoding='utf-8'))
byid={a['arxiv_id']:a for a in corpus};esc=html.escape
chunks=['''<!doctype html><meta charset="utf-8"><title>AGEO RECHERCHE — Relecture V3</title><style>body{max-width:1000px;margin:40px auto;font:16px system-ui;line-height:1.6;background:#f4f7f8;color:#193b46}article{background:white;border:1px solid #d8e2e6;border-radius:10px;padding:24px;margin:20px 0}textarea{width:100%;min-height:75px}button{padding:12px;background:#176b63;color:white;border:0}input{padding:10px}pre{white-space:pre-wrap}</style><h1>AGEO RECHERCHE · Relecture V3</h1><p>Les références ci-dessous sont des propositions préparées par l’assistant. Aucune validation humaine indépendante n’est attestée. Vérifier les résumés et l’ontologie avant d’approuver ou corriger chaque ensemble attendu. Le téléchargement recueille les avis ; il ne modifie pas automatiquement les références du benchmark.</p><label>Nom du relecteur <input id="reviewer"></label><p><button id="export">Exporter les avis de relecture</button></p><h2>Ontologie</h2>''','<pre>'+esc(json.dumps(ontology,ensure_ascii=False,indent=2))+'</pre>']
for p in refs['papers']:
 a=byid[p['arxiv_id']];key='paper-'+p['arxiv_id']
 chunks.append('<article data-id="'+key+'"><h2>'+esc(a['title'])+'</h2><a href="'+esc(a['source'])+'">Source arXiv</a><p>'+esc(a['abstract'])+'</p><p><b>Sujets proposés pour la référence :</b> '+esc(', '.join(p['topics']))+'</p><details><summary>Extraction du modèle à comparer après relecture</summary><pre>'+esc(json.dumps(pred.get(p['arxiv_id'],[]),ensure_ascii=False,indent=2))+'</pre></details><label><input type="checkbox" class="approved"> Ensemble proposé vérifié</label><p>Corrections ou réserves :</p><textarea></textarea></article>')
chunks.append('<h2>Questions et réponses attendues proposées</h2>')
for q in qs['questions']:
 chunks.append('<article data-id="question-'+q['id']+'"><h3>'+esc(q['question'])+'</h3><pre>'+esc(json.dumps(q['expected'],ensure_ascii=False,indent=2))+'</pre><label><input type="checkbox" class="approved"> Question et ensemble attendu vérifiés contre les sources et l’ontologie</label><p>Corrections ou réserves :</p><textarea></textarea></article>')
chunks.append('''<script>document.getElementById('export').onclick=()=>{let reviewer=document.getElementById('reviewer').value.trim();if(!reviewer){alert('Indiquer le nom du relecteur.');return}let result={reviewer,reviewer_identity_independently_verified:false,date:new Date().toISOString(),status:'review_feedback_only',entries:[...document.querySelectorAll('article')].map(a=>({id:a.dataset.id,approved:a.querySelector('.approved').checked,notes:a.querySelector('textarea').value}))};let url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));let a=document.createElement('a');a.href=url;a.download='avis-relecture-v3.json';a.click();URL.revokeObjectURL(url)};</script>''')
out=R.parent/'relecture-sujets-questions-v3.html';out.write_text('\n'.join(chunks),encoding='utf-8');print(out.name)
